# src/teleauto/updater.py
import requests
import sys
import os
import subprocess
from packaging import version

# Укажите точно ваш репозиторий: user/repo
GITHUB_REPO = "Shura4eburek/TeleAuto"


def check_and_download(current_ver):
    """
    1. Проверяет последнюю версию на GitHub.
    2. Если она новее current_ver -> скачивает .exe как TeleAuto_new.exe.
    Возвращает: (bool: скачано_ли, str: новая_версия)
    """
    try:
        # Получаем данные о последнем релизе
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        resp = requests.get(url, timeout=5)

        if resp.status_code != 200:
            return False, None

        data = resp.json()
        remote_tag = data.get("tag_name", "v0.0")

        # Сравнение версий (убираем 'v' для парсера)
        # Если версия на сервере <= текущей, то обновления нет
        if version.parse(remote_tag.replace("v", "")) <= version.parse(current_ver.replace("v", "")):
            return False, None

        print(f"Update found: {remote_tag}. Downloading...")

        # Ищем файл .exe в ассетах релиза
        exe_url = None
        for asset in data.get("assets", []):
            if asset["name"].endswith(".exe"):
                exe_url = asset["browser_download_url"]
                break

        if not exe_url:
            return False, None

        # Скачиваем файл
        new_exe_path = "TeleAuto_new.exe"
        with requests.get(exe_url, stream=True) as r:
            r.raise_for_status()
            with open(new_exe_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return True, remote_tag

    except Exception as e:
        print(f"Updater error: {e}")
        return False, None


def create_update_batch():
    """Создает BAT файл для подмены (запускается при закрытии)"""
    current_exe = os.path.basename(sys.executable)
    new_exe = "TeleAuto_new.exe"

    # VBS скрипт для окна "Успех"
    vbs_msg = 'MsgBox "TeleAuto updated successfully!", 64, "TeleAuto Update"'

    bat_content = f"""
@echo off
timeout /t 2 /nobreak > NUL
:loop
tasklist | find /i "{current_exe}" >nul
if %errorlevel%==0 (
    timeout /t 1 >nul
    goto loop
)
if exist "{current_exe}" del "{current_exe}"
if exist "{new_exe}" move "{new_exe}" "{current_exe}"

echo {vbs_msg} > success.vbs
cscript //nologo success.vbs
del success.vbs
del "%~f0"
"""
    with open("updater.bat", "w") as f:
        f.write(bat_content)


def schedule_update_on_exit():
    """Запускает механизм обновления скрытно"""
    create_update_batch()
    # Запускаем без окна консоли
    subprocess.Popen(["updater.bat"], shell=True, creationflags=0x08000000)