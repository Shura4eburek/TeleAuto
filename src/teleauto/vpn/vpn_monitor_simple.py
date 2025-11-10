import time
import threading
# import ntplib  <- Удалено
# import pyotp   <- Удалено
from . import vpn
from src.teleauto.network.network_utils import wait_for_internet
# --- Добавлено: ---
from src.teleauto.authenticator.totp_client import check_time_drift, get_current_totp
# --------------------

class SimpleVPNMonitor:
    def __init__(self, pin_code=None, secret_2fa=None):
        self.running = False
        self.connected = False
        self.monitor_thread = None
        self.pin_code = pin_code
        self.totp_secret = secret_2fa
        self.check_interval = 5

        print("VPN Monitor (Simple) инициализирован")

    # --- Метод check_time_drift(self, ...) удален ---

    # --- Метод get_current_totp(self, ...) удален ---

    def check_vpn_connection(self):
        """Проверяем состояние VPN подключения через обновленную функцию"""
        try:
            return vpn.check_vpn_connection()
        except Exception as e:
            print(f"Ошибка проверки VPN: {e}")
            return False

    def reconnect_vpn(self):
        """Переподключение к VPN"""
        print("Проверяем статус подключения к интернету...")
        wait_for_internet()

        print("Переподключение к VPN...")
        try:
            vpn.start_pritunl()

            # --- Изменено (убран self.): ---
            time_ok, ntp_time = check_time_drift()
            if not time_ok:
                input("Исправьте системное время и нажмите Enter для продолжения...")

            # --- Изменено (убран self. и добавлен self.totp_secret): ---
            totp_code = get_current_totp(self.totp_secret, ntp_time=ntp_time)

            if not totp_code:
                print("Не удалось получить TOTP код")
                return False

            if vpn.click_pritunl_connect():
                if vpn.input_2fa_code_and_reconnect(totp_code):
                    print("Восстановление соединения VPN началось...")
                    return True
            return False
        except Exception as e:
            print(f"Ошибка переподключения VPN: {e}")
            return False

    def monitor_loop(self):
        """Основной цикл мониторинга"""
        print("Запуск цикла мониторинга VPN...")

        while self.running:
            try:
                is_connected = self.check_vpn_connection()

                if is_connected != self.connected:
                    self.connected = is_connected
                    status = "ПОДКЛЮЧЕН" if self.connected else "ОТКЛЮЧЕН"
                    print(f"VPN статус: {status}")

                if not self.connected:
                    print("VPN отключен, попытка переподключения...")
                    if self.reconnect_vpn():
                        time.sleep(10)
                        self.connected = self.check_vpn_connection()
                        if self.connected:
                            print("Переподключение успешно")

                time.sleep(self.check_interval)

            except Exception as e:
                print(f"Ошибка в мониторинге: {e}")
                time.sleep(self.check_interval)

    def start(self):
        """Запуск мониторинга"""
        if not self.totp_secret:
            print("Нет секрета 2FA для мониторинга")
            return False

        print("Запуск VPN Monitor (консольная версия)...")
        self.connected = self.check_vpn_connection()
        print(f"Начальное состояние VPN: {'подключен' if self.connected else 'отключен'}")

        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

        print("Мониторинг VPN запущен в фоне")
        return True

    def stop(self):
        """Остановка мониторинга"""
        print("Остановка VPN Monitor...")
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)