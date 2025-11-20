# src/teleauto/network/network_utils.py
import subprocess
import time
import re
import platform
from src.teleauto.localization import tr


# Существующая функция wait_for_internet остается без изменений...
def wait_for_internet(host="1.1.1.1", timeout=5, retry_interval=5):
    # ... ваш старый код ...
    print(tr("log_net_checking", host=host))
    while True:
        try:
            # Windows флаг создания окна, чтобы не мигала консоль
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout * 1000), host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            if "TTL=" in result.stdout:
                print(tr("log_net_available"))
                return True
            else:
                print(tr("log_net_unavailable"))
        except Exception as e:
            print(tr("log_net_ping_err", e=e))
        time.sleep(retry_interval)


# --- НОВАЯ ФУНКЦИЯ ---
def check_internet_ping(host="1.1.1.1", timeout=1000):
    """
    Возвращает кортеж (connected: bool, ping_ms: int/None).
    Timeout указывается в миллисекундах.
    """
    try:
        # Скрываем окно консоли при вызове ping (для Windows)
        startupinfo = None
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        command = ["ping", "-n", "1", "-w", str(timeout), host]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )

        output = result.stdout
        if "TTL=" in output:
            # Ищем время (time=12ms или время=12мс или time<1ms)
            # Регулярка ищет число перед ms/мс
            match = re.search(r"(?:time|время)[=<]([\d\.]+)\s*(?:ms|мс)", output.lower())
            ping = int(float(match.group(1))) if match else 0
            return True, ping
        else:
            return False, None
    except Exception:
        return False, None