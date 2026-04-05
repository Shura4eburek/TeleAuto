# src/teleauto/vpn/pritunl_auto.py
import os
import time
import subprocess
import logging
import pyotp
import tarfile
import glob
import ntplib
import json
import socket
import threading
import http.client
import email.utils

from src.teleauto.gui.constants import (
    VPN_CHECK_INTERVAL, VPN_RECONNECT_DELAY, VPN_NO_PROFILES_DELAY,
    VPN_NO_INTERNET_DELAY, NTP_TIMEOUT, HTTP_SYNC_TIMEOUT,
    SOCKET_CHECK_TIMEOUT, VPN_BACKOFF_BASE, VPN_BACKOFF_MULTIPLIER, VPN_BACKOFF_MAX,
)
from src.teleauto.localization import tr

logger = logging.getLogger(__name__)

# ================= CONFIGURATION =================
CLI_PATH = r"C:\Program Files (x86)\Pritunl\pritunl-client.exe"
PROFILES_FILE = "profiles.json"


# ================================================

class PritunlAutopilot:
    def __init__(self, stop_event=None, status_callback=None, secrets_dict=None, manual_offset=0, profile_status_callback=None):
        self.cli = CLI_PATH
        self.manual_offset_val = manual_offset
        self.time_offset = 0
        self.secrets = secrets_dict or {}
        self.internet_was_down = False
        self.stop_event = stop_event or threading.Event()
        self.status_callback = status_callback
        self.profile_status_callback = profile_status_callback
        self._last_profile_statuses: dict = {}

        self.is_connected_state = False
        self.last_connected_count = -1

        # Backoff state
        self._backoff_delay = VPN_BACKOFF_BASE

        if not os.path.exists(self.cli):
            logger.error(tr("log_vpn_no_cli", path=self.cli))
            return

        self.sync_time()

        if not os.path.exists("profiles"):
            os.makedirs("profiles")

    def notify_ui(self, state, msg=""):
        if self.status_callback:
            self.status_callback(state, msg)

    def check_stop(self):
        return self.stop_event.is_set()

    def check_internet(self):
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=SOCKET_CHECK_TIMEOUT)
            if self.internet_was_down:
                logger.info(tr("log_vpn_internet_restored"))
                self.internet_was_down = False
            return True
        except OSError:
            if not self.internet_was_down:
                logger.warning(tr("log_vpn_no_internet"))
                self.internet_was_down = True
            return False

    def sync_time(self):
        logger.info(tr("log_vpn_syncing"))
        drift = 0

        try:
            client = ntplib.NTPClient()
            response = client.request('pool.ntp.org', version=3, timeout=NTP_TIMEOUT)
            drift = response.tx_time - time.time()
            logger.info(tr("log_vpn_ntp_ok", drift=drift))
        except Exception:
            try:
                conn = http.client.HTTPSConnection("www.google.com", timeout=HTTP_SYNC_TIMEOUT)
                conn.request("HEAD", "/")
                res = conn.getresponse()
                date_str = res.getheader('Date')
                if date_str:
                    dt = email.utils.parsedate_to_datetime(date_str)
                    drift = dt.timestamp() - time.time()
                    logger.info(tr("log_vpn_http_ok", drift=drift))
            except Exception as e:
                logger.warning(tr("log_vpn_sync_err", e=e))
                drift = 0

        self.time_offset = drift + self.manual_offset_val
        logger.info(tr("log_vpn_offset", total=self.time_offset, drift=drift, manual=self.manual_offset_val))

    def get_profiles(self):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            try:
                res = subprocess.run([self.cli, "list"], capture_output=True, text=True, encoding='utf-8',
                                     errors='ignore', startupinfo=startupinfo)
            except Exception:
                res = subprocess.run([self.cli, "list"], capture_output=True, text=True, encoding='cp866',
                                     errors='ignore', startupinfo=startupinfo)

            raw_output = res.stdout.strip()
            profiles = []

            for line in raw_output.splitlines():
                if not line.strip(): continue
                if "|" in line:
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if not parts or parts[0].upper() in ["ID", "NAME", "USER"] or "---" in parts[0]:
                        continue

                    if len(parts) >= 3:
                        p_id = parts[0]
                        p_name = parts[1]
                        p_status = parts[2].lower().strip()
                        profiles.append({"id": p_id, "name": p_name, "status": p_status})
            return profiles
        except Exception as e:
            logger.error(tr("log_vpn_profiles_err", e=e))
            return []

    def export_discovered_profiles(self, profiles):
        try:
            profile_names = [p['name'] for p in profiles]
            temp_file = PROFILES_FILE + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(profile_names, f, indent=4, ensure_ascii=False)

            if os.path.exists(PROFILES_FILE):
                os.remove(PROFILES_FILE)
            os.rename(temp_file, PROFILES_FILE)
        except Exception as e:
            logger.error(tr("log_vpn_profiles_save_err", e=e))

    def import_all_ovpn(self):
        ovpn_files = glob.glob(os.path.join("profiles", "*.ovpn"))
        if not ovpn_files: return

        current_profiles = self.get_profiles()
        current_names = [p['name'] for p in current_profiles]

        for ovpn_path in ovpn_files:
            if self.check_stop(): return
            file_name = os.path.splitext(os.path.basename(ovpn_path))[0]

            if any(file_name in name for name in current_names):
                continue

            logger.info(tr("log_vpn_importing", name=file_name))
            tar_path = f"{file_name}.tar"
            try:
                with tarfile.open(tar_path, "w") as tar:
                    tar.add(ovpn_path, arcname=os.path.basename(ovpn_path))

                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                subprocess.run([self.cli, "add", os.path.abspath(tar_path)],
                               capture_output=True, text=True, startupinfo=startupinfo)

                if os.path.exists(tar_path):
                    os.remove(tar_path)
            except Exception as e:
                logger.error(tr("log_vpn_import_err", name=file_name, e=e))

    def get_totp(self, profile_name):
        secret = self.secrets.get(profile_name)
        if not secret: return None
        try:
            return pyotp.TOTP(secret.replace(" ", "")).at(time.time() + self.time_offset)
        except Exception:
            return None

    def connect(self, profile_id, profile_name):
        if profile_name not in self.secrets:
            logger.error(tr("log_vpn_no_secret", name=profile_name))
            self.notify_ui("working", tr("log_vpn_no_secret", name=profile_name))
            self.stop_event.set()
            return

        otp = self.get_totp(profile_name)
        if not otp:
            logger.error(tr("log_vpn_totp_err", name=profile_name))
            return

        logger.info(tr("log_vpn_connecting", name=profile_name))
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run([self.cli, "start", profile_id, "-p", otp], capture_output=True, startupinfo=startupinfo)

    def disconnect(self, profile_id):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run([self.cli, "stop", profile_id], capture_output=True, startupinfo=startupinfo)

    def disconnect_all(self):
        logger.info(tr("log_vpn_disconnecting_all"))
        profiles = self.get_profiles()
        for p in profiles:
            if p['status'] not in ['disconnected', 'inactive']:
                logger.info(tr("log_vpn_disconnecting", name=p['name']))
                self.disconnect(p['id'])

    def run(self):
        logger.info(tr("log_vpn_started"))
        self.notify_ui("working", tr("status_working"))

        try:
            while not self.check_stop():
                profiles = self.get_profiles()

                if not profiles:
                    logger.info(tr("log_vpn_empty_profiles"))
                    self.import_all_ovpn()
                    profiles = self.get_profiles()

                self.export_discovered_profiles(profiles)

                if not profiles:
                    time.sleep(VPN_NO_PROFILES_DELAY)
                    continue

                if not self.check_internet():
                    time.sleep(VPN_NO_INTERNET_DELAY)
                    continue

                active_count = 0
                any_connecting = False
                total_profiles = len(profiles)

                for p in profiles:
                    if self.check_stop(): break

                    status = p['status']

                    if status == 'active':
                        active_count += 1
                    elif status in ["connecting", "authenticating"]:
                        any_connecting = True
                    elif status in ["disconnected", "inactive", "error"]:
                        logger.info(tr("log_vpn_initiating", name=p['name']))
                        self.connect(p['id'], p['name'])
                        time.sleep(VPN_RECONNECT_DELAY)
                        any_connecting = True

                if self.profile_status_callback:
                    current_statuses = {p['name']: p['status'] for p in profiles}
                    if current_statuses != self._last_profile_statuses:
                        self._last_profile_statuses = current_statuses
                        self.profile_status_callback(current_statuses)

                if active_count > 0:
                    # Reset backoff on success
                    self._backoff_delay = VPN_BACKOFF_BASE
                    if not self.is_connected_state or self.last_connected_count != active_count:
                        msg = tr("log_vpn_active", active=active_count, total=total_profiles)
                        logger.info(tr("log_vpn_status", msg=msg))
                        self.notify_ui("connected", msg)
                        self.is_connected_state = True
                        self.last_connected_count = active_count
                else:
                    if not any_connecting:
                        if self.is_connected_state:
                            self.notify_ui("working", tr("status_off"))
                        self.is_connected_state = False

                if self.is_connected_state:
                    sleep_time = VPN_CHECK_INTERVAL
                else:
                    sleep_time = int(self._backoff_delay)
                    logger.debug(tr("log_vpn_backoff", delay=sleep_time))
                    # Exponential backoff
                    self._backoff_delay = min(self._backoff_delay * VPN_BACKOFF_MULTIPLIER, VPN_BACKOFF_MAX)

                for _ in range(sleep_time):
                    if self.check_stop(): break
                    time.sleep(1)

        finally:
            self.disconnect_all()
            logger.info(tr("log_vpn_monitor_stopped"))
