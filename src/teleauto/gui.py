# gui.py
import customtkinter as ctk
import threading
import sys
import os
import time
import json
from tkinter import messagebox

# --- Импортируем всю вашу логику ---
# Убедимся, что Python видит папку 'src'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

try:
    from src.teleauto.login.login import login_telemart, start_telemart
    from src.teleauto.credentials import (
        load_credentials, verify_pin, decrypt_credentials, save_credentials,
        clear_credentials
    )
    from src.teleauto.vpn import vpn
    from src.teleauto.vpn.vpn_monitor_simple import SimpleVPNMonitor
    from src.teleauto.network.network_utils import wait_for_internet
    from src.teleauto.authenticator.totp_client import check_time_drift, get_current_totp
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Убедитесь, что вы запускаете gui.py из корня проекта")
    print("и что папка 'src' существует и содержит все модули.")
    sys.exit(1)


# --- Класс для перенаправления print в GUI ---
class TextboxLogger:
    def __init__(self, textbox):
        self.textbox = textbox
        self.stdout = sys.stdout

    def write(self, message):
        self.stdout.write(message)
        self.textbox.after(0, self.write_to_gui, message)

    def write_to_gui(self, message):
        try:
            if self.textbox.winfo_exists():
                self.textbox.insert(ctk.END, message)
                self.textbox.see(ctk.END)
        except Exception:
            pass

    def flush(self):
        self.stdout.flush()


