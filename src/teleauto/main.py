import time
from src.teleauto.login.login import login_telemart, start_telemart
from src.teleauto.credentials import input_credentials, load_credentials, verify_pin, decrypt_credentials
from src.teleauto.vpn import vpn
from src.teleauto.vpn.vpn_monitor_simple import SimpleVPNMonitor
from src.teleauto.network.network_utils import wait_for_internet
from src.teleauto.authenticator.totp_client import check_time_drift, get_current_totp

def main():
    print("Запуск автоматизированной системы...")

    creds = load_credentials()
    pin_entered = None

    if not creds:
        username, password, pin, secret_2fa, start_telemart_flag = input_credentials()
        pin_entered = pin
    else:
        pin_hash = creds.get("pin_hash")
        if pin_hash:
            pin_entered = input("Введите PIN-код: ").strip()
            if not verify_pin(pin_hash, pin_entered):
                print("Неверный PIN-код.")
                return
            try:
                username, password, secret_2fa, start_telemart_flag = decrypt_credentials(creds, pin_entered)
            except ValueError as e:
                print(f"{e}")
                return
        else:
            username, password, secret_2fa, start_telemart_flag = decrypt_credentials(creds, None)

    # Ждём интернет перед первой попыткой VPN подключения
    wait_for_internet()

    vpn_connected = False
    max_attempts = 5
    attempt = 0

    # Проверяем состояние адаптеров VPN перед попытками подключения
    if not vpn.check_vpn_connection():
        print("VPN адаптеры не подключены, начинаем попытки подключения...")
    else:
        print("VPN адаптеры уже подключены, подключение пропущено.")
        vpn_connected = True

    while attempt < max_attempts and not vpn_connected:
        if attempt > 0:
            print(f"Повторная попытка подключения VPN #{attempt + 1}")
        vpn.start_pritunl()
        vpn.click_pritunl_connect()
        time_ok, ntp_time = check_time_drift()
        if not time_ok:
            input("Исправьте системное время и нажмите Enter для продолжения...")
        totp_code = get_current_totp(secret_2fa, ntp_time=ntp_time)
        if not vpn.input_2fa_code_and_reconnect(totp_code):
            print("Не удалось ввести 2FA код и нажать кнопку Connect")
        else:
            time.sleep(5)
            vpn_connected = vpn.check_vpn_connection()
        if not vpn_connected:
            time.sleep(10)
        attempt += 1

    if not vpn_connected:
        print("Не удалось подключиться к VPN после нескольких попыток.")
        return

    print("Запускаем Telemart Client...")
    if vpn_connected and start_telemart_flag:
        print("Запускаем Telemart Client...")
        start_telemart()
        time.sleep(5)

        print("Выполняем вход в систему...")
        if login_telemart(username, password):
            print("Вход в Telemart выполнен успешно!")
        else:
            print("Ошибка входа в Telemart")

    else:
        print("Запуск Telemart Client пропущен.")

    if vpn_connected:
        print("Запуск мониторинга VPN...")
        monitor = SimpleVPNMonitor(pin_code=None, secret_2fa=secret_2fa)
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
