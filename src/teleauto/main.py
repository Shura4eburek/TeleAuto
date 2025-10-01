import time
import threading
import pyotp
from src.teleauto.login.login import login_telemart, start_telemart
from src.teleauto.credentials import input_credentials, load_credentials, verify_pin, decrypt_credentials
from src.teleauto.vpn import vpn

TOTP_OFFSET = 40


def get_current_totp(secret, offset_seconds=TOTP_OFFSET, interval=30):
    totp = pyotp.TOTP(secret, interval=interval)
    current_time = time.time() + offset_seconds
    return totp.at(current_time)


class SimpleVPNMonitor:
    def __init__(self, secret_2fa):
        self.running = False
        self.connected = False
        self.monitor_thread = None
        self.totp_secret = secret_2fa
        self.check_interval = 5

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
                    current_time = time.strftime("%H:%M:%S", time.localtime())
                    print(f"[{current_time}] VPN статус: {status}")

                if not self.connected:
                    print(f"⚠️ [{time.strftime('%H:%M:%S')}] VPN отключен, попытка переподключения...")
                    if self.reconnect_vpn():
                        time.sleep(10)
                        self.connected = self.check_vpn_connection()
                        if self.connected:
                            print(f"[{time.strftime('%H:%M:%S')}] Переподключение успешно")

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
        status = "подключен" if self.connected else "отключен"
        print(f"Начальное состояние VPN: {status}")

        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

        print("Мониторинг VPN запущен в фоне")
        print("Для завершения мониторинга закройте программу (Ctrl+C)")
        return True

    def stop(self):
        """Остановка мониторинга"""
        print("Остановка VPN Monitor...")
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)


def main():
    print("Запуск автоматизированной системы...")

    creds = load_credentials()
    pin_entered = None

    if not creds:
        username, password, pin, secret_2fa = input_credentials()
        pin_entered = pin
    else:
        pin_hash = creds.get("pin_hash")
        if pin_hash:
            pin_entered = input("Введите PIN-код: ").strip()
            if not verify_pin(pin_hash, pin_entered):
                print("Неверный PIN-код.")
                return
            try:
                username, password, secret_2fa = decrypt_credentials(creds, pin_entered)
            except ValueError as e:
                print(f"{e}")
                return
        else:
            username, password, secret_2fa = decrypt_credentials(creds, None)

    ip_vpn_first_try = vpn.get_first_tap_adapter()
    totp_code = get_current_totp(secret_2fa)

    # Получаем IP с любого активного адаптера Pritunl
    print("\n📡 Получение IP адреса активного адаптера Pritunl...")

    vpn_connected = False
    telemart_logged_in = False

    if ip_vpn_first_try:
        print("Проверка активного подключения")
        if vpn.vpn_connect_check(ip_vpn_first_try):
            print("VPN уже подключен!")
            vpn_connected = True
        else:
            print("🔌 Подключение к VPN...")
            vpn.start_pritunl()
            vpn.click_pritunl_connect()
            if not vpn.input_2fa_code_and_reconnect(totp_code):
                print("Не удалось ввести 2FA код и нажать кнопку Connect")
                return

            time.sleep(5)
            ip_vpn = vpn.get_first_tap_adapter()

            # Получаем IP с любого активного адаптера Pritunl
            print("\nПолучение IP адреса активного адаптера Pritunl...")

            if ip_vpn:
                print(f"Используем IP для проверки подключения: {ip_vpn}")
                if vpn.vpn_connect_with_retries(ip_vpn, totp_code):
                    print("VPN подключен успешно!")
                    vpn_connected = True
                else:
                    print("Не удалось подключиться к VPN")
                    return
            else:
                print("Не удалось получить IP адрес VPN")
                return
    else:
        print("TAP-адаптер не найден")
        return

    if vpn_connected:
        print("Запускаем Telemart Client...")
        start_telemart()
        time.sleep(5)

        print("Выполняем вход в систему...")
        if login_telemart(username, password):
            print("Вход в Telemart выполнен успешно!")
            telemart_logged_in = True
        else:
            print("Ошибка входа в Telemart")

    if vpn_connected and telemart_logged_in:
        # Запускаем VPN Monitor
        print("Запуск мониторинга VPN...")
        monitor = SimpleVPNMonitor(secret_2fa)

        if monitor.start():
            print("Система запущена! VPN Monitor работает в фоне.")
            print("=" * 50)

            try:
                # Держим программу запущенной
                while True:
                    time.sleep(30)

            except KeyboardInterrupt:
                print("\nЗавершение работы...")
                monitor.stop()
                print("До свидания!")
        else:
            print("⚠️ VPN Monitor не запущен, но система работает")


if __name__ == "__main__":
    main()