# --- 1. Окно Конфигурации (Первый запуск) ---
class ConfigWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title("Первичная настройка TeleAuto")
        self.geometry("450x550")
        self.transient(master_app)
        self.grab_set()

        self.grid_columnconfigure(1, weight=1)

        # --- Поля ---
        ctk.CTkLabel(self, text="PIN-код (оставьте пустым, если не нужен):").grid(row=0, column=0, padx=10, pady=5,
                                                                                  sticky="w")
        self.pin_entry = ctk.CTkEntry(self, show="*")
        self.pin_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Повторите PIN-код:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pin_repeat_entry = ctk.CTkEntry(self, show="*")
        self.pin_repeat_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Секрет 2FA (Профиль 1):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.secret_entry_1 = ctk.CTkEntry(self)
        self.secret_entry_1.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Секрет 2FA (Профиль 2):").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.secret_entry_2 = ctk.CTkEntry(self)
        self.secret_entry_2.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Секрет 2FA (Профиль 3):").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.secret_entry_3 = ctk.CTkEntry(self)
        self.secret_entry_3.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Оставьте поле 2FA пустым, если профиль не используется.",
                     font=ctk.CTkFont(size=10)).grid(row=5, column=0, columnspan=2, padx=10, sticky="w")

        ctk.CTkLabel(self, text="").grid(row=6, column=0)  # Разделитель

        self.telemart_checkbox = ctk.CTkCheckBox(self, text="Автозапуск Telemart Client",
                                                 command=self.toggle_login_fields)
        self.telemart_checkbox.grid(row=7, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self, text="Логин Telemart:").grid(row=8, column=0, padx=10, pady=5, sticky="w")
        self.login_entry = ctk.CTkEntry(self)
        self.login_entry.grid(row=8, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Пароль Telemart:").grid(row=9, column=0, padx=10, pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(self, show="*")
        self.password_entry.grid(row=9, column=1, padx=10, pady=5, sticky="ew")

        self.save_button = ctk.CTkButton(self, text="Сохранить и продолжить", command=self.save_config)
        self.save_button.grid(row=10, column=0, columnspan=2, padx=10, pady=20)

        self.toggle_login_fields()
        self.protocol("WM_DELETE_WINDOW", self.master_app.quit)

    def toggle_login_fields(self):
        if self.telemart_checkbox.get() == 1:
            self.login_entry.configure(state="normal")
            self.password_entry.configure(state="normal")
        else:
            self.login_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")

    def save_config(self):
        pin = self.pin_entry.get()
        pin_repeat = self.pin_repeat_entry.get()

        secrets_list = [
            self.secret_entry_1.get().strip(),
            self.secret_entry_2.get().strip(),
            self.secret_entry_3.get().strip()
        ]

        if pin != pin_repeat:
            messagebox.showerror("Ошибка", "PIN-коды не совпадают.")
            return

        if not any(secrets_list):
            messagebox.showerror("Ошибка", "Хотя бы один секретный ключ 2FA должен быть заполнен.")
            return

        login = self.login_entry.get()
        password = self.password_entry.get()
        start_telemart = self.telemart_checkbox.get() == 1

        if start_telemart and (not login or not password):
            messagebox.showerror("Ошибка", "Логин и Пароль не могут быть пустыми, если включен автозапуск Telemart.")
            return

        try:
            save_credentials(login, password, pin if pin else None, secrets_list, start_telemart)
            self.master_app.config_saved(pin if pin else None)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить credentials.json:\n{e}")


# --- 2. Окно ввода PIN-кода ---
class PinWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title("Введите PIN-код")
        self.geometry("350x150")
        self.transient(master_app)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Введите PIN-код для расшифровки данных:").pack(pady=10)
        self.pin_entry = ctk.CTkEntry(self, show="*", width=200)
        self.pin_entry.pack(pady=5)
        self.pin_entry.focus()
        self.unlock_button = ctk.CTkButton(self, text="Войти", command=self.check_pin)
        self.unlock_button.pack(pady=10)
        self.pin_entry.bind("<Return>", self.check_pin)
        self.protocol("WM_DELETE_WINDOW", self.master_app.quit)

    def check_pin(self, event=None):
        pin = self.pin_entry.get()
        creds = self.master_app.creds

        if not verify_pin(creds.get("pin_hash"), pin):
            messagebox.showerror("Ошибка", "Неверный PIN-код.", parent=self)
            return

        try:
            decrypted_data = decrypt_credentials(creds, pin)
            self.master_app.pin_unlocked(decrypted_data)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка расшифровки данных:\n{e}", parent=self)


# --- 3. Главное Окно ---
class MainWindow(ctk.CTkFrame):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app

        self.grid_columnconfigure(0, weight=1)

        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.top_frame.grid_columnconfigure(0, weight=1)
        self.settings_button = ctk.CTkButton(
            self.top_frame, text="⚙️", width=30, height=30,
            command=self.master_app.open_settings_window
        )
        self.settings_button.grid(row=0, column=1, sticky="e")

        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.status_frame.grid_columnconfigure(1, weight=1)  # Колонка статуса

        # --- Ряд 1: Telemart Client ---
        ctk.CTkLabel(self.status_frame, text="Telemart Client:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0,
                                                                                                       padx=(10, 5),
                                                                                                       pady=10,
                                                                                                       sticky="w")
        self.telemart_status = ctk.CTkLabel(self.status_frame, textvariable=self.master_app.telemart_status_var)
        self.telemart_status.grid(row=0, column=1, padx=5, pady=10, sticky="w")
        self.start_telemart_button = ctk.CTkButton(self.status_frame, text="Start", width=120, state="disabled",
                                                   command=self.master_app.on_start_telemart_click)
        self.start_telemart_button.grid(row=0, column=2, padx=10, pady=10, sticky="e")

        # --- Ряд 2: Pritunl ---
        ctk.CTkLabel(self.status_frame, text="Pritunl:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0,
                                                                                               padx=(10, 5), pady=10,
                                                                                               sticky="w")
        self.pritunl_status = ctk.CTkLabel(self.status_frame, textvariable=self.master_app.pritunl_status_var)
        self.pritunl_status.grid(row=1, column=1, padx=5, pady=10, sticky="w")

        self.pritunl_buttons_frame = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        self.pritunl_buttons_frame.grid(row=1, column=2, padx=10, pady=10, sticky="e")

        self.pritunl_btn_1 = ctk.CTkButton(self.pritunl_buttons_frame, text="P1", width=35,
                                           command=lambda: self.master_app.on_pritunl_connect_click(0))
        self.pritunl_btn_1.pack(side="left", padx=(0, 5))
        self.pritunl_btn_2 = ctk.CTkButton(self.pritunl_buttons_frame, text="P2", width=35,
                                           command=lambda: self.master_app.on_pritunl_connect_click(1))
        self.pritunl_btn_2.pack(side="left", padx=5)
        self.pritunl_btn_3 = ctk.CTkButton(self.pritunl_buttons_frame, text="P3", width=35,
                                           command=lambda: self.master_app.on_pritunl_connect_click(2))
        self.pritunl_btn_3.pack(side="left", padx=(5, 0))

        # --- Ряд 3: VPN Monitor ---
        ctk.CTkLabel(self.status_frame, text="VPN Monitor:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0,
                                                                                                   padx=(10, 5),
                                                                                                   pady=10, sticky="w")
        self.monitor_status = ctk.CTkLabel(self.status_frame, textvariable=self.master_app.monitor_status_var)
        self.monitor_status.grid(row=2, column=1, padx=5, pady=10, sticky="w")

        self.disconnect_button = ctk.CTkButton(self.status_frame, text="Disconnect", width=120, state="disabled",
                                               fg_color="gray", command=self.master_app.on_disconnect_click)
        self.disconnect_button.grid(row=2, column=2, padx=10, pady=10, sticky="e")

        # --- Лог (скрыт) ---
        self.log_textbox = ctk.CTkTextbox(self, state=ctk.NORMAL, height=250)
        self.is_expanded = False

    def expand_log(self):
        if self.is_expanded:
            return
        self.is_expanded = True

        current_w = self.master_app.winfo_width()
        self.master_app.geometry(f"{current_w}x600")

        self.log_textbox.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)

        logger = TextboxLogger(self.log_textbox)
        sys.stdout = logger
        sys.stderr = logger


