# gui.py
import customtkinter as ctk
import threading
import sys
import os
import time
from tkinter import messagebox
from PIL import Image, ImageDraw

# --- Импорт логики ---
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
    sys.exit(1)

# === КОНСТАНТЫ ДИЗАЙНА ===
ROW_HEIGHT = 35
CORNER_RADIUS = 6


# --- Виджет Светодиода (Сглаженный через PIL) ---
class LEDCircle(ctk.CTkLabel):
    def __init__(self, master, size=15, fg_color="transparent", **kwargs):
        super().__init__(master, text="", width=size, height=size, fg_color=fg_color, **kwargs)
        self.size = size

        # Цвета
        self.colors = {
            "off": "#151515",
            "shadow": "#111111",
            "working": "#FFD700",
            "working_dim": "#8B7500",
            "success": "#00DD00",
            "error": "#FF4444"
        }

        self._state = "off"
        self._blink_job = None
        self._blink_state = False

        # Кэш для изображений
        self._images = {}

        # Генерируем состояния
        for k, c in self.colors.items():
            if k != "shadow":
                self._images[k] = self._draw_circle(c)

        # Устанавливаем начальное состояние
        self.set_state("off")

    def _draw_circle(self, color):
        """Рисует сглаженный круг через PIL"""
        scale = 4  # Супер-сэмплинг
        s = int(self.size * scale)
        pad = int(4 * scale)

        image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Тень
        draw.ellipse((0, 0, s - 1, s - 1), fill=self.colors["shadow"])
        # Огонек
        draw.ellipse((pad, pad, s - pad - 1, s - pad - 1), fill=color)

        # Сглаживание
        image = image.resize((self.size, self.size), Image.Resampling.LANCZOS)

        return ctk.CTkImage(light_image=image, dark_image=image, size=(self.size, self.size))

    def start_blinking(self):
        if self._blink_job is None: self._blink_loop()

    def stop_blinking(self):
        if self._blink_job:
            self.after_cancel(self._blink_job)
            self._blink_job = None

    def _blink_loop(self):
        key = "working" if self._blink_state else "working_dim"
        self.configure(image=self._images[key])
        self._blink_state = not self._blink_state
        self._blink_job = self.after(600, self._blink_loop)

    def set_state(self, state):
        self.stop_blinking()
        self._state = state

        if state == "waiting":
            self.start_blinking()
        else:
            self.configure(image=self._images.get(state, self._images["off"]))


# --- TitleBox (Название + Лампочка) ---
class TitleBox(ctk.CTkFrame):
    def __init__(self, master, title, **kwargs):
        super().__init__(master, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                         fg_color="#181818", border_width=1, border_color="#333333", **kwargs)
        self.pack_propagate(False)

        # Лампочка
        self.led = LEDCircle(self, size=15, fg_color="#181818")
        self.led.place(x=10, rely=0.5, anchor="w")

        # Текст
        self.label = ctk.CTkLabel(self, text=title, text_color="#E0E0E0", font=ctk.CTkFont(size=13, weight="bold"))
        self.label.place(x=33, rely=0.53, anchor="w")

    def set_led(self, state):
        self.led.set_state(state)


# --- StatusBox (Текст статуса) ---
class StatusBox(ctk.CTkFrame):
    def __init__(self, master, text="Ожидание", **kwargs):
        super().__init__(master, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                         fg_color="#181818", border_width=1, border_color="#333333", **kwargs)
        self.pack_propagate(False)

        self.label = ctk.CTkLabel(self, text=text, text_color="#777777", font=ctk.CTkFont(size=12))
        self.label.place(relx=0.5, rely=0.53, anchor="center")

    def set_text(self, text, state):
        self.label.configure(text=text)
        if state == "success":
            self.label.configure(text_color="#44DD44")
        elif state == "error":
            self.label.configure(text_color="#FF5555")
        elif state == "working":
            self.label.configure(text_color="#FFD700")
        else:
            self.label.configure(text_color="#777777")


# --- Logger ---
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


