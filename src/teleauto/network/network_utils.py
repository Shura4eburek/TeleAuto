# src/teleauto/network/network_utils.py
import subprocess
import time
import re
import platform
from src.teleauto.localization import tr


# --- ОБНОВЛЕНО: добавлен cancel_event ---
def wait_for_internet(host="1.1.1.1", timeout=5, retry_interval=5, cancel_event=None):
    print(tr("log_net_checking", host=host))
    while True:
        # ПРОВЕРКА ОТМЕНЫ
        if cancel_event and cancel_event.is_set():
            return False

        try:
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

        # Ждем с возможностью быстрого выхода
        for _ in range(retry_interval * 2):  # проверяем каждые 0.5 сек
            if cancel_event and cancel_event.is_set():
                return False
            time.sleep(0.5)


# check_internet_ping оставляем без изменений
def check_internet_ping(host="1.1.1.1", timeout=1000):
    try:
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
            match = re.search(r"(?:time|время)[=<]([\d\.]+)\s*(?:ms|мс)", output.lower())
            ping = int(float(match.group(1))) if match else 0
            return True, ping
        else:
            return False, None
    except Exception:
        return False, None