# src/teleauto/authenticator/totp_client.py
import time
import ntplib
import pyotp
from src.teleauto.localization import tr

def check_time_drift(max_drift_seconds=5):
    client = ntplib.NTPClient()
    try:
        response = client.request('time.windows.com', version=3)
        internet_time = response.tx_time
        system_time = time.time()
        drift = abs(system_time - internet_time)
        if drift > max_drift_seconds:
            print(tr("log_time_drift_warn", drift=drift))
            print(tr("log_time_sync_rec"))
            return False, internet_time
        return True, internet_time
    except Exception as e:
        print(tr("log_time_ntp_err", e=e))
        return True, time.time()

def get_current_totp(secret, offset_seconds=0, interval=30, ntp_time=None):
    totp = pyotp.TOTP(secret, interval=interval)
    if ntp_time is None:
        current_time = time.time() + offset_seconds
    else:
        current_time = ntp_time + offset_seconds
    return totp.at(current_time)