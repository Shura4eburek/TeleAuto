# src/teleauto/vpn/vpn_monitor_simple.py
import time
import threading
from . import vpn
from src.teleauto.network.network_utils import wait_for_internet
from src.teleauto.authenticator.totp_client import check_time_drift, get_current_totp
from src.teleauto.localization import tr


class SimpleVPNMonitor:
    def __init__(self, pin_code=None, secret_2fa=None, profile_index=0):
        self.running = False
        self.connected = False
        self.monitor_thread = None
        self.pin_code = pin_code
        self.totp_secret = secret_2fa
        self.profile_index = profile_index
        self.check_interval = 5

        print(tr("log_mon_init", idx=profile_index + 1))

    def check_vpn_connection(self):
        try:
            return vpn.check_vpn_connection()
        except Exception as e:
            print(tr("log_mon_vpn_check_err", e=e))
            return False

    def reconnect_vpn(self):
        print(tr("log_mon_internet_check"))
        wait_for_internet()

        print(tr("log_mon_reconnect_profile", idx=self.profile_index + 1))
        try:
            vpn.start_pritunl()

            time_ok, ntp_time = check_time_drift()
            if not time_ok:
                print(tr("log_mon_time_fix"))

            totp_code = get_current_totp(self.totp_secret, ntp_time=ntp_time)

            if not totp_code:
                print(tr("log_mon_totp_fail"))
                return False

            if vpn.click_pritunl_connect(profile_index=self.profile_index):
                if vpn.input_2fa_code_and_reconnect(totp_code):
                    print(tr("log_mon_restore_start"))
                    return True

            print(tr("log_mon_click_fail", idx=self.profile_index + 1))
            return False
        except Exception as e:
            print(tr("log_mon_reconnect_err", e=e))
            return False

    def monitor_loop(self):
        print(tr("log_mon_loop_start"))

        while self.running:
            try:
                is_connected = self.check_vpn_connection()

                if is_connected != self.connected:
                    self.connected = is_connected
                    status = tr("status_connected") if self.connected else tr("status_disconnected")
                    print(tr("log_mon_status", status=status))

                if not self.connected:
                    print(tr("log_mon_vpn_down"))
                    if self.reconnect_vpn():
                        time.sleep(10)
                        self.connected = self.check_vpn_connection()
                        if self.connected:
                            print(tr("log_mon_reconnect_success"))

                time.sleep(self.check_interval)

            except Exception as e:
                print(tr("log_mon_loop_err", e=e))
                time.sleep(self.check_interval)

    def start(self):
        if not self.totp_secret:
            print(tr("log_mon_no_secret", idx=self.profile_index + 1))
            return False

        self.connected = self.check_vpn_connection()
        state_text = tr("state_connected_lower") if self.connected else tr("state_disconnected_lower")
        print(tr("log_mon_initial_state", state=state_text))

        self.running = True

        # ИСПРАВЛЕНИЕ: Сначала пишем в лог, потом запускаем поток
        # Это предотвращает "слипание" строк из-за гонки потоков
        print(tr("log_mon_bg_start"))

        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

        return True

    def stop(self):
        print(tr("log_mon_stop"))
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)