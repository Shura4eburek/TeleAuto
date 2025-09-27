import pyotp
import time
import ntplib

def check_time_drift(max_drift_seconds=5):
    client = ntplib.NTPClient()
    try:
        response = client.request('time.windows.com', version=3)
        internet_time = response.tx_time
        system_time = time.time()
        drift = abs(system_time - internet_time)
        if drift > max_drift_seconds:
            print(f"Внимание! Системное время отличается от реального на {drift:.2f} секунд.")
            print("Рекомендуется синхронизировать время на компьютере.")
            return False
        return True
    except Exception as e:
        print(f"Ошибка проверки времени через NTP: {e}")
        # Не блокируем работу если нет доступа к NTP
        return True

def get_current_totp(secret, offset_seconds=40, interval=30):
    totp = pyotp.TOTP(secret, interval=interval)
    current_time = time.time() + offset_seconds
    return totp.at(current_time)

if __name__ == "__main__":
    secret_key = "H7XUNV6UNLY3OV6D"  # Ваш секрет

    if not check_time_drift():
        input("Исправьте системное время и нажмите Enter для продолжения...")

    while True:
        code = get_current_totp(secret_key)
        print("Текущий TOTP код:", code)
        time.sleep(30)
