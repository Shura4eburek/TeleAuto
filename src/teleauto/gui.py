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
        clear_credentials, hash_password, derive_key, encrypt_data
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
        self.stdout = sys.stdout  # Сохраняем оригинальный stdout

    def write(self, message):
        self.stdout.write(message)  # Пишем в консоль

        # Безопасно пишем в GUI (из любого потока)
        # Использование .after() гарантирует, что обновление GUI
        # произойдет в основном потоке
        self.textbox.after(0, self.write_to_gui, message)

    def write_to_gui(self, message):
        try:
            if self.textbox.winfo_exists():
                self.textbox.insert(ctk.END, message)
                self.textbox.see(ctk.END)  # Автопрокрутка
        except Exception:
            pass  # Окно могло быть закрыто

    def flush(self):
        self.stdout.flush()


# --- 1. Окно Конфигурации (Первый запуск) ---
class ConfigWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title("Первичная настройка TeleAuto")
        self.geometry("450x400")
        self.transient(master_app)  # Поверх главного
        self.grab_set()  # Модальное окно

        self.grid_columnconfigure(1, weight=1)

        # --- Поля ---
        ctk.CTkLabel(self, text="PIN-код (оставьте пустым, если не нужен):").grid(row=0, column=0, padx=10, pady=5,
                                                                                  sticky="w")
        self.pin_entry = ctk.CTkEntry(self, show="*")
        self.pin_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Повторите PIN-код:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pin_repeat_entry = ctk.CTkEntry(self, show="*")
        self.pin_repeat_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Секрет 2FA (BASE32):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.secret_entry = ctk.CTkEntry(self)
        self.secret_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="").grid(row=3, column=0)  # Разделитель

        self.telemart_checkbox = ctk.CTkCheckBox(self, text="Автозапуск Telemart Client",
                                                 command=self.toggle_login_fields)
        self.telemart_checkbox.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self, text="Логин Telemart:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.login_entry = ctk.CTkEntry(self)
        self.login_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Пароль Telemart:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(self, show="*")
        self.password_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        self.save_button = ctk.CTkButton(self, text="Сохранить и продолжить", command=self.save_config)
        self.save_button.grid(row=7, column=0, columnspan=2, padx=10, pady=20)

        self.toggle_login_fields()  # Устанавливаем начальное состояние полей

        # Запрещаем закрытие окна крестиком
        self.protocol("WM_DELETE_WINDOW", self.master_app.quit)

    def toggle_login_fields(self):
        # Реализация Шага 1: неактивные поля
        if self.telemart_checkbox.get() == 1:
            self.login_entry.configure(state="normal")
            self.password_entry.configure(state="normal")
        else:
            self.login_entry.configure(state="disabled")
            self.password_entry.configure(state="disabled")

    def save_config(self):
        pin = self.pin_entry.get()
        pin_repeat = self.pin_repeat_entry.get()
        secret = self.secret_entry.get().strip()

        # Валидация
        if pin != pin_repeat:
            messagebox.showerror("Ошибка", "PIN-коды не совпадают.")
            return
        if not secret:
            messagebox.showerror("Ошибка", "Секретный ключ 2FA не может быть пустым.")
            return

        login = self.login_entry.get()
        password = self.password_entry.get()
        start_telemart = self.telemart_checkbox.get() == 1

        if start_telemart and (not login or not password):
            messagebox.showerror("Ошибка", "Логин и Пароль не могут быть пустыми, если включен автозапуск Telemart.")
            return

        try:
            # Сохраняем (используем вашу функцию из credentials.py)
            save_credentials(login, password, pin if pin else None, secret, start_telemart)

            # Сообщаем главному окну, что конфиг сохранен
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
            # Пытаемся расшифровать
            decrypted_data = decrypt_credentials(creds, pin)
            # Сообщаем главному окну, что пин верный
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
        self.grid_rowconfigure(2, weight=1)  # Элемент [2] (лог) будет расширяться

        # --- Верхний фрейм (Настройки) ---
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        self.top_frame.grid_columnconfigure(0, weight=1)

        self.settings_button = ctk.CTkButton(
            self.top_frame, text="⚙️", width=30, height=30,
            command=self.master_app.open_settings_window
        )
        self.settings_button.grid(row=0, column=1, sticky="e")

        # --- Фрейм Статуса ---
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.status_frame.grid_columnconfigure(1, weight=1)

        # Статус 1: Pritunl
        ctk.CTkLabel(self.status_frame, text="Pritunl:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0,
                                                                                               padx=(10, 5), pady=5,
                                                                                               sticky="w")
        self.pritunl_status = ctk.CTkLabel(self.status_frame, textvariable=self.master_app.pritunl_status_var)
        self.pritunl_status.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Статус 2: Telemart
        ctk.CTkLabel(self.status_frame, text="Telemart Client:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0,
                                                                                                       padx=(10, 5),
                                                                                                       pady=5,
                                                                                                       sticky="w")
        self.telemart_status = ctk.CTkLabel(self.status_frame, textvariable=self.master_app.telemart_status_var)
        self.telemart_status.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Статус 3: VPN Monitor
        ctk.CTkLabel(self.status_frame, text="VPN Monitor:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0,
                                                                                                   padx=(10, 5), pady=5,
                                                                                                   sticky="w")
        self.monitor_status = ctk.CTkLabel(self.status_frame, textvariable=self.master_app.monitor_status_var)
        self.monitor_status.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # --- Кнопка "Начать работу" ---
        self.start_button = ctk.CTkButton(self, text="Начать работу", height=40,
                                          command=self.toggle_expansion_and_start)
        self.start_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # --- Лог (скрыт) ---
        self.log_textbox = ctk.CTkTextbox(self, state=ctk.NORMAL, height=250)
        # .grid() не вызывается, он будет вызван при нажатии кнопки

        self.is_expanded = False

    def toggle_expansion_and_start(self):
        if self.is_expanded:
            return  # Уже запущено

        self.is_expanded = True

        # Шаг 3: Расширяем окно
        current_w = self.master_app.winfo_width()
        self.master_app.geometry(f"{current_w}x600")  # Увеличиваем высоту

        # Показываем лог
        self.log_textbox.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(3, weight=1)  # Теперь лог будет расширяться

        self.start_button.configure(state="disabled")  # Блокируем кнопку

        # Перенаправляем stdout
        logger = TextboxLogger(self.log_textbox)
        sys.stdout = logger
        sys.stderr = logger

        print("--- Запуск рабочего потока ---")

        # Запускаем основную логику в отдельном потоке
        self.master_app.start_work_thread()