# --- Config Window ---
class ConfigWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title("Первичная настройка")
        self.geometry("450x550")
        self.transient(master_app)
        self.grab_set()
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="PIN-код:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.pin_entry = ctk.CTkEntry(self, show="*")
        self.pin_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Повторите PIN:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pin_repeat_entry = ctk.CTkEntry(self, show="*")
        self.pin_repeat_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Секрет 2FA (1):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.secret_entry_1 = ctk.CTkEntry(self, show="*")
        self.secret_entry_1.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Секрет 2FA (2):").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.secret_entry_2 = ctk.CTkEntry(self, show="*")
        self.secret_entry_2.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Секрет 2FA (3):").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.secret_entry_3 = ctk.CTkEntry(self, show="*")
        self.secret_entry_3.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Оставьте пустым, если не используется.", font=ctk.CTkFont(size=10)).grid(row=5,
                                                                                                          column=0,
                                                                                                          columnspan=2,
                                                                                                          padx=10)

        self.telemart_checkbox = ctk.CTkCheckBox(self, text="Автозапуск Telemart", command=self.toggle_login_fields)
        self.telemart_checkbox.grid(row=7, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(self, text="Логин:").grid(row=8, column=0, padx=10, pady=5, sticky="w")
        self.login_entry = ctk.CTkEntry(self)
        self.login_entry.grid(row=8, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Пароль:").grid(row=9, column=0, padx=10, pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(self, show="*")
        self.password_entry.grid(row=9, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(self, text="Сохранить", command=self.save_config).grid(row=10, column=0, columnspan=2, pady=20)
        self.toggle_login_fields()
        self.protocol("WM_DELETE_WINDOW", self.master_app.quit)

    def toggle_login_fields(self):
        st = "normal" if self.telemart_checkbox.get() == 1 else "disabled"
        self.login_entry.configure(state=st)
        self.password_entry.configure(state=st)

    def save_config(self):
        pin = self.pin_entry.get()
        if pin != self.pin_repeat_entry.get(): return messagebox.showerror("Ошибка", "PIN не совпадают.")
        secrets = [self.secret_entry_1.get().strip(), self.secret_entry_2.get().strip(),
                   self.secret_entry_3.get().strip()]
        if not any(secrets): return messagebox.showerror("Ошибка", "Нужен хотя бы один секрет.")

        try:
            save_credentials(self.login_entry.get(), self.password_entry.get(), pin or None, secrets,
                             self.telemart_checkbox.get() == 1)
            self.master_app.config_saved(pin or None)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


# --- Pin Window ---
class PinWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title("Ввод PIN")
        self.geometry("300x160")
        self.transient(master_app)
        self.grab_set()

        ctk.CTkLabel(self, text="Введите ваш PIN-код:").pack(pady=(15, 5))

        self.pin_entry = ctk.CTkEntry(self, show="*", width=200)
        self.pin_entry.pack(pady=5)
        self.pin_entry.bind("<Return>", self.check)
        self.pin_entry.focus()

        ctk.CTkButton(self, text="Войти", command=self.check).pack(pady=10)
        self.protocol("WM_DELETE_WINDOW", self.master_app.quit)

    def check(self, event=None):
        if verify_pin(self.master_app.creds.get("pin_hash"), self.pin_entry.get()):
            try:
                self.master_app.pin_unlocked(decrypt_credentials(self.master_app.creds, self.pin_entry.get()))
                self.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
        else:
            messagebox.showerror("Ошибка", "Неверный PIN")


# --- Settings Window ---
class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title("Настройки")
        self.geometry("500x600")
        self.transient(master_app)
        self.grab_set()
        self.grid_columnconfigure(1, weight=1)

        self.sv1 = ctk.StringVar();
        self.sv2 = ctk.StringVar();
        self.sv3 = ctk.StringVar()
        self.lv = ctk.StringVar();
        self.pv = ctk.StringVar()

        self.pin_frame = ctk.CTkFrame(self)
        self.pin_frame.grid(row=0, columnspan=2, sticky="ew", padx=10, pady=10)
        ctk.CTkLabel(self.pin_frame, text="PIN:").pack(side="left", padx=5)
        self.pin_ent = ctk.CTkEntry(self.pin_frame, show="*")
        self.pin_ent.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(self.pin_frame, text="Разблокировать", command=self.unlock).pack(side="left", padx=5)

        self.sf = ctk.CTkFrame(self)
        self.sf.grid(row=1, columnspan=2, sticky="ew", padx=10)
        self.sf.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.sf, text="Секрет 1:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(self.sf, textvariable=self.sv1, state="disabled").grid(row=0, column=1, sticky="ew", pady=5,
                                                                            padx=5)

        ctk.CTkLabel(self.sf, text="Секрет 2:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(self.sf, textvariable=self.sv2, state="disabled").grid(row=1, column=1, sticky="ew", pady=5,
                                                                            padx=5)

        ctk.CTkLabel(self.sf, text="Секрет 3:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(self.sf, textvariable=self.sv3, state="disabled").grid(row=2, column=1, sticky="ew", pady=5,
                                                                            padx=5)

        self.cb = ctk.CTkCheckBox(self.sf, text="Автозапуск Telemart", state="disabled", command=self.upd)
        self.cb.grid(row=4, column=0, columnspan=2, pady=15, padx=5, sticky="w")

        ctk.CTkLabel(self.sf, text="Логин:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.le = ctk.CTkEntry(self.sf, textvariable=self.lv, state="disabled")
        self.le.grid(row=5, column=1, sticky="ew", pady=5, padx=5)

        ctk.CTkLabel(self.sf, text="Пароль:").grid(row=6, column=0, padx=5, pady=5, sticky="w")
        self.pe = ctk.CTkEntry(self.sf, textvariable=self.pv, show="*", state="disabled")
        self.pe.grid(row=6, column=1, sticky="ew", pady=5, padx=5)

        self.save_btn = ctk.CTkButton(self, text="Сохранить изменения", state="disabled", command=self.save)
        self.save_btn.grid(row=2, columnspan=2, pady=20)

        ctk.CTkButton(self, text="Удалить все данные", fg_color="#D00", hover_color="#A00", command=self.delete).grid(
            row=3, columnspan=2)

        if self.master_app.creds.get("start_telemart"): self.cb.select()
        if not self.master_app.creds.get("pin_hash"): self.pin_frame.grid_forget(); self.unlock(True)

    def upd(self):
        st = "normal" if (self.cb.get() == 1 and self.save_btn.cget("state") == "normal") else "disabled"
        self.le.configure(state=st)
        self.pe.configure(state=st)

    def unlock(self, no_pin=False):
        try:
            d = decrypt_credentials(self.master_app.creds, None if no_pin else self.pin_ent.get())
            self.lv.set(d[0]);
            self.pv.set(d[1]);
            self.sv1.set(d[2][0]);
            self.sv2.set(d[2][1]);
            self.sv3.set(d[2][2])
            if d[3]: self.cb.select()
            for w in self.sf.winfo_children():
                if isinstance(w, (ctk.CTkEntry, ctk.CTkCheckBox, ctk.CTkButton)): w.configure(state="normal")
            self.save_btn.configure(state="normal")
            self.upd()
            self.pin_frame.grid_forget()
        except:
            messagebox.showerror("Ошибка", "Ошибка разблокировки")

    def save(self):
        try:
            save_credentials(self.lv.get(), self.pv.get(), self.pin_ent.get() or None,
                             [self.sv1.get(), self.sv2.get(), self.sv3.get()], self.cb.get() == 1)
            self.master_app.creds = load_credentials()
            self.master_app.decrypted_creds = decrypt_credentials(self.master_app.creds, self.pin_ent.get() or None)
            self.master_app.update_main_window_buttons()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def delete(self):
        if messagebox.askyesno("Удаление", "Вы уверены? Это удалит credentials.json"):
            clear_credentials()
            self.master_app.quit()


# --- MAIN WINDOW ---
class MainWindow(ctk.CTkFrame):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        # --- ВЕРХНЯЯ ПАНЕЛЬ ---
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=(5, 0), sticky="ew")

        self.top_frame.grid_columnconfigure(0, weight=1)
        self.top_frame.grid_columnconfigure(1, weight=1)
        self.top_frame.grid_columnconfigure(2, weight=0)

        # 1. Версия
        self.version_frame = ctk.CTkFrame(self.top_frame, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                                          fg_color="#181818", border_width=1, border_color="#333333")
        self.version_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.version_frame.pack_propagate(False)
        self.version_label = ctk.CTkLabel(self.version_frame, text="v1.0 release", text_color="#666666",
                                          font=ctk.CTkFont(size=12))
        self.version_label.place(relx=0.5, rely=0.53, anchor="center")

        # 2. Статус Обновления
        self.update_frame = ctk.CTkFrame(self.top_frame, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                                         fg_color="#181818", border_width=1, border_color="#333333")
        self.update_frame.grid(row=0, column=1, sticky="ew", padx=(5, 5))
        self.update_frame.pack_propagate(False)

        self.update_inner = ctk.CTkFrame(self.update_frame, fg_color="transparent")
        self.update_inner.place(relx=0.5, rely=0.53, anchor="center")

        ctk.CTkLabel(self.update_inner, text="Обновление", text_color="#AAAAAA", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(0, 8))
        self.update_led = LEDCircle(self.update_inner, size=15, fg_color="#181818")
        self.update_led.pack(side="left", padx=(0, 8))
        self.update_led.set_state("success")
        self.update_label = ctk.CTkLabel(self.update_inner, text="Актуально", text_color="#666666",
                                         font=ctk.CTkFont(size=12))
        self.update_label.pack(side="left")

        # 3. Настройки (Вернулись к CTkButton)
        self.settings_btn = ctk.CTkButton(self.top_frame, text="⚙️", width=35, height=ROW_HEIGHT,
                                          fg_color="#181818", border_width=1, border_color="#333333",
                                          text_color="#AAA", hover_color="#333",
                                          command=self.master_app.open_settings_window)
        self.settings_btn.grid(row=0, column=2, sticky="e", padx=(5, 0))

        # --- КОНТЕНТ ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="nsew")

        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=1)
        self.content_frame.grid_columnconfigure(2, weight=0)

        # === Ряд 1: Telemart ===
        self.telemart_title = TitleBox(self.content_frame, title="Telemart")
        self.telemart_title.grid(row=0, column=0, padx=(0, 5), pady=8, sticky="ew")

        self.telemart_status = StatusBox(self.content_frame, text="Ожидание")
        self.telemart_status.grid(row=0, column=1, padx=(5, 5), pady=8, sticky="ew")

        self.start_telemart_button = ctk.CTkButton(self.content_frame, text="Start",
                                                   width=125, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                                                   state="disabled",
                                                   command=self.master_app.on_start_telemart_click)
        self.start_telemart_button.grid(row=0, column=2, padx=(5, 0), pady=8, sticky="e")

        # === Ряд 2: Pritunl ===
        self.pritunl_title = TitleBox(self.content_frame, title="Pritunl")
        self.pritunl_title.grid(row=1, column=0, padx=(0, 5), pady=8, sticky="ew")

        self.pritunl_status = StatusBox(self.content_frame, text="Ожидание")
        self.pritunl_status.grid(row=1, column=1, padx=(5, 5), pady=8, sticky="ew")

        self.pritunl_buttons_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.pritunl_buttons_frame.grid(row=1, column=2, padx=(5, 0), pady=8, sticky="e")

        # Кнопки P1/P2/P3
        self.pritunl_btn_1 = ctk.CTkButton(self.pritunl_buttons_frame, text="P1", height=ROW_HEIGHT,
                                           corner_radius=CORNER_RADIUS,
                                           command=lambda: self.master_app.on_pritunl_connect_click(0))
        self.pritunl_btn_2 = ctk.CTkButton(self.pritunl_buttons_frame, text="P2", height=ROW_HEIGHT,
                                           corner_radius=CORNER_RADIUS,
                                           command=lambda: self.master_app.on_pritunl_connect_click(1))
        self.pritunl_btn_3 = ctk.CTkButton(self.pritunl_buttons_frame, text="P3", height=ROW_HEIGHT,
                                           corner_radius=CORNER_RADIUS,
                                           command=lambda: self.master_app.on_pritunl_connect_click(2))

        # === Ряд 3: Monitor ===
        self.monitor_title = TitleBox(self.content_frame, title="Monitor")
        self.monitor_title.grid(row=2, column=0, padx=(0, 5), pady=8, sticky="ew")

        self.monitor_status = StatusBox(self.content_frame, text="Ожидание")
        self.monitor_status.grid(row=2, column=1, padx=(5, 5), pady=8, sticky="ew")

        self.disconnect_button = ctk.CTkButton(self.content_frame, text="Disconnect",
                                               width=125, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                                               state="disabled",
                                               fg_color="grey",
                                               command=self.master_app.on_disconnect_click)
        self.disconnect_button.grid(row=2, column=2, padx=(5, 0), pady=8, sticky="e")

        # --- Лог ---
        self.log_textbox = ctk.CTkTextbox(self, state=ctk.NORMAL, height=200, fg_color="#111", text_color="#CCC")
        self.is_expanded = False

    def expand_log(self):
        if self.is_expanded: return
        self.is_expanded = True
        current_w = self.master_app.winfo_width()
        self.master_app.geometry(f"{current_w}x600")
        self.log_textbox.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)
        logger = TextboxLogger(self.log_textbox)
        sys.stdout = logger
        sys.stderr = logger

    def update_panel_safe(self, panel_name, state, text):
        title_box, status_box = None, None
        if panel_name == 'telemart':
            title_box, status_box = self.telemart_title, self.telemart_status
        elif panel_name == 'pritunl':
            title_box, status_box = self.pritunl_title, self.pritunl_status
        elif panel_name == 'monitor':
            title_box, status_box = self.monitor_title, self.monitor_status
        if title_box and status_box:
            self.after(0, lambda: title_box.set_led(state))
            self.after(0, lambda: status_box.set_text(text, state))


