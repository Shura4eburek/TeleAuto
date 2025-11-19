# src/teleauto/network/network_utils.py
import subprocess
import time
from src.teleauto.localization import tr

def wait_for_internet(host="1.1.1.1", timeout=5, retry_interval=5):
    print(tr("log_net_checking", host=host))
    while True:
        try:
            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout * 1000), host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if "TTL=" in result.stdout:
                print(tr("log_net_available"))
                return True
            else:
                print(tr("log_net_unavailable"))
        except Exception as e:
            print(tr("log_net_ping_err", e=e))
        time.sleep(retry_interval)