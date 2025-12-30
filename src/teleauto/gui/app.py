# src/teleauto/gui/app.py
import sys
import os
import threading
import time
import customtkinter as ctk
from tkinter import messagebox

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.teleauto.credentials import load_credentials, decrypt_credentials
from src.teleauto.localization import tr, set_language
from src.teleauto.login.login import login_telemart, start_telemart
from src.teleauto.vpn import vpn
from src.teleauto.vpn.vpn_monitor_simple import SimpleVPNMonitor
from src.teleauto.network.network_utils import wait_for_internet, check_internet_ping
from src.teleauto.authenticator.totp_client import check_time_drift, get_current_totp

from src.teleauto.gui.windows import ConfigWindow, PinWindow, SettingsWindow
from src.teleauto.gui.main_view import MainWindow
from src.teleauto.gui.utils import apply_window_settings
from src.teleauto.gui.constants import ROW_HEIGHT

from src.teleauto.gui.fonts import load_custom_font
from src.teleauto.updater import check_and_download, schedule_update_on_exit
from src.teleauto.gui.constants import VERSION


class App(ctk.CTk):
    def __init__(self):
        load_custom_font("Unbounded-VariableFont_wght.ttf")
        super().__init__()

        self.creds = load_credentials()
        # БЕЗОПАСНОСТЬ: Храним только PIN, а не расшифрованные данные
        self.user_pin = None

        self.monitor_instance = None
        self.main_frame = None
        self.vpn_is_connected = False
        self.update_ready = False
        self.new_version_tag = None

        self.pritunl_cancel_event = threading.Event()
        self.telemart_cancel_event = threading.Event()

        threading.Thread(target=self.bg_update_check, daemon=True).start()

        if self.creds:
            set_language(self.creds.get("language", "ru"))

        self.title("TeleAuto")
        self.geometry("550x280")
        self.resizable(False, False)
        self.after(10, lambda: apply_window_settings(self))

        if not self.creds:
            self.withdraw()
            ConfigWindow(self)
        else:
            if self.creds.get("pin_hash"):
                self.withdraw()
                PinWindow(self)
            else:
                # Если пина нет, просто запускаем интерфейс
                self.show_main_window()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.net_monitor_running = True
        threading.Thread(target=self.network_monitor_loop, daemon=True).start()

    def config_saved(self, pin_used):
        self.creds = load_credentials()
        if pin_used:
            PinWindow(self)
        else:
            self.show_main_window()

    def pin_unlocked(self, pin):
        self.user_pin = pin
        try:
            # Теперь temp_data[4] гарантированно будет языком
            temp_data = decrypt_credentials(self.creds, pin)
            set_language(temp_data[4])
            del temp_data
            self.show_main_window()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.quit()

    def show_main_window(self):
        self.deiconify()
        self.main_frame = MainWindow(self)
        self.main_frame.pack(fill="both", expand=True)
        self.main_frame.expand_log()
        self.geometry("650x600")
        self.resizable(True, True)
        self.update_main_window_buttons()
        print(tr("log_system_start"))
        self.on_disconnect_click(startup=True)
        if self.update_ready and self.new_version_tag:
            self.main_frame.show_update_ready(self.new_version_tag)

    def update_main_window_buttons(self, is_busy=False):
        if not self.main_frame: return
        self.main_frame.toggle_pritunl_ui('normal')

        # Для отрисовки кнопок расшифровываем наличие секретов "на лету"
        try:
            data = decrypt_credentials(self.creds, self.user_pin)
            secrets = data[2]
            active = [i for i, s in enumerate(secrets) if s]
            del data  # Удаляем расшифрованные данные сразу после проверки
        except:
            active = []

        buttons = [self.main_frame.pritunl_btn_1, self.main_frame.pritunl_btn_2, self.main_frame.pritunl_btn_3]
        count = len(active)
        total = 125
        spacing = 5
        w = (total - (count - 1) * spacing) // count if count > 0 else 0

        for btn in buttons: btn.pack_forget()
        for i, btn in enumerate(buttons):
            if i in active:
                px = (0, 0) if (i == active[-1]) else (0, spacing)
                btn.configure(width=w, height=ROW_HEIGHT)
                btn.pack(side="left", padx=px)
                btn.configure(state="disabled" if (is_busy or self.vpn_is_connected) else "normal")

        if not is_busy:
            self.main_frame.toggle_telemart_ui('normal')

        state = "disabled" if is_busy else ("normal" if self.vpn_is_connected else "disabled")
        self.main_frame.start_telemart_button.configure(state=state)
        self.main_frame.disconnect_button.configure(state=state)

    def run_pritunl(self, idx):
        try:
            self.set_ui_status("pritunl", "waiting", "status_working")
            if not wait_for_internet(cancel_event=self.pritunl_cancel_event):
                self.set_ui_status("pritunl", "error",
                                   "status_no_net" if not self.pritunl_cancel_event.is_set() else "status_cancelled")
                self.update_main_window_buttons()
                return

            # Расшифровываем секрет только для текущей попытки подключения
            data = decrypt_credentials(self.creds, self.user_pin)
            secret = data[2][idx]

            attempt = 0
            while attempt < 5 and not self.vpn_is_connected:
                if self.pritunl_cancel_event.is_set(): break
                if attempt > 0: vpn.force_kill_pritunl()

                attempt += 1
                self.set_ui_status("pritunl", "working", "status_working")
                vpn.start_pritunl()

                if not vpn.click_pritunl_connect(profile_index=idx): continue

                ok, ntp = check_time_drift()
                totp = get_current_totp(secret, ntp_time=ntp)

                if vpn.input_2fa_code_and_reconnect(totp):
                    # Ожидание стабилизации соединения
                    for _ in range(10):
                        if vpn.check_vpn_connection():
                            self.vpn_is_connected = True
                            break
                        time.sleep(1)

            # ОЧИСТКА: Удаляем расшифрованный секрет из памяти
            del secret, data

            if self.vpn_is_connected:
                self.set_ui_status("pritunl", "success", "status_active")
                # Для монитора передаем секрет (он будет храниться там локально)
                data_for_mon = decrypt_credentials(self.creds, self.user_pin)
                self.start_monitor(idx, data_for_mon[2][idx])
                del data_for_mon
            else:
                self.set_ui_status("pritunl", "error", "status_error")

            self.update_main_window_buttons()
        except Exception as e:
            print(f"Pritunl error: {e}")
            self.update_main_window_buttons()

    def run_telemart(self):
        try:
            if not self.vpn_is_connected: return

            # Расшифровываем данные Telemart ТОЛЬКО перед вводом
            data = decrypt_credentials(self.creds, self.user_pin)
            u, p, _, _, _, tm_path = data

            if not tm_path or not os.path.exists(tm_path):
                self.after(0, lambda: messagebox.showerror("Error", tr("error_no_tm_path")))
                return

            self.set_ui_status("telemart", "working", "status_working")
            start_telemart(tm_path)

            # Эмуляция ожидания окна (как в исходном коде)
            time.sleep(5)

            if login_telemart(u, p):
                self.set_ui_status("telemart", "success", "status_success")
            else:
                self.set_ui_status("telemart", "error", "status_error")

            # ОЧИСТКА: Стираем пароли из локальных переменных
            del u, p, data
        except Exception as e:
            print(f"Telemart error: {e}")
            self.set_ui_status("telemart", "error", "status_error")
        finally:
            self.update_main_window_buttons()

    def set_ui_status(self, target, state, text_key):
        if self.main_frame: self.main_frame.update_panel_safe(target, state, text_key)

    def open_settings_window(self):
        SettingsWindow(self)

    def network_monitor_loop(self):
        while self.net_monitor_running:
            try:
                connected, ping = check_internet_ping()
                if self.main_frame:
                    self.main_frame.after(0, lambda c=connected, p=ping: self.main_frame.update_net_status(c, p))
            except:
                pass
            time.sleep(3)

    def on_pritunl_connect_click(self, idx):
        if not self.main_frame.is_expanded: self.main_frame.expand_log()
        self.pritunl_cancel_event.clear()
        self.main_frame.toggle_pritunl_ui('working')
        threading.Thread(target=self.run_pritunl, args=(idx,), daemon=True).start()

    def on_start_telemart_click(self):
        if not self.main_frame.is_expanded: self.main_frame.expand_log()
        self.telemart_cancel_event.clear()
        self.main_frame.toggle_telemart_ui('working')
        threading.Thread(target=self.run_telemart, daemon=True).start()

    def on_cancel_pritunl_click(self):
        """Обработчик нажатия кнопки отмены во время подключения VPN"""
        self.pritunl_cancel_event.set()
        print(tr("log_op_cancelled"))

    def on_cancel_telemart_click(self):
        """Обработчик нажатия кнопки отмены во время логина в Telemart"""
        self.telemart_cancel_event.set()
        print(tr("log_op_cancelled"))

    def on_disconnect_click(self, startup=False):
        self.update_main_window_buttons(is_busy=True)
        threading.Thread(target=self.run_disconnect, args=(startup,), daemon=True).start()

    def run_disconnect(self, startup=False):
        try:
            if self.monitor_instance: self.monitor_instance.stop(); self.monitor_instance = None
            if vpn.check_vpn_connection(): vpn.disconnect_vpn(); vpn.wait_for_disconnect()
            self.vpn_is_connected = False
        finally:
            self.set_ui_status("pritunl", "off", "status_off")
            self.update_main_window_buttons(is_busy=False)

    def start_monitor(self, idx, secret):
        m = SimpleVPNMonitor(pin_code=self.user_pin, secret_2fa=secret, profile_index=idx)
        if m.start():
            self.set_ui_status("monitor", "success", "status_active")
            self.monitor_instance = m

    def bg_update_check(self):
        try:
            downloaded, tag = check_and_download(VERSION)
            if downloaded:
                self.update_ready = True
                self.new_version_tag = tag
                if self.main_frame: self.main_frame.after(0, lambda: self.main_frame.show_update_ready(tag))
        except:
            pass

    def on_closing(self):
        self.net_monitor_running = False
        if self.monitor_instance: self.monitor_instance.stop()
        self.quit()


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()