# --- Окно Настроек (вызывается из Главного) ---
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title("Настройки TeleAuto")
        self.geometry("500x450")  # Уменьшил высоту, т.к. убрали блок
        self.transient(master_app)
        self.grab_set()

        self.grid_columnconfigure(1, weight=1)

        # Переменные для хранения введенных данных
        self.login_var = ctk.StringVar()
        self.password_var = ctk.StringVar()
        self.secret_var = ctk.StringVar()

        # --- Блок 1: PIN-код для разблокировки ---
        self.pin_frame = ctk.CTkFrame(self)
        self.pin_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        self.pin_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.pin_frame, text="PIN-код:").grid(row=0, column=0, padx=5, sticky="w")
        self.pin_entry = ctk.CTkEntry(self.pin_frame, show="*")
        self.pin_entry.grid(row=0, column=1, padx=5, sticky="ew")
        self.unlock_button = ctk.CTkButton(self.pin_frame, text="Разблокировать", command=self.unlock_fields)
        self.unlock_button.grid(row=0, column=2, padx=5)

        # --- Блок 2: Настройки (изначально выключены) ---
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.settings_frame.grid_columnconfigure(1, weight=1)

        self.telemart_checkbox = ctk.CTkCheckBox(
            self.settings_frame, text="Автозапуск Telemart Client",
            command=self.toggle_login_fields, state="disabled"
        )
        self.telemart_checkbox.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.settings_frame, text="Логин Telemart:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.login_entry = ctk.CTkEntry(self.settings_frame, textvariable=self.login_var, state="disabled")
        self.login_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.settings_frame, text="Пароль Telemart:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(self.settings_frame, textvariable=self.password_var, show="*",
                                           state="disabled")
        self.password_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self.settings_frame, text="Секрет 2FA (BASE32):").grid(row=3, column=0, padx=10, pady=5,
                                                                            sticky="w")
        self.secret_entry = ctk.CTkEntry(self.settings_frame, textvariable=self.secret_var, state="disabled")
        self.secret_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        # --- Блок 3: Тема (УДАЛЕН) ---

        # --- Блок 4: Кнопки (СМЕЩЕНЫ НА ROW 2 и 3) ---
        self.save_button = ctk.CTkButton(self, text="Сохранить изменения", state="disabled", command=self.save_changes)
        self.save_button.grid(row=2, column=0, columnspan=2, padx=10, pady=20)  # Был row=3

        self.delete_button = ctk.CTkButton(self, text="Удалить все данные", fg_color="#D00", hover_color="#A00",
                                           command=self.delete_data)
        self.delete_button.grid(row=3, column=0, columnspan=2, padx=10, pady=5)  # Был row=4

        # --- Логика ---
        # Загружаем нешифрованные данные сразу
        self.telemart_checkbox.select() if self.master_app.creds.get(
            "start_telemart") else self.telemart_checkbox.deselect()
        self.toggle_login_fields()  # Устанавливаем состояние полей

        # Если PIN не установлен, сразу разблокируем
        if not self.master_app.creds.get("pin_hash"):
            self.pin_frame.grid_forget()  # Скрываем фрейм с PIN
            self.unlock_fields(no_pin=True)  # Разблокируем без PIN

    def toggle_login_fields(self):
        # Включает/выключает поля Логин/Пароль в зависимости от чекбокса
        if self.telemart_checkbox.get() == 1:
            self.login_entry.configure(state="normal" if self.save_button.cget("state") == "normal" else "disabled")
            self.password_entry.configure(state="normal" if self.save_button.cget("state") == "normal" else "disabled")
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

        # Разблокировка прошла успешно!
        # Заполняем поля
        self.login_var.set(decrypted_data[0])
        self.password_var.set(decrypted_data[1])
        self.secret_var.set(decrypted_data[2])
        self.telemart_checkbox.select() if decrypted_data[3] else self.telemart_checkbox.deselect()

        # Включаем все поля
        self.save_button.configure(state="normal")
        self.telemart_checkbox.configure(state="normal")
        self.secret_entry.configure(state="normal")
        self.toggle_login_fields()  # Включаем логин/пароль, если нужно

        # Скрываем блок PIN
        self.pin_frame.grid_forget()

    def save_changes(self):
        # Собираем данные из полей
        login = self.login_var.get()
        password = self.password_var.get()
        secret = self.secret_var.get().strip()
        start_telemart = self.telemart_checkbox.get() == 1

        # Берем PIN из поля разблокировки
        pin = self.pin_entry.get() if self.master_app.creds.get("pin_hash") else None

        if not secret:
            messagebox.showerror("Ошибка", "Секретный ключ 2FA не может быть пустым.", parent=self)
            return

        if start_telemart and (not login or not password):
            messagebox.showerror("Ошибка", "Логин и Пароль не могут быть пустыми, если включен автозапуск Telemart.",
                                 parent=self)
            return

        try:
            # Пересохраняем credentials
            save_credentials(login, password, pin, secret, start_telemart)

            # Обновляем креды в главном приложении
            self.master_app.creds = load_credentials()
            self.master_app.decrypted_creds = (login, password, secret, start_telemart)

            messagebox.showinfo("Успех", "Настройки сохранены.", parent=self)
            self.destroy()  # Закрываем окно
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить credentials.json:\n{e}", parent=self)

    def delete_data(self):
        if messagebox.askyesno("Подтверждение",
                               "Вы уверены, что хотите удалить все сохраненные данные?\nПриложение будет закрыто.",
                               parent=self):
            try:
                clear_credentials()
                self.master_app.quit()  # Закрываем приложение
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить файл:\n{e}", parent=self)


