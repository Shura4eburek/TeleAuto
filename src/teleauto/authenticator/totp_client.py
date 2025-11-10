import time
import ntplib
import pyotp

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
            return False, internet_time
        return True, internet_time
    except Exception as e:
        print(f"Ошибка проверки времени через NTP: {e}")
        return True, time.time()

def get_current_totp(secret, offset_seconds=0, interval=30, ntp_time=None):
    totp = pyotp.TOTP(secret, interval=interval)
    if ntp_time is None:
        current_time = time.time() + offset_seconds
    else:
        current_time = ntp_time + offset_seconds
    return totp.at(current_time)