# --- APP CONTROLLER ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.creds = load_credentials()
        self.decrypted_creds = None
        self.monitor_instance = None
        self.monitor_thread = None
        self.main_frame = None
        self.vpn_is_connected = False
        self.title("TeleAuto");
        self.geometry("550x280");
        self.resizable(False, False)

        if not self.creds:
            self.withdraw(); ConfigWindow(self)
        else:
            if self.creds.get("pin_hash"):
                self.withdraw(); PinWindow(self)
            else:
                try:
                    self.decrypted_creds = decrypt_credentials(self.creds, None); self.show_main_window()
                except Exception as e:
                    messagebox.showerror("Error", str(e)); self.quit()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def config_saved(self, pin_used):
        self.creds = load_credentials()
        if pin_used:
            PinWindow(self)
        else:
            self.decrypted_creds = decrypt_credentials(self.creds, None); self.show_main_window()

    def pin_unlocked(self, data):
        self.decrypted_creds = data
        self.show_main_window()

    def show_main_window(self):
        self.deiconify();
        self.main_frame = MainWindow(self);
        self.main_frame.pack(fill="both", expand=True)
        self.main_frame.expand_log();
        self.geometry("650x600");
        self.resizable(True, True)
        self.update_main_window_buttons()
        print("--- Запуск Системы ---");
        self.on_disconnect_click(startup=True)

    def set_ui_status(self, target, state, text):
        if self.main_frame: self.main_frame.update_panel_safe(target, state, text)

    def update_main_window_buttons(self, is_busy=False):
        if not self.main_frame: return
        secrets = self.decrypted_creds[2]
        buttons = [self.main_frame.pritunl_btn_1, self.main_frame.pritunl_btn_2, self.main_frame.pritunl_btn_3]
        active = [i for i, s in enumerate(secrets) if s]
        count = len(active)

        total = 125;
        spacing = 5
        w = (total - (count - 1) * spacing) // count if count > 0 else 0

        for btn in buttons: btn.pack_forget()
        for i, btn in enumerate(buttons):
            if i in active:
                is_last = (i == active[-1])
                px = (0, 0) if is_last else (0, spacing)

                # Стандартный configure для CTkButton
                btn.configure(width=w, height=ROW_HEIGHT)
                btn.pack(side="left", padx=px)

                state = "disabled" if (is_busy or self.vpn_is_connected) else "normal"
                btn.configure(state=state)

        state = "disabled" if is_busy else ("normal" if self.vpn_is_connected else "disabled")
        self.main_frame.start_telemart_button.configure(state=state)
        self.main_frame.disconnect_button.configure(state=state)
        if not is_busy and not self.vpn_is_connected:
            self.main_frame.start_telemart_button.configure(state="disabled")
            self.main_frame.disconnect_button.configure(state="disabled")
            for i, btn in enumerate(buttons):
                if i in active: btn.configure(state="normal")

    def open_settings_window(self):
        SettingsWindow(self)

    def on_closing(self):
        if self.monitor_instance: self.monitor_instance.stop()
        self.quit()

    # --- LOGIC ---
    def on_pritunl_connect_click(self, idx):
        if not self.main_frame.is_expanded: self.main_frame.expand_log()
        self.update_main_window_buttons(is_busy=True)
        threading.Thread(target=self.run_pritunl, args=(idx,), daemon=True).start()

    def on_start_telemart_click(self):
        if not self.main_frame.is_expanded: self.main_frame.expand_log()
        self.main_frame.start_telemart_button.configure(state="disabled")
        threading.Thread(target=self.run_telemart, daemon=True).start()

    def on_disconnect_click(self, startup=False):
        if not self.main_frame.is_expanded and not startup: self.main_frame.expand_log()
        self.update_main_window_buttons(is_busy=True)
        self.set_ui_status("pritunl", "waiting", "Отключение...")
        threading.Thread(target=self.run_disconnect, args=(startup,), daemon=True).start()

    def run_disconnect(self, startup=False):
        try:
            if self.monitor_instance: self.monitor_instance.stop(); self.monitor_instance = None
            if vpn.check_vpn_connection(): vpn.disconnect_vpn(); vpn.wait_for_disconnect()
            self.vpn_is_connected = False
        except Exception as e:
            print(e)
        finally:
            self.set_ui_status("pritunl", "off", "Отключен")
            self.set_ui_status("telemart", "off", "Ожидание")
            self.set_ui_status("monitor", "off", "Ожидание")
            self.update_main_window_buttons(is_busy=False)

    def run_pritunl(self, idx):
        try:
            self.set_ui_status("pritunl", "waiting", "Интернет...")
            if not wait_for_internet():
                self.set_ui_status("pritunl", "error", "Нет сети");
                self.update_main_window_buttons();
                return

            secret = self.decrypted_creds[2][idx]
            attempt = 0
            while attempt < 5 and not self.vpn_is_connected:
                attempt += 1
                self.set_ui_status("pritunl", "working", f"Попытка {attempt}...")
                vpn.start_pritunl()
                if not vpn.click_pritunl_connect(profile_index=idx): time.sleep(2); continue

                ok, ntp = check_time_drift()
                totp = get_current_totp(secret, ntp_time=ntp)
                if not vpn.input_2fa_code_and_reconnect(totp): time.sleep(2); continue

                time.sleep(10)
                if vpn.check_vpn_connection():
                    self.vpn_is_connected = True
                    self.set_ui_status("pritunl", "success", "Подключено")

            if not self.vpn_is_connected:
                self.set_ui_status("pritunl", "error", "Сбой")
            else:
                self.start_monitor(idx, secret)
            self.update_main_window_buttons()
        except Exception as e:
            print(e);
            self.set_ui_status("pritunl", "error", "Ошибка");
            self.update_main_window_buttons()

    def run_telemart(self):
        try:
            if not self.vpn_is_connected: return
            self.set_ui_status("telemart", "working", "Запуск...")
            start_telemart();
            time.sleep(5)
            self.set_ui_status("telemart", "working", "Вход...")
            u, p, _, _ = self.decrypted_creds
            if login_telemart(u, p):
                self.set_ui_status("telemart", "success", "Готово")
            else:
                self.set_ui_status("telemart", "error", "Ошибка")
        except Exception as e:
            print(e); self.set_ui_status("telemart", "error", "Сбой")
        finally:
            self.main_frame.start_telemart_button.configure(state="normal")

    def start_monitor(self, idx, secret):
        self.set_ui_status("monitor", "working", "Запуск...")
        m = SimpleVPNMonitor(pin_code=None, secret_2fa=secret, profile_index=idx)
        if m.start():
            self.set_ui_status("monitor", "success", "Активен")
            self.monitor_instance = m
        else:
            self.set_ui_status("monitor", "error", "Ошибка")


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()