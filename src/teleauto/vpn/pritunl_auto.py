# src/teleauto/vpn/pritunl_auto.py
import os
import time
import subprocess
import pyotp
import tarfile
import glob
import ntplib
import json
import sys
import socket
import threading
import http.client
import email.utils

# ================= КОНФИГУРАЦИЯ =================
CLI_PATH = r"C:\Program Files (x86)\Pritunl\pritunl-client.exe"
PROFILES_FILE = "profiles.json"
CHECK_INTERVAL = 5


# ================================================

class PritunlAutopilot:
    def __init__(self, stop_event=None, status_callback=None, secrets_dict=None, manual_offset=0):
        """
        Добавлен аргумент manual_offset
        """
        self.cli = CLI_PATH
        self.manual_offset_val = manual_offset  # Сохраняем значение из настроек
        self.time_offset = 0
        self.secrets = secrets_dict or {}
        self.internet_was_down = False
        self.stop_event = stop_event or threading.Event()
        self.status_callback = status_callback

        self.is_connected_state = False
        self.last_connected_count = -1

        if not os.path.exists(self.cli):
            print(f"[ERROR] Pritunl CLI не найден: {self.cli}")
            return

        self.sync_time()

        if not os.path.exists("profiles"):
            os.makedirs("profiles")

    def notify_ui(self, state, msg=""):
        if self.status_callback:
            self.status_callback(state, msg)

    def check_stop(self):
        return self.stop_event.is_set()

    def check_internet(self):
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=3)
            if self.internet_was_down:
                print("[+] Интернет восстановлен!")
                self.internet_was_down = False
            return True
        except OSError:
            if not self.internet_was_down:
                print("[!] Интернет отсутствует...")
                self.internet_was_down = True
            return False

    def sync_time(self):
        """Синхронизация времени: Автоматика + Оффсет из настроек"""
        print("[*] Синхронизация времени...")
        drift = 0

        try:
            client = ntplib.NTPClient()
            response = client.request('pool.ntp.org', version=3, timeout=2)
            drift = response.tx_time - time.time()
            print(f"[*] NTP OK. Авто-дрифт: {drift:.2f} сек.")
        except:
            try:
                conn = http.client.HTTPSConnection("www.google.com", timeout=3)
                conn.request("HEAD", "/")
                res = conn.getresponse()
                date_str = res.getheader('Date')
                if date_str:
                    dt = email.utils.parsedate_to_datetime(date_str)
                    drift = dt.timestamp() - time.time()
                    print(f"[*] HTTP OK. Авто-дрифт: {drift:.2f} сек.")
            except Exception as e:
                print(f"[!] Ошибка авто-синхронизации: {e}")
                drift = 0

        # Используем значение из настроек
        self.time_offset = drift + self.manual_offset_val
        print(
            f"[*] ИТОГОВОЕ СМЕЩЕНИЕ: {self.time_offset:.2f} сек. (Авто: {drift:.2f} + Настройка: {self.manual_offset_val})")

    def get_profiles(self):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            try:
                res = subprocess.run([self.cli, "list"], capture_output=True, text=True, encoding='utf-8',
                                     errors='ignore', startupinfo=startupinfo)
            except:
                res = subprocess.run([self.cli, "list"], capture_output=True, text=True, encoding='cp866',
                                     errors='ignore', startupinfo=startupinfo)

            raw_output = res.stdout.strip()
            profiles = []

            for line in raw_output.splitlines():
                if not line.strip(): continue
                if "|" in line:
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if not parts or parts[0].upper() in ["ID", "NAME", "USER"] or "---" in parts[0]:
                        continue

                    if len(parts) >= 3:
                        p_id = parts[0]
                        p_name = parts[1]
                        p_status = parts[2].lower().strip()
                        profiles.append({"id": p_id, "name": p_name, "status": p_status})
            return profiles
        except Exception as e:
            print(f"[ERROR] Ошибка get_profiles: {e}")
            return []

    def export_discovered_profiles(self, profiles):
        try:
            profile_names = [p['name'] for p in profiles]
            temp_file = PROFILES_FILE + ".tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(profile_names, f, indent=4, ensure_ascii=False)

            if os.path.exists(PROFILES_FILE):
                os.remove(PROFILES_FILE)
            os.rename(temp_file, PROFILES_FILE)
        except Exception as e:
            print(f"[ERROR] Не удалось сохранить список профилей: {e}")

    def import_all_ovpn(self):
        ovpn_files = glob.glob(os.path.join("profiles", "*.ovpn"))
        if not ovpn_files: return

        current_profiles = self.get_profiles()
        current_names = [p['name'] for p in current_profiles]

        for ovpn_path in ovpn_files:
            if self.check_stop(): return
            file_name = os.path.splitext(os.path.basename(ovpn_path))[0]

            if any(file_name in name for name in current_names):
                continue

            print(f"[*] Импорт нового файла: {file_name}")
            tar_path = f"{file_name}.tar"
            try:
                with tarfile.open(tar_path, "w") as tar:
                    tar.add(ovpn_path, arcname=os.path.basename(ovpn_path))

                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

                res = subprocess.run([self.cli, "add", os.path.abspath(tar_path)],
                                     capture_output=True, text=True, startupinfo=startupinfo)

                if os.path.exists(tar_path):
                    os.remove(tar_path)
            except Exception as e:
                print(f"[ERROR] Ошибка импорта {file_name}: {e}")

    def get_totp(self, profile_name):
        secret = self.secrets.get(profile_name)
        if not secret: return None
        try:
            return pyotp.TOTP(secret.replace(" ", "")).at(time.time() + self.time_offset)
        except:
            return None

    def connect(self, profile_id, profile_name):
        if profile_name not in self.secrets:
            print(f"[!] ОШИБКА: Секрет для '{profile_name}' не найден!")
            print("[!] Откройте Настройки (⚙️) и нажмите 'Сохранить', чтобы обновить секреты.")
            self.notify_ui("working", "Нет секрета!")
            self.stop_event.set()
            return

        otp = self.get_totp(profile_name)
        if not otp:
            print(f"[!] Ошибка генерации TOTP для {profile_name}")
            return

        print(f"[*] >>> Подключение к {profile_name}...")
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run([self.cli, "start", profile_id, "-p", otp], capture_output=True, startupinfo=startupinfo)

    def disconnect(self, profile_id):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run([self.cli, "stop", profile_id], capture_output=True, startupinfo=startupinfo)

    def disconnect_all(self):
        print("[*] Завершение работы: Отключаю все профили...")
        profiles = self.get_profiles()
        for p in profiles:
            if p['status'] not in ['disconnected', 'inactive']:
                print(f"[-] Отключаю: {p['name']}")
                self.disconnect(p['id'])

    def run(self):
        print("[>] Pritunl Auto-Monitor запущен.")
        self.notify_ui("working", "Запуск...")

        try:
            while not self.check_stop():
                profiles = self.get_profiles()

                if not profiles:
                    print("[*] Список профилей пуст. Пробую импортировать из папки...")
                    self.import_all_ovpn()
                    profiles = self.get_profiles()

                self.export_discovered_profiles(profiles)

                if not profiles:
                    time.sleep(3)
                    continue

                if not self.check_internet():
                    time.sleep(5)
                    continue

                active_count = 0
                any_connecting = False
                total_profiles = len(profiles)

                for p in profiles:
                    if self.check_stop(): break

                    status = p['status']

                    if status == 'active':
                        active_count += 1
                    elif status in ["connecting", "authenticating"]:
                        any_connecting = True
                    elif status in ["disconnected", "inactive", "error"]:
                        print(f"[*] Инициирую подключение: {p['name']}")
                        self.connect(p['id'], p['name'])
                        time.sleep(2)
                        any_connecting = True

                if active_count > 0:
                    if not self.is_connected_state or self.last_connected_count != active_count:
                        msg = f"Активны: {active_count} из {total_profiles}"
                        print(f"[+] Статус VPN: {msg}")
                        self.notify_ui("connected", msg)
                        self.is_connected_state = True
                        self.last_connected_count = active_count
                else:
                    if not any_connecting:
                        if self.is_connected_state:
                            self.notify_ui("working", "Все отключены")
                        self.is_connected_state = False

                sleep_time = CHECK_INTERVAL if self.is_connected_state else 2
                for _ in range(sleep_time):
                    if self.check_stop(): break
                    time.sleep(1)

        finally:
            self.disconnect_all()
            print("[*] Мониторинг остановлен.")