# --- Главный класс приложения (контроллер) ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Переменные состояния ---
        self.creds = load_credentials()
        self.decrypted_creds = None
        self.monitor_thread = None

        # --- Переменные для GUI (для привязки к лейблам) ---
        self.pritunl_status_var = ctk.StringVar(value="⚪ Ожидание")
        self.telemart_status_var = ctk.StringVar(value="⚪ Ожидание")
        self.monitor_status_var = ctk.StringVar(value="⚪ Ожидание")

        # --- Конфигурация окна ---
        self.title("TeleAuto")
        self.geometry("500x250")  # Начальный размер

        # --- ЛОГИКА ЗАПУСКА ---
        # Проверяем, что делать при старте
        if not self.creds:
            # 1. Файла нет -> Показываем окно Конфигурации
            self.withdraw()  # Скрываем основное окно
            ConfigWindow(self)
        else:
            # 2. Файл есть -> Проверяем, нужен ли PIN
            if self.creds.get("pin_hash"):
                # 2a. Нужен PIN -> Показываем окно PIN
                self.withdraw()
                PinWindow(self)
            else:
                # 2b. PIN не нужен -> Сразу расшифровываем и показываем Главное Окно
                try:
                    self.decrypted_creds = decrypt_credentials(self.creds, None)
                    self.show_main_window()
                except Exception as e:
                    self.withdraw()
                    messagebox.showerror("Ошибка данных",
                                         f"Не удалось расшифровать данные без PIN. \n{e}\nУдалите credentials.json и перезапустите.")
                    self.quit()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- Методы, вызываемые окнами ---

    def config_saved(self, pin_used):
        # Вызывается из ConfigWindow
        self.creds = load_credentials()
        if pin_used:
            PinWindow(self)  # Показываем окно PIN
        else:
            self.decrypted_creds = decrypt_credentials(self.creds, None)
            self.show_main_window()  # Сразу показываем главное

    def pin_unlocked(self, decrypted_data):
        # Вызывается из PinWindow
        self.decrypted_creds = decrypted_data
        self.show_main_window()

    def show_main_window(self):
        # Собираем главный интерфейс
        self.deiconify()  # Показываем основное окно
        self.main_frame = MainWindow(self)
        self.main_frame.pack(fill="both", expand=True)

    def open_settings_window(self):
        # Вызывается из MainWindow
        if self.decrypted_creds is None and self.creds.get("pin_hash"):
            messagebox.showinfo("Информация", "Сначала нужно разблокировать данные, введя PIN в окне настроек.",
                                parent=self)

        SettingsWindow(self)

    def on_closing(self):
        # При закрытии окна
        if self.monitor_thread and self.monitor_thread.is_alive():
            # Тут должна быть логика остановки монитора, если она есть
            pass
        self.quit()

    # --- Основная логика (в отдельном потоке) ---

    def start_work_thread(self):
        # Запускается по нажатию "Начать работу"
        threading.Thread(target=self.run_work_logic, daemon=True).start()

    def run_work_logic(self):
        try:
            # Получаем расшифрованные данные
            username, password, secret_2fa, start_telemart_flag = self.decrypted_creds

            # --- 1. Проверка Интернета ---
            self.pritunl_status_var.set("🟡 Проверка интернета...")
            if not wait_for_internet():
                self.pritunl_status_var.set("🔴 Интернет недоступен")
                return

            # --- 2. Подключение VPN ---
            vpn_connected = False
            self.pritunl_status_var.set("🟡 Проверка VPN...")
            if vpn.check_vpn_connection():
                print("VPN уже подключен.")
                self.pritunl_status_var.set("🟢 VPN уже подключен")
                vpn_connected = True
            else:
                print("VPN не подключен, начинаем попытки...")
                max_attempts = 5
                attempt = 0
                while attempt < max_attempts and not vpn_connected:
                    attempt += 1
                    self.pritunl_status_var.set(f"🟡 Попытка VPN #{attempt}...")

                    vpn.start_pritunl()
                    vpn.click_pritunl_connect()

                    print("Проверка времени (NTP)...")
                    time_ok, ntp_time = check_time_drift()
                    if not time_ok:
                        print("!!! ВНИМАНИЕ: СИСТЕМНОЕ ВРЕМЯ НЕВЕРНО !!!")

                    totp_code = get_current_totp(secret_2fa, ntp_time=ntp_time)

                    if not vpn.input_2fa_code_and_reconnect(totp_code):
                        print("Не удалось ввести 2FA код.")
                        time.sleep(5)
                        continue

                    print("Ожидание подключения (10 сек)...")
                    time.sleep(10)  # Даем VPN время

                    if vpn.check_vpn_connection():
                        vpn_connected = True
                        self.pritunl_status_var.set("🟢 VPN подключен")
                        print("VPN подключен успешно!")
                    else:
                        print(f"Попытка #{attempt} не удалась.")

            if not vpn_connected:
                self.pritunl_status_var.set("🔴 Не удалось подключиться к VPN")
                self.main_frame.start_button.configure(state="normal", text="Попробовать снова")
                return

            # --- 3. Запуск Telemart ---
            if start_telemart_flag:
                self.telemart_status_var.set("🟡 Запуск Telemart...")
                print("Запускаем Telemart Client...")
                start_telemart()
                time.sleep(5)

                self.telemart_status_var.set("🟡 Вход в Telemart...")
                print("Выполняем вход в Telemart...")
                if login_telemart(username, password):
                    print("Вход в Telemart выполнен!")
                    self.telemart_status_var.set("🟢 Вход выполнен")
                else:
                    print("Ошибка входа в Telemart.")
                    self.telemart_status_var.set("🔴 Ошибка входа")
            else:
                print("Запуск Telemart пропущен (настройка).")
                self.telemart_status_var.set("⚪ Пропущено")

            # --- 4. Запуск Монитора VPN ---
            self.monitor_status_var.set("🟡 Запуск монитора...")
            print("Запуск фонового мониторинга VPN...")

            # ВАЖНО: Монитор тоже должен писать в наш GUI
            # Мы должны передать ему наш логгер.
            # (Сейчас он будет писать в stdout, что уже перехвачено)

            monitor = SimpleVPNMonitor(pin_code=None, secret_2fa=secret_2fa)
            if monitor.start():
                print("VPN Monitor запущен в фоне.")
                self.monitor_status_var.set("🟢 Мониторинг активен")
                # Сохраняем ссылку на поток, чтобы он не умер
                self.monitor_thread = monitor.monitor_thread
            else:
                print("VPN Monitor не запущен.")
                self.monitor_status_var.set("🔴 Ошибка монитора")

            print("=" * 50)
            print("Автоматизация завершена. Система работает.")
            self.main_frame.start_button.configure(text="Запущено")

        except Exception as e:
            print(f"!!! КРИТИЧЕСКАЯ ОШИБКА В РАБОЧЕМ ПОТОКЕ: {e} !!!")
            self.pritunl_status_var.set("🔴 Критическая ошибка")
            self.main_frame.start_button.configure(state="normal", text="Попробовать снова")


if __name__ == "__main__":
    # *** ИЗМЕНЕНО: Принудительно ставим 'Dark' ***
    ctk.set_appearance_mode("Dark")  # System, Dark, Light
    ctk.set_default_color_theme("blue")  # blue, dark-blue, green

    app = App()
    app.mainloop()