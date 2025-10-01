import time
import threading
import pyotp
from . import vpn


class VPNMonitorSimple:
    def __init__(self, pin_code=None, secret_2fa=None):
        self.running = False
        self.connected = False
        self.monitor_thread = None
        self.pin_code = pin_code
        self.totp_secret = secret_2fa
        self.check_interval = 5

        print("VPN Monitor (Simple) инициализирован")

    def get_current_totp(self, offset_seconds=40, interval=30):
        """Генерация TOTP кода"""
        if not self.totp_secret:
            return None
        totp = pyotp.TOTP(self.totp_secret, interval=interval)
        current_time = time.time() + offset_seconds
        return totp.at(current_time)

    def check_vpn_connection(self):
        """Проверяем состояние VPN подключения"""
        try:
            ip = vpn.get_first_tap_adapter()
            if ip and not ip.startswith("169.254"):
                return vpn.vpn_connect_check(ip, attempts=1, interval=0.5)
            return False
        except Exception as e:
            print(f"Ошибка проверки VPN: {e}")
            return False

    def reconnect_vpn(self):
        """Переподключение к VPN"""
        print("Переподключение к VPN...")
        try:
            vpn.start_pritunl()

            totp_code = self.get_current_totp()
            if not totp_code:
                print("Не удалось получить TOTP код")
                return False

            if vpn.click_pritunl_connect():
                if vpn.input_2fa_code_and_reconnect(totp_code):
                    print("VPN переподключен успешно")
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
