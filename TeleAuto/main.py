import time
import pyotp
from login import login_telemart
from credentials import input_credentials, load_credentials, verify_pin, decrypt_credentials
import vpn

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

    vpn.start_pritunl()
    proc = vpn.connect_vpn()
    vpn.click_pritunl_connect()

    totp_code = get_current_totp(secret_2fa)
    if not vpn.input_2fa_code_and_reconnect(totp_code):
        print("Не удалось ввести 2FA код и нажать вторую кнопку Connect")


    vpn.wait_for_connection()

    login_telemart(username, password)
    time.sleep(10)

if __name__ == "__main__":
    main()