# --- Окно Настроек (вызывается из Главного) ---
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title("Настройки TeleAuto")
        self.geometry("500x600")
        self.transient(master_app)
        self.grab_set()

        self.grid_columnconfigure(1, weight=1)

        self.login_var = ctk.StringVar()
        self.password_var = ctk.StringVar()
        self.secret_var_1 = ctk.StringVar()
        self.secret_var_2 = ctk.StringVar()
        self.secret_var_3 = ctk.StringVar()

        self.pin_frame = ctk.CTkFrame(self)
        self.pin_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        self.pin_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.pin_frame, text="PIN-код:").grid(row=0, column=0, padx=5, sticky="w")
        self.pin_entry = ctk.CTkEntry(self.pin_frame, show="*")
        self.pin_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.unlock_button = ctk.CTkButton(self.pin_frame, text="Разблокировать", command=self.unlock_fields)
        self.unlock_button.grid(row=0, column=2, padx=5)

        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.settings_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.settings_frame, text="Секрет 2FA (Профиль 1):").grid(row=0, column=0, padx=10, pady=5,
                                                                               sticky="w")
        self.secret_entry_1 = ctk.CTkEntry(self.settings_frame, textvariable=self.secret_var_1, state="disabled")
        self.secret_entry_1.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.settings_frame, text="Секрет 2FA (Профиль 2):").grid(row=1, column=0, padx=10, pady=5,
                                                                               sticky="w")
        self.secret_entry_2 = ctk.CTkEntry(self.settings_frame, textvariable=self.secret_var_2, state="disabled")
        self.secret_entry_2.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.settings_frame, text="Секрет 2FA (Профиль 3):").grid(row=2, column=0, padx=10, pady=5,
                                                                               sticky="w")
        self.secret_entry_3 = ctk.CTkEntry(self.settings_frame, textvariable=self.secret_var_3, state="disabled")
        self.secret_entry_3.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        help_text = "Обязательно заполняйте секретки в том порядке, в котором у вас находятся профиля в Pritunl"
        ctk.CTkLabel(self.settings_frame, text=help_text, font=ctk.CTkFont(size=10), text_color="gray").grid(row=3,
                                                                                                             column=0,
                                                                                                             columnspan=2,
                                                                                                             padx=10,
                                                                                                             pady=(0,
                                                                                                                   10),
                                                                                                             sticky="w")

        self.telemart_checkbox = ctk.CTkCheckBox(self.settings_frame, text="Автозапуск Telemart Client",
                                                 command=self.toggle_login_fields, state="disabled")
        self.telemart_checkbox.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(self.settings_frame, text="Логин Telemart:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.login_entry = ctk.CTkEntry(self.settings_frame, textvariable=self.login_var, state="disabled")
        self.login_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.settings_frame, text="Пароль Telemart:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(self.settings_frame, textvariable=self.password_var, show="*",
                                           state="disabled")
        self.password_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        self.save_button = ctk.CTkButton(self, text="Сохранить изменения", state="disabled", command=self.save_changes)
        self.save_button.grid(row=2, column=0, columnspan=2, padx=10, pady=20)
        self.delete_button = ctk.CTkButton(self, text="Удалить все данные", fg_color="#D00", hover_color="#A00",
                                           command=self.delete_data)
        self.delete_button.grid(row=3, column=0, columnspan=2, padx=10, pady=5)

        self.telemart_checkbox.select() if self.master_app.creds.get(
            "start_telemart") else self.telemart_checkbox.deselect()
        self.toggle_login_fields()
        if not self.master_app.creds.get("pin_hash"):
            self.pin_frame.grid_forget()
            self.unlock_fields(no_pin=True)

    def toggle_login_fields(self):
        is_unlocked = self.save_button.cget("state") == "normal"
        if self.telemart_checkbox.get() == 1 and is_unlocked:
            self.login_entry.configure(state="normal")
            self.password_entry.configure(state="normal")
        else:
            self.login_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")

    def unlock_fields(self, no_pin=False):
        pin = self.pin_entry.get()
        creds = self.master_app.creds
        decrypted_data = None

        if no_pin:
            try:
                decrypted_data = decrypt_credentials(creds, None)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка расшифровки данных: {e}", parent=self)
                return
        else:
            if not verify_pin(creds.get("pin_hash"), pin):
                messagebox.showerror("Ошибка", "Неверный PIN-код.", parent=self)
                return
            try:
                decrypted_data = decrypt_credentials(creds, pin)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка расшифровки данных: {e}", parent=self)
                return

        self.login_var.set(decrypted_data[0])
        self.password_var.set(decrypted_data[1])
        secrets = decrypted_data[2]
        self.secret_var_1.set(secrets[0])
        self.secret_var_2.set(secrets[1])
        self.secret_var_3.set(secrets[2])
        self.telemart_checkbox.select() if decrypted_data[3] else self.telemart_checkbox.deselect()

        self.save_button.configure(state="normal")
        self.telemart_checkbox.configure(state="normal")
        self.secret_entry_1.configure(state="normal")
        self.secret_entry_2.configure(state="normal")
        self.secret_entry_3.configure(state="normal")
        self.toggle_login_fields()
        self.pin_frame.grid_forget()

    def save_changes(self):
        login = self.login_var.get()
        password = self.password_var.get()
        secrets_list = [
            self.secret_var_1.get().strip(),
            self.secret_var_2.get().strip(),
            self.secret_var_3.get().strip()
        ]
        start_telemart = self.telemart_checkbox.get() == 1
        pin = self.pin_entry.get() if self.master_app.creds.get("pin_hash") else None

        if not any(secrets_list):
            messagebox.showerror("Ошибка", "Хотя бы один секретный ключ 2FA должен быть заполнен.", parent=self)
            return

        if start_telemart and (not login or not password):
            messagebox.showerror("Ошибка", "Логин и Пароль не могут быть пустыми...", parent=self)
            return

        try:
            save_credentials(login, password, pin, secrets_list, start_telemart)
            self.master_app.creds = load_credentials()
            self.master_app.decrypted_creds = (login, password, secrets_list, start_telemart)
            self.master_app.update_main_window_buttons()
            messagebox.showinfo("Успех", "Настройки сохранены.", parent=self)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить credentials.json:\n{e}", parent=self)

    def delete_data(self):
        if messagebox.askyesno("Подтверждение", "Удалить все данные?\nПриложение будет закрыто.", parent=self):
            try:
                clear_credentials()
                self.master_app.quit()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить файл:\n{e}", parent=self)


