import sys
import os
import threading
from tkinter import messagebox
# --- PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import threading
import time
import customtkinter as ctk
from tkinter import messagebox

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
        load_custom_font("Unbounded-Regular.ttf")
        super().__init__()
        self.creds = load_credentials()
        self.decrypted_creds = None
        self.monitor_instance = None
        self.monitor_thread = None
        self.main_frame = None
        self.vpn_is_connected = False
        self.update_ready = False
        self.new_version_tag = None

        threading.Thread(target=self.bg_update_check, daemon=True).start()

        if self.creds: set_language(self.creds.get("language", "ru"))
        self.title("TeleAuto")
        self.geometry("550x280")
        self.resizable(False, False)
        self.after(10, lambda: apply_window_settings(self))
        if not self.creds:
            self.withdraw();
            ConfigWindow(self)
        else:
            if self.creds.get("pin_hash"):
                self.withdraw();
                PinWindow(self)
            else:
                try:
                    self.decrypted_creds = decrypt_credentials(self.creds, None);
                    self.show_main_window()
                except Exception as e:
                    messagebox.showerror("Error", str(e));
                    self.quit()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start network monitoring
        self.net_monitor_running = True
        threading.Thread(target=self.network_monitor_loop, daemon=True).start()

    def config_saved(self, pin_used):
        self.creds = load_credentials()
        if pin_used:
            PinWindow(self)
        else:
            self.decrypted_creds = decrypt_credentials(self.creds, None);
            self.show_main_window()

    def pin_unlocked(self, data):
        self.decrypted_creds = data
        if len(data) > 4: set_language(data[4])
        self.show_main_window()

    def show_main_window(self):
        self.deiconify();
        self.main_frame = MainWindow(self);
        self.main_frame.pack(fill="both", expand=True);
        self.main_frame.expand_log();
        self.geometry("650x600");
        self.resizable(True, True)
        self.update_main_window_buttons();
        print(tr("log_system_start"));
        self.on_disconnect_click(startup=True)
        if self.update_ready and self.new_version_tag:
            self.main_frame.show_update_ready(self.new_version_tag)

    def set_ui_status(self, target, state, text_key):
        if self.main_frame: self.main_frame.update_panel_safe(target, state, text_key)

    def update_main_window_buttons(self, is_busy=False):
        if not self.main_frame: return
        secrets = self.decrypted_creds[2]
        buttons = [self.main_frame.pritunl_btn_1, self.main_frame.pritunl_btn_2, self.main_frame.pritunl_btn_3]
        active = [i for i, s in enumerate(secrets) if s];
        count = len(active);
        total = 125;
        spacing = 5
        w = (total - (count - 1) * spacing) // count if count > 0 else 0
        for btn in buttons: btn.pack_forget()
        for i, btn in enumerate(buttons):
            if i in active:
                is_last = (i == active[-1]);
                px = (0, 0) if is_last else (0, spacing)
                btn.configure(width=w, height=ROW_HEIGHT);
                btn.pack(side="left", padx=px)
                btn.configure(state="disabled" if (is_busy or self.vpn_is_connected) else "normal")
        state = "disabled" if is_busy else ("normal" if self.vpn_is_connected else "disabled")
        self.main_frame.start_telemart_button.configure(state=state);
        self.main_frame.disconnect_button.configure(state=state)
        if not is_busy and not self.vpn_is_connected:
            self.main_frame.start_telemart_button.configure(state="disabled");
            self.main_frame.disconnect_button.configure(state="disabled")
            for i, btn in enumerate(buttons):
                if i in active: btn.configure(state="normal")

    def open_settings_window(self):
        SettingsWindow(self)

    def on_closing(self):
        self.net_monitor_running = False  # Stop net monitor
        if self.monitor_instance: self.monitor_instance.stop()
        self.quit()

    def network_monitor_loop(self):
        """Background thread to check internet ping."""
        while self.net_monitor_running:
            try:
                connected, ping = check_internet_ping()
                if self.main_frame:
                    self.main_frame.after(0, lambda c=connected, p=ping: self.main_frame.update_net_status(c, p))
            except Exception:
                pass
            time.sleep(3)

    def on_pritunl_connect_click(self, idx):
        if not self.main_frame.is_expanded: self.main_frame.expand_log()
        self.update_main_window_buttons(is_busy=True);
        self.set_ui_status("monitor", "waiting", "status_waiting");
        threading.Thread(target=self.run_pritunl, args=(idx,), daemon=True).start()

    def on_start_telemart_click(self):
        if not self.main_frame.is_expanded: self.main_frame.expand_log()
        self.main_frame.start_telemart_button.configure(state="disabled");
        threading.Thread(target=self.run_telemart, daemon=True).start()

    def on_disconnect_click(self, startup=False):
        if not self.main_frame.is_expanded and not startup: self.main_frame.expand_log()
        self.update_main_window_buttons(is_busy=True);
        self.set_ui_status("pritunl", "waiting", "status_waiting");
        threading.Thread(target=self.run_disconnect, args=(startup,), daemon=True).start()

    def run_disconnect(self, startup=False):
        try:
            if self.monitor_instance: self.monitor_instance.stop(); self.monitor_instance = None
            if vpn.check_vpn_connection(): vpn.disconnect_vpn(); vpn.wait_for_disconnect()
            self.vpn_is_connected = False
        except Exception as e:
            print(e)
        finally:
            self.set_ui_status("pritunl", "off", "status_off");
            self.set_ui_status("telemart", "off", "status_waiting");
            self.set_ui_status("monitor", "off", "status_waiting");
            self.update_main_window_buttons(is_busy=False)

    def run_pritunl(self, idx):
        try:
            self.set_ui_status("pritunl", "waiting", "status_working")
            if not wait_for_internet(): self.set_ui_status("pritunl", "error", "status_no_net"); self.set_ui_status(
                "monitor", "off", "status_waiting"); self.update_main_window_buttons(); return
            secret = self.decrypted_creds[2][idx];
            attempt = 0
            while attempt < 5 and not self.vpn_is_connected:
                attempt += 1;
                self.set_ui_status("pritunl", "working", "status_working");
                print(f"{tr('log_vpn_attempt')} {attempt}...")
                vpn.start_pritunl()
                if not vpn.click_pritunl_connect(profile_index=idx): time.sleep(2); continue
                ok, ntp = check_time_drift();
                totp = get_current_totp(secret, ntp_time=ntp)
                if not vpn.input_2fa_code_and_reconnect(totp): time.sleep(2); continue
                time.sleep(10)
                if vpn.check_vpn_connection(): self.vpn_is_connected = True; self.set_ui_status("pritunl", "success",
                                                                                                "status_active"); print(
                    tr("log_vpn_connected"))
            if not self.vpn_is_connected:
                self.set_ui_status("pritunl", "error", "status_error");
                self.set_ui_status("monitor", "off",
                                   "status_waiting")
            else:
                self.start_monitor(idx, secret)
            self.update_main_window_buttons()
        except Exception as e:
            print(e);
            self.set_ui_status("pritunl", "error", "status_error");
            self.set_ui_status("monitor", "off",
                               "status_waiting");
            self.update_main_window_buttons()

    def run_telemart(self):
        try:
            if not self.vpn_is_connected: return

            # Распаковка с путем
            u, p, _, _, _, tm_path = self.decrypted_creds

            # Проверка пути
            if not tm_path or not os.path.exists(tm_path):
                self.after(0, lambda: messagebox.showerror("Error", tr("error_no_tm_path")))
                return

            self.set_ui_status("telemart", "working", "status_working");
            print(tr("log_tm_start"));

            # Передаем путь
            start_telemart(tm_path);

            time.sleep(5)
            print(tr("log_tm_login"));
            if login_telemart(u, p):
                self.set_ui_status("telemart", "success", "status_success");
                print(tr("log_tm_success"))
            else:
                self.set_ui_status("telemart", "error", "status_error")
        except Exception as e:
            print(e);
            self.set_ui_status("telemart", "error", "status_error")
        finally:
            self.main_frame.start_telemart_button.configure(state="normal")

    def start_monitor(self, idx, secret):
        self.set_ui_status("monitor", "working", "status_working");
        print(tr("log_monitor_start"))
        m = SimpleVPNMonitor(pin_code=None, secret_2fa=secret, profile_index=idx)
        if m.start():
            self.set_ui_status("monitor", "success", "status_active");
            self.monitor_instance = m
        else:
            self.set_ui_status("monitor", "error", "status_error")

    def bg_update_check(self):
        """Фоновая проверка обновлений через GitHub"""
        try:
            # Вызываем реальную функцию проверки
            downloaded, tag = check_and_download(VERSION)

            if downloaded:
                self.update_ready = True
                self.new_version_tag = tag
                # Сообщаем GUI, что пора менять цвет лампочки
                if self.main_frame:
                    self.main_frame.after(0, self.notify_update_ui)
        except Exception:
            pass

    def notify_update_ui(self):
        """Сообщаем GUI, что обновление скачано"""
        if self.main_frame:
            # Метод, который мы добавим в MainWindow
            self.main_frame.show_update_ready(self.new_version_tag)

    def on_closing(self):
        """Перехват закрытия окна"""
        if self.update_ready:
            # Если обновление скачано, спрашиваем или просто уведомляем
            if messagebox.askyesno("Обновление",
                                   f"Загружена версия {self.new_version_tag}.\nУстановить её сейчас?"):
                schedule_update_on_exit()

        # Стандартное закрытие
        self.net_monitor_running = False
        if self.monitor_instance: self.monitor_instance.stop()
        self.quit()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()