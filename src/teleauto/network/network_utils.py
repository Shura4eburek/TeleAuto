import subprocess
import time

def wait_for_internet(host="1.1.1.1", timeout=5, retry_interval=5):
    print(f"Проверка подключения к интернету через {host}...")
    while True:
        try:
            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout * 1000), host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if "TTL=" in result.stdout:
                print("Интернет доступен.")
                return True
            else:
                print("Интернет недоступен, пробуем снова...")
        except Exception as e:
            print(f"Ошибка пинга: {e}")
        time.sleep(retry_interval)