# --- Главный класс приложения (контроллер) ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.creds = load_credentials()
        self.decrypted_creds = None
        self.monitor_instance = None
        self.monitor_thread = None
        self.main_frame = None
        self.vpn_is_connected = False

        self.pritunl_status_var = ctk.StringVar(value="⚪ Ожидание")
        self.telemart_status_var = ctk.StringVar(value="⚪ Ожидание")
        self.monitor_status_var = ctk.StringVar(value="⚪ Ожидание")

        self.title("TeleAuto")
        self.geometry("500x280")
        self.resizable(False, False)

        if not self.creds:
            self.withdraw()
            ConfigWindow(self)
        else:
            if self.creds.get("pin_hash"):
                self.withdraw()
                PinWindow(self)
            else:
                try:
                    self.decrypted_creds = decrypt_credentials(self.creds, None)
                    self.show_main_window()
                except Exception as e:
                    self.withdraw()
                    messagebox.showerror("Ошибка данных",
                                         f"Не удалось расшифровать данные без PIN. \n{e}\nУдалите credentials.json и перезапустите.")
                    self.quit()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def config_saved(self, pin_used):
        self.creds = load_credentials()
        if pin_used:
            PinWindow(self)
        else:
            self.decrypted_creds = decrypt_credentials(self.creds, None)
            self.show_main_window()

    def pin_unlocked(self, decrypted_data):
        self.decrypted_creds = decrypted_data
        self.show_main_window()

    def show_main_window(self):
        self.deiconify()
        self.main_frame = MainWindow(self)
        self.main_frame.pack(fill="both", expand=True)
        self.main_frame.expand_log()
        self.geometry("600x600")
        self.resizable(True, True)

        self.update_main_window_buttons()

        print("--- Запуск: проверка активных VPN ---")
        self.on_disconnect_click(startup=True)

    def update_main_window_buttons(self, is_busy=False):
        if not self.main_frame:
            return

        secrets = self.decrypted_creds[2]
        buttons = [
            self.main_frame.pritunl_btn_1,
            self.main_frame.pritunl_btn_2,
            self.main_frame.pritunl_btn_3
        ]

        if is_busy:
            for btn in buttons:
                btn.configure(state="disabled")
            self.main_frame.start_telemart_button.configure(state="disabled")
            self.main_frame.disconnect_button.configure(state="disabled")
        else:
            # Логика по умолчанию
            for i, secret in enumerate(secrets):
                if not secret:
                    buttons[i].configure(state="disabled")
                else:
                    buttons[i].configure(state="normal")

            if self.vpn_is_connected:
                self.main_frame.start_telemart_button.configure(state="normal")
                self.main_frame.disconnect_button.configure(state="normal")
                for btn in buttons:
                    btn.configure(state="disabled")
            else:
                self.main_frame.start_telemart_button.configure(state="disabled")
                self.main_frame.disconnect_button.configure(state="disabled")

    def open_settings_window(self):
        if self.decrypted_creds is None and self.creds.get("pin_hash"):
            messagebox.showinfo("Информация", "Сначала нужно разблокировать данные, введя PIN в окне настроек.",
                                parent=self)
        SettingsWindow(self)

    def on_closing(self):
        if self.monitor_instance:
            self.monitor_instance.stop()
        self.quit()

    def on_pritunl_connect_click(self, profile_index):
        if not self.main_frame.is_expanded:
            self.main_frame.expand_log()
            print("--- Лог активирован ---")

        self.update_main_window_buttons(is_busy=True)

        secret_2fa = self.decrypted_creds[2][profile_index]

        threading.Thread(
            target=self.run_pritunl_logic,
            args=(profile_index, secret_2fa),
            daemon=True
        ).start()

    def on_start_telemart_click(self):
        if not self.main_frame.is_expanded:
            self.main_frame.expand_log()
            print("--- Лог активирован ---")

        self.main_frame.start_telemart_button.configure(state="disabled")
        threading.Thread(target=self.run_telemart_logic, daemon=True).start()

    def on_disconnect_click(self, startup=False):
        if not self.main_frame.is_expanded and not startup:
            self.main_frame.expand_log()
            print("--- Лог активирован ---")

        self.update_main_window_buttons(is_busy=True)
        self.pritunl_status_var.set("🟡 Отключение...")

        threading.Thread(target=self.run_disconnect_logic, args=(startup,), daemon=True).start()

    # --- ИЗМЕНЕНА ЛОГИКА ---
    def run_disconnect_logic(self, startup=False):
        try:
            # 1. Остановить монитор
            if self.monitor_instance:
                print("Остановка VPN монитора...")
                self.monitor_instance.stop()
                self.monitor_instance = None

            # 2. Проверить, нужно ли отключаться
            if vpn.check_vpn_connection():  #
                print("Обнаружен активный VPN. Запускаю отключение...")
                vpn.disconnect_vpn()  #
                vpn.wait_for_disconnect()  #
            else:
                if startup:
                    print("Активный VPN не обнаружен. Пропускаю отключение.")
                else:
                    print("VPN уже отключен.")

            self.vpn_is_connected = False

            if not startup:
                print("--- Система готова к новому подключению ---")

        except Exception as e:
            print(f"Ошибка при отключении: {e}")
        finally:
            # 4. Сбросить GUI
            self.pritunl_status_var.set("⚪ Отключен")
            self.telemart_status_var.set("⚪ Ожидание")
            self.monitor_status_var.set("⚪ Ожидание")
            self.update_main_window_buttons(is_busy=False)  # Разблокируем P1/P2/P3

    def run_pritunl_logic(self, profile_index, secret_2fa):
        try:
            self.pritunl_status_var.set("🟡 Проверка интернета...")
            if not wait_for_internet():  #
                self.pritunl_status_var.set("🔴 Интернет недоступен")
                self.update_main_window_buttons(is_busy=False)
                return

            if vpn.check_vpn_connection():  #
                self.pritunl_status_var.set("🔴 Ошибка: VPN все еще активен.")
                self.update_main_window_buttons(is_busy=False)
                return

            max_attempts = 5
            attempt = 0
            while attempt < max_attempts and not self.vpn_is_connected:
                attempt += 1
                self.pritunl_status_var.set(f"🟡 Попытка P{profile_index + 1} #{attempt}...")

                vpn.start_pritunl()  #

                if not vpn.click_pritunl_connect(profile_index=profile_index):  #
                    print(f"Не удалось нажать Connect для профиля {profile_index + 1}")
                    time.sleep(5)
                    continue

                print("Проверка времени (NTP)...")
                time_ok, ntp_time = check_time_drift()  #
                if not time_ok:
                    print("!!! ВНИМАНИЕ: СИСТЕМНОЕ ВРЕМЯ НЕВЕРНО !!!")

                totp_code = get_current_totp(secret_2fa, ntp_time=ntp_time)  #

                if not vpn.input_2fa_code_and_reconnect(totp_code):  #
                    print("Не удалось ввести 2FA код.")
                    time.sleep(5)
                    continue

                print("Ожидание подключения (10 сек)...")
                time.sleep(10)

                if vpn.check_vpn_connection():  #
                    self.vpn_is_connected = True
                    self.pritunl_status_var.set(f"🟢 VPN P{profile_index + 1} подключен")
                    print("VPN подключен успешно!")
                else:
                    print(f"Попытка #{attempt} не удалась.")

            if not self.vpn_is_connected:
                self.pritunl_status_var.set("🔴 Ошибка подключения")
                self.update_main_window_buttons(is_busy=False)
            else:
                self.start_vpn_monitor(profile_index, secret_2fa)
                self.update_main_window_buttons(is_busy=False)

        except Exception as e:
            print(f"!!! КРИТИЧЕСКАЯ ОШИБКА VPN: {e} !!!")
            self.pritunl_status_var.set("🔴 Критическая ошибка")
            self.update_main_window_buttons(is_busy=False)

    def run_telemart_logic(self):
        try:
            username, password, _, start_telemart_flag = self.decrypted_creds

            if not start_telemart_flag:
                print("Запуск Telemart отключен в настройках.")
                self.telemart_status_var.set("⚪ Отключено")
                self.main_frame.start_telemart_button.configure(state="normal")
                return

            if not self.vpn_is_connected:
                messagebox.showerror("Ошибка", "VPN не подключен. Сначала подключите Pritunl.")
                self.telemart_status_var.set("🔴 VPN не подключен")
                self.main_frame.start_telemart_button.configure(state="normal")
                return

            self.telemart_status_var.set("🟡 Запуск Telemart...")
            print("Запускаем Telemart Client...")
            start_telemart()  #
            time.sleep(5)

            self.telemart_status_var.set("🟡 Вход в Telemart...")
            print("Выполняем вход в Telemart...")
            if login_telemart(username, password):  #
                print("Вход в Telemart выполнен!")
                self.telemart_status_var.set("🟢 Вход выполнен")
            else:
                print("Ошибка входа в Telemart.")
                self.telemart_status_var.set("🔴 Ошибка входа")

        except Exception as e:
            print(f"!!! КРИТИЧЕСКАЯ ОШИБКА TELEMART: {e} !!!")
            self.telemart_status_var.set("🔴 Критическая ошибка")
        finally:
            self.main_frame.start_telemart_button.configure(state="normal")

    def start_vpn_monitor(self, profile_index, secret_2fa):
        self.monitor_status_var.set("🟡 Запуск монитора...")
        print("Запуск фонового мониторинга VPN...")

        if not secret_2fa:
            print(f"VPN Monitor не может быть запущен: нет 2FA секрета для профиля {profile_index + 1}.")
            self.monitor_status_var.set("🔴 Нет 2FA для монитора")
            return

        monitor = SimpleVPNMonitor(pin_code=None, secret_2fa=secret_2fa, profile_index=profile_index)  #

        if monitor.start():  #
            print("VPN Monitor запущен в фоне.")
            self.monitor_status_var.set("🟢 Мониторинг активен")
            self.monitor_instance = monitor
            self.monitor_thread = monitor.monitor_thread
        else:
            print("VPN Monitor не запущен.")
            self.monitor_status_var.set("🔴 Ошибка монитора")


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    app = App()
    app.mainloop()