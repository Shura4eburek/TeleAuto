# src/teleauto/gui/app.py
import sys
import os
import threading
import time
import customtkinter as ctk
from tkinter import messagebox

# Определяем пути для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Импорты проекта
from src.teleauto.credentials import load_credentials, decrypt_credentials
from src.teleauto.localization import tr, set_language
from src.teleauto.login.login import login_telemart, start_telemart

# Импортируем модуль автопилота
from src.teleauto.vpn.pritunl_auto import PritunlAutopilot

from src.teleauto.network.network_utils import wait_for_internet, check_internet_ping
from src.teleauto.gui.windows import ConfigWindow, PinWindow, SettingsWindow
from src.teleauto.gui.main_view import MainWindow
from src.teleauto.gui.utils import apply_window_settings
from src.teleauto.gui.constants import ROW_HEIGHT, VERSION
from src.teleauto.gui.fonts import load_custom_font
from src.teleauto.updater import check_and_download


class App(ctk.CTk):
    def __init__(self):
        load_custom_font("Unbounded-VariableFont_wght.ttf")
        super().__init__()

        self.creds = load_credentials()
        self.user_pin = None

        # --- Переменные для автопилота ---
        self.autopilot_thread = None
        self.autopilot_stop_event = threading.Event()
        self.vpn_is_connected = False
        # ----------------------------------------

        self.main_frame = None
        self.update_ready = False
        self.new_version_tag = None

        self.telemart_cancel_event = threading.Event()

        # Фоновая проверка обновлений
        threading.Thread(target=self.bg_update_check, daemon=True).start()

        if self.creds:
            set_language(self.creds.get("language", "ru"))

        self.title("TeleAuto")
        self.geometry("550x280")
        self.resizable(False, False)
        self.after(10, lambda: apply_window_settings(self))

        # Логика первого запуска / PIN кода
        if not self.creds:
            self.withdraw()
            ConfigWindow(self)
        else:
            if self.creds.get("pin_hash"):
                self.withdraw()
                PinWindow(self)
            else:
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
            # Берем только язык (индекс 4) для установки
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

        # При старте убеждаемся, что всё остановлено
        self.on_disconnect_click(startup=True)

        if self.update_ready and self.new_version_tag:
            self.main_frame.show_update_ready(self.new_version_tag)

    def update_main_window_buttons(self, is_busy=False):
        if not self.main_frame: return
        self.main_frame.toggle_pritunl_ui('normal')

        state_connect = "disabled" if (is_busy or self.vpn_is_connected) else "normal"
        self.main_frame.pritunl_connect_btn.configure(state=state_connect)

        if not is_busy:
            self.main_frame.toggle_telemart_ui('normal')

        state_disconnect = "normal" if self.vpn_is_connected else "disabled"
        state_telemart = "disabled" if is_busy else "normal"

        self.main_frame.start_telemart_button.configure(state=state_telemart)
        self.main_frame.disconnect_button.configure(state=state_disconnect)

    # --- CALLBACK ОТ АВТОПИЛОТА ---
    def update_autopilot_ui(self, state, msg):
        if not self.main_frame: return

        if state == "connected":
            self.main_frame.after(0, lambda: self.set_ui_status("pritunl", "success", "status_connected"))
            self.main_frame.after(0, lambda: self.set_ui_status("monitor", "success", "status_active"))
        elif state == "connecting":
            self.main_frame.after(0, lambda: self.set_ui_status("pritunl", "working", "status_working"))
            self.main_frame.after(0, lambda: self.set_ui_status("monitor", "working", "status_working"))
        elif state == "error":
            self.main_frame.after(0, lambda: self.set_ui_status("monitor", "error", "status_error"))
        elif state == "working":
            self.main_frame.after(0, lambda: self.set_ui_status("monitor", "working", "status_working"))

    # --- ЗАПУСК VPN (АВТОПИЛОТ) ---
    def on_pritunl_connect_click(self):
        if not self.main_frame.is_expanded: self.main_frame.expand_log()
        self.autopilot_stop_event.clear()
        self.main_frame.toggle_pritunl_ui('working')
        self.update_main_window_buttons(is_busy=True)
        self.autopilot_thread = threading.Thread(target=self.run_autopilot_logic, daemon=True)
        self.autopilot_thread.start()

    def run_autopilot_logic(self):
        try:
            self.set_ui_status("pritunl", "working", "status_working")

            # Читаем данные из конфига
            decrypted_secrets = {}
            offset_val = 0

            try:
                data = decrypt_credentials(self.creds, self.user_pin)
                # data[2] = secrets_dict
                # data[6] = manual_offset
                decrypted_secrets = data[2]
                if len(data) > 6:
                    offset_val = data[6]
                del data
            except:
                pass

            # Запускаем автопилот с переданными параметрами
            pilot = PritunlAutopilot(
                stop_event=self.autopilot_stop_event,
                status_callback=self.update_autopilot_ui,
                secrets_dict=decrypted_secrets,
                manual_offset=offset_val
            )

            self.vpn_is_connected = True
            self.main_frame.after(0, lambda: self.update_main_window_buttons(is_busy=False))

            pilot.run()

        except Exception as e:
            print(f"Ошибка автопилота: {e}")
            self.main_frame.after(0, lambda: self.set_ui_status("pritunl", "error", "status_error"))
        finally:
            self.vpn_is_connected = False
            self.main_frame.after(0, lambda: self.set_ui_status("pritunl", "off", "status_off"))
            self.main_frame.after(0, lambda: self.set_ui_status("monitor", "off", "status_waiting"))
            self.main_frame.after(0, lambda: self.update_main_window_buttons(is_busy=False))

    def on_cancel_pritunl_click(self):
        self.autopilot_stop_event.set()
        print(tr("log_op_cancelled"))

    def on_disconnect_click(self, startup=False):
        if not startup:
            print("Остановка системы мониторинга...")
        self.autopilot_stop_event.set()
        if not startup:
            self.main_frame.disconnect_button.configure(state="disabled")

    # --- TELEMART LOGIC (ИСПРАВЛЕНО) ---
    def run_telemart(self):
        try:
            # Получаем все данные
            data = decrypt_credentials(self.creds, self.user_pin)

            # ИСПРАВЛЕНИЕ: Берем данные по индексам, игнорируя лишние поля
            # [username, password, secrets, start_tm, lang, tm_path, offset]
            u = data[0]
            p = data[1]
            tm_path = data[5]

            # Очищаем чувствительные данные из переменной data
            del data

            if not tm_path or not os.path.exists(tm_path):
                self.after(0, lambda: messagebox.showerror("Error", tr("error_no_tm_path")))
                return

            self.set_ui_status("telemart", "working", "status_working")
            start_telemart(tm_path)
            time.sleep(5)
            if login_telemart(u, p):
                self.set_ui_status("telemart", "success", "status_success")
            else:
                self.set_ui_status("telemart", "error", "status_error")

            # Очищаем переменные
            del u, p
        except Exception as e:
            print(f"Telemart error: {e}")
            self.set_ui_status("telemart", "error", "status_error")
        finally:
            self.update_main_window_buttons()

    def on_start_telemart_click(self):
        if not self.main_frame.is_expanded: self.main_frame.expand_log()
        self.telemart_cancel_event.clear()
        self.main_frame.toggle_telemart_ui('working')
        threading.Thread(target=self.run_telemart, daemon=True).start()

    def on_cancel_telemart_click(self):
        self.telemart_cancel_event.set()
        print(tr("log_op_cancelled"))

    # --- UTILS ---
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

    def bg_update_check(self):
        try:
            downloaded, tag = check_and_download(VERSION)
            if downloaded:
                self.update_ready = True
                self.new_version_tag = tag
                if self.main_frame: self.main_frame.after(0, lambda: self.main_frame.show_update_ready(tag))
        except:
            pass

    def install_update_now(self):
        from src.teleauto.updater import schedule_update_on_exit
        if messagebox.askyesno(tr("update_label"), "Install update and restart?"):
            schedule_update_on_exit()
            self.on_closing()

    def on_closing(self):
        self.net_monitor_running = False
        self.autopilot_stop_event.set()
        self.quit()


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()