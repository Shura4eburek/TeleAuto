import time
import pyotp
from src.teleauto.login.login import login_telemart, start_telemart
from credentials import input_credentials, load_credentials, verify_pin, decrypt_credentials
from src.teleauto.vpn import vpn

TOTP_OFFSET = 40  # скорректируйте при необходимости


def get_current_totp(secret, offset_seconds=TOTP_OFFSET, interval=30):
    totp = pyotp.TOTP(secret, interval=interval)
    current_time = time.time() + offset_seconds
    return totp.at(current_time)


def main():
    creds = load_credentials()
    if not creds:
        username, password, pin, secret_2fa = input_credentials()
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
                print(e)
                return
        else:
            username, password, secret_2fa = decrypt_credentials(creds, None)

    ip_vpn = vpn.get_first_tap_adapter()
    totp_code = get_current_totp(secret_2fa)
    # Получаем IP с любого активного адаптера Pritunl
    print("\nПолучение IP адреса активного адаптера Pritunl...")

    if ip_vpn:
        print("Проверка активного подключения")
        if vpn.vpn_connect_check(ip_vpn):
            print("VPN уже подключен!")
            start_telemart()
            time.sleep(5)
            login_telemart(username, password)
        else:
            vpn.start_pritunl()
            vpn.click_pritunl_connect()
            if not vpn.input_2fa_code_and_reconnect(totp_code):
                print("Не удалось ввести 2FA код и нажать вторую кнопку Connect")

            time.sleep(5)

            # Получаем IP с любого активного адаптера Pritunl
            print("\nПолучение IP адреса активного адаптера Pritunl...")

            if ip_vpn:
                print(f"Используем IP для проверки подключения: {ip_vpn}")
                if vpn.vpn_connect_with_retries(ip_vpn, totp_code):
                    print("VPN подключен успешно!")
                    start_telemart()
                    time.sleep(5)
                    login_telemart(username, password)
                else:
                    print("Не удалось подключиться к VPN")

if __name__ == "__main__":
    main()
