# src/teleauto/controller.py
import os
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from src.teleauto.credentials import load_credentials, decrypt_credentials
from src.teleauto.localization import tr, set_language
from src.teleauto.login.login import login_telemart, start_telemart
from src.teleauto.vpn.pritunl_auto import PritunlAutopilot
from src.teleauto.network.network_utils import check_internet_ping
from src.teleauto.updater import check_and_download
from src.teleauto.gui.constants import (
    VERSION, NETWORK_MONITOR_INTERVAL, TELEMART_LAUNCH_DELAY,
)

logger = logging.getLogger(__name__)

EXECUTOR_MAX_WORKERS = 4
SHUTDOWN_TIMEOUT = 5


class AppController:
    """Business logic extracted from App. Communicates to UI via callbacks."""

    def __init__(self, ui):
        self.ui = ui
        self.creds = load_credentials()
        self.user_pin = None

        self.autopilot_stop_event = threading.Event()
        self.telemart_cancel_event = threading.Event()
        self.vpn_is_connected = False

        self.net_monitor_running = True
        self.update_ready = False
        self.new_version_tag = None

        self._executor = ThreadPoolExecutor(max_workers=EXECUTOR_MAX_WORKERS)
        self._futures = []

    def submit(self, fn, *args):
        future = self._executor.submit(fn, *args)
        future.add_done_callback(self._on_future_done)
        self._futures.append(future)
        return future

    @staticmethod
    def _on_future_done(future):
        exc = future.exception()
        if exc:
            logger.error(tr("log_ctrl_bg_err", e=exc))

    def start_background_tasks(self):
        self.submit(self.bg_update_check)
        self.submit(self.network_monitor_loop)

    def shutdown(self):
        """Graceful shutdown: signal all loops to stop, then shut down executor."""
        self.net_monitor_running = False
        self.autopilot_stop_event.set()
        self.telemart_cancel_event.set()

        # Give executor time to finish (VPN disconnect_all runs in finally)
        self._executor.shutdown(wait=False, cancel_futures=True)

        # Safety net: if threads don't stop in time, force quit
        timer = threading.Timer(SHUTDOWN_TIMEOUT, self._force_quit)
        timer.daemon = True
        timer.start()

        # Wait for VPN disconnect
        for f in self._futures:
            try:
                f.result(timeout=SHUTDOWN_TIMEOUT)
            except Exception:
                pass

        timer.cancel()

    def _force_quit(self):
        logger.warning(tr("log_ctrl_forced_shutdown"))
        os._exit(1)

    # --- Credentials ---
    def load_creds(self):
        self.creds = load_credentials()

    def decrypt_and_set_language(self, pin):
        self.user_pin = pin
        with decrypt_credentials(self.creds, pin) as data:
            set_language(data.language)

    # --- VPN Autopilot ---
    def update_autopilot_ui(self, state, msg):
        if not self.ui.main_frame:
            return
        if state == "connected":
            self.ui.main_frame.after(0, lambda: self.ui.set_ui_status("pritunl", "success", "status_connected"))
            self.ui.main_frame.after(0, lambda: self.ui.set_ui_status("monitor", "success", "status_active"))
        elif state == "connecting":
            self.ui.main_frame.after(0, lambda: self.ui.set_ui_status("pritunl", "working", "status_working"))
            self.ui.main_frame.after(0, lambda: self.ui.set_ui_status("monitor", "working", "status_working"))
        elif state == "error":
            self.ui.main_frame.after(0, lambda: self.ui.set_ui_status("monitor", "error", "status_error"))
        elif state == "working":
            self.ui.main_frame.after(0, lambda: self.ui.set_ui_status("monitor", "working", "status_working"))

    def run_autopilot_logic(self):
        try:
            self.ui.set_ui_status("pritunl", "working", "status_working")

            decrypted_secrets = {}
            offset_val = 0

            try:
                data = decrypt_credentials(self.creds, self.user_pin)
                decrypted_secrets = data.secrets
                offset_val = data.manual_offset
            except Exception:
                pass

            pilot = PritunlAutopilot(
                stop_event=self.autopilot_stop_event,
                status_callback=self.update_autopilot_ui,
                secrets_dict=decrypted_secrets,
                manual_offset=offset_val
            )

            self.vpn_is_connected = True
            self.ui.main_frame.after(0, lambda: self.ui.update_main_window_buttons(is_busy=False))

            pilot.run()

        except Exception as e:
            logger.error(tr("log_ctrl_autopilot_err", e=e))
            self.ui.main_frame.after(0, lambda: self.ui.set_ui_status("pritunl", "error", "status_error"))
        finally:
            self.vpn_is_connected = False
            self.ui.main_frame.after(0, lambda: self.ui.set_ui_status("pritunl", "off", "status_off"))
            self.ui.main_frame.after(0, lambda: self.ui.set_ui_status("monitor", "off", "status_waiting"))
            self.ui.main_frame.after(0, lambda: self.ui.update_main_window_buttons(is_busy=False))

    def start_autopilot(self):
        self.autopilot_stop_event.clear()
        self.submit(self.run_autopilot_logic)

    def stop_autopilot(self):
        self.autopilot_stop_event.set()

    # --- Telemart ---
    def run_telemart(self):
        try:
            with decrypt_credentials(self.creds, self.user_pin) as data:
                u = data.username
                p = data.password
                tm_path = data.telemart_path

            if not tm_path or not os.path.exists(tm_path):
                from tkinter import messagebox
                self.ui.after(0, lambda: messagebox.showerror("Error", tr("error_no_tm_path")))
                return

            self.ui.set_ui_status("telemart", "working", "status_working")
            start_telemart(tm_path)
            time.sleep(TELEMART_LAUNCH_DELAY)
            if login_telemart(u, p):
                self.ui.set_ui_status("telemart", "success", "status_success")
            else:
                self.ui.set_ui_status("telemart", "error", "status_error")

        except Exception as e:
            logger.error(tr("log_ctrl_telemart_err", e=e))
            self.ui.set_ui_status("telemart", "error", "status_error")
        finally:
            self.ui.update_main_window_buttons()

    def start_telemart(self):
        self.telemart_cancel_event.clear()
        self.submit(self.run_telemart)

    def stop_telemart(self):
        self.telemart_cancel_event.set()

    # --- Network Monitor ---
    def network_monitor_loop(self):
        while self.net_monitor_running:
            try:
                connected, ping = check_internet_ping()
                if self.ui.main_frame:
                    self.ui.main_frame.after(0, lambda c=connected, p=ping: self.ui.main_frame.update_net_status(c, p))
            except Exception:
                pass
            time.sleep(NETWORK_MONITOR_INTERVAL)

    # --- Update ---
    def bg_update_check(self):
        try:
            downloaded, tag = check_and_download(VERSION)
            if downloaded:
                self.update_ready = True
                self.new_version_tag = tag
                if self.ui.main_frame:
                    self.ui.main_frame.after(0, lambda: self.ui.main_frame.show_update_ready(tag))
        except Exception:
            pass
