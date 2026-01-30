# src/teleauto/gui/windows.py
import customtkinter as ctk
import json
import os
import time
import pyotp
from tkinter import messagebox
from src.teleauto.credentials import save_credentials, load_credentials, verify_pin, decrypt_credentials, \
    clear_credentials
from src.teleauto.localization import tr, set_language, get_language, LANG_CODES, LANG_NAMES
from .constants import FRAME_BG, BORDER_COLOR, CORNER_RADIUS, EMOJI_FONT, MAIN_FONT_FAMILY
from .utils import apply_window_settings
from .widgets import SettingsGroup

PROFILES_FILE = "profiles.json"


class ConfigWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title(tr("window_title_setup"))
        self.geometry("450x750")
        self.transient(master_app)
        self.grab_set()
        self.after(10, lambda: apply_window_settings(self))

        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        f_label = (MAIN_FONT_FAMILY, 12)
        f_entry = (MAIN_FONT_FAMILY, 12)
        f_btn = (MAIN_FONT_FAMILY, 13, "bold")
        f_hint = (MAIN_FONT_FAMILY, 11)

        # Язык
        self.lang_frame = SettingsGroup(self.main_frame, title_key="lang_label")
        self.lang_frame.pack(fill="x", pady=(0, 10))
        self.lang_var = ctk.StringVar(value=LANG_NAMES.get(get_language(), "💩 Russian"))
        self.lang_combo = ctk.CTkOptionMenu(self.lang_frame, values=list(LANG_CODES.keys()),
                                            variable=self.lang_var, command=self.change_lang,
                                            font=EMOJI_FONT, dropdown_font=EMOJI_FONT)
        self.lang_combo.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Безопасность
        self.sec_frame = SettingsGroup(self.main_frame, title_key="group_security")
        self.sec_frame.pack(fill="x", pady=(0, 10))
        self.lbl_pin = ctk.CTkLabel(self.sec_frame, text=tr("pin_label"), font=f_label)
        self.lbl_pin.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pin_entry = ctk.CTkEntry(self.sec_frame, show="*", font=f_entry)
        self.pin_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.lbl_pin_rep = ctk.CTkLabel(self.sec_frame, text=tr("pin_repeat"), font=f_label)
        self.lbl_pin_rep.grid(row=2, column=0, padx=10, pady=(5, 15), sticky="w")
        self.pin_repeat_entry = ctk.CTkEntry(self.sec_frame, show="*", font=f_entry)
        self.pin_repeat_entry.grid(row=2, column=1, padx=10, pady=(5, 15), sticky="ew")

        # Инструкция
        self.vpn_frame = SettingsGroup(self.main_frame, title_key="group_vpn")
        self.vpn_frame.pack(fill="x", pady=(0, 10))

        self.lbl_info = ctk.CTkLabel(self.vpn_frame, text=tr("vpn_instruction"), font=f_hint,
                                     text_color="#FFD700", justify="left", wraplength=380)
        self.lbl_info.grid(row=1, column=0, columnspan=2, padx=10, pady=15, sticky="w")

        # Telemart
        self.tm_frame = SettingsGroup(self.main_frame, title_key="group_tm")
        self.tm_frame.pack(fill="x", pady=(0, 10))
        self.telemart_checkbox = ctk.CTkCheckBox(self.tm_frame, text=tr("auto_start_tm"), font=f_label,
                                                 command=self.toggle_login_fields)
        self.telemart_checkbox.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        self.lbl_path = ctk.CTkLabel(self.tm_frame, text=tr("tm_path_label"), font=f_label)
        self.lbl_path.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.path_entry = ctk.CTkEntry(self.tm_frame, font=f_entry)
        self.path_entry.grid(row=2, column=1, padx=(10, 5), pady=5, sticky="ew")
        self.browse_btn = ctk.CTkButton(self.tm_frame, text="📂", width=40, font=f_btn, command=self.browse_file)
        self.browse_btn.grid(row=2, column=2, padx=(0, 10), pady=5)

        self.lbl_login = ctk.CTkLabel(self.tm_frame, text=tr("login"), font=f_label)
        self.lbl_login.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.login_entry = ctk.CTkEntry(self.tm_frame, font=f_entry)
        self.login_entry.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        self.lbl_pass = ctk.CTkLabel(self.tm_frame, text=tr("password"), font=f_label)
        self.lbl_pass.grid(row=4, column=0, padx=10, pady=(5, 15), sticky="w")
        self.password_entry = ctk.CTkEntry(self.tm_frame, show="*", font=f_entry)
        self.password_entry.grid(row=4, column=1, columnspan=2, padx=10, pady=(5, 15), sticky="ew")

        self.save_btn = ctk.CTkButton(self, text=tr("save_btn"), height=35, font=f_btn, command=self.save_config)
        self.save_btn.pack(padx=20, pady=20, fill="x")

        self.toggle_login_fields()
        self.protocol("WM_DELETE_WINDOW", self.master_app.quit)

    def change_lang(self, choice):
        set_language(LANG_CODES[choice])
        self.refresh_ui()

    def browse_file(self):
        filename = ctk.filedialog.askopenfilename(filetypes=[("Executables", "*.exe"), ("All files", "*.*")])
        if filename:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, filename)

    def refresh_ui(self):
        self.title(tr("window_title_setup"))
        for frame in [self.lang_frame, self.sec_frame, self.vpn_frame, self.tm_frame]: frame.refresh_text()

        self.lbl_pin.configure(text=tr("pin_label"))
        self.lbl_pin_rep.configure(text=tr("pin_repeat"))
        self.lbl_info.configure(text=tr("vpn_instruction"))  # Обновляем инструкцию
        self.telemart_checkbox.configure(text=tr("auto_start_tm"))
        self.lbl_path.configure(text=tr("tm_path_label"))
        self.lbl_login.configure(text=tr("login"))
        self.lbl_pass.configure(text=tr("password"))
        self.save_btn.configure(text=tr("save_btn"))

    def toggle_login_fields(self):
        st = "normal" if self.telemart_checkbox.get() == 1 else "disabled"
        self.login_entry.configure(state=st)
        self.password_entry.configure(state=st)
        self.path_entry.configure(state=st)
        self.browse_btn.configure(state=st)

    def save_config(self):
        pin = self.pin_entry.get()
        if pin != self.pin_repeat_entry.get(): return messagebox.showerror("Error", tr("error_pin_mismatch"))
        secrets_dict = {}
        try:
            save_credentials(self.login_entry.get(), self.password_entry.get(), pin or None, secrets_dict,
                             self.telemart_checkbox.get() == 1, language=get_language(),
                             telemart_path=self.path_entry.get(), manual_offset=0)
            self.destroy()
            self.master_app.config_saved(pin or None)
        except Exception as e:
            messagebox.showerror("Error", str(e))


class PinWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title(tr("window_title_pin"))
        self.geometry("320x180")
        self.transient(master_app)
        self.grab_set()
        self.after(10, lambda: apply_window_settings(self))
        f_msg = (MAIN_FONT_FAMILY, 13)
        f_entry = (MAIN_FONT_FAMILY, 14, "bold")
        f_btn = (MAIN_FONT_FAMILY, 13, "bold")
        self.frame = ctk.CTkFrame(self, fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR,
                                  corner_radius=CORNER_RADIUS)
        self.frame.pack(expand=True, fill="both", padx=15, pady=15)
        self.lbl_msg = ctk.CTkLabel(self.frame, text=tr("pin_enter_msg"), font=f_msg)
        self.lbl_msg.pack(pady=(20, 5))
        self.pin_entry = ctk.CTkEntry(self.frame, show="*", width=200, justify="center", font=f_entry)
        self.pin_entry.pack(pady=10)
        self.pin_entry.bind("<Return>", self.check)
        self.pin_entry.focus()
        self.btn_unlock = ctk.CTkButton(self.frame, text=tr("unlock_btn"), height=35, width=200, font=f_btn,
                                        command=self.check)
        self.btn_unlock.pack(pady=10)
        self.protocol("WM_DELETE_WINDOW", self.master_app.quit)

    def check(self, event=None):
        entered_pin = self.pin_entry.get()
        if verify_pin(self.master_app.creds.get("pin_hash"), entered_pin):
            self.destroy()
            self.master_app.pin_unlocked(entered_pin)
        else:
            messagebox.showerror("Error", tr("error_wrong_pin"))


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title(tr("window_title_settings"))
        self.geometry("500x800")
        self.transient(master_app)
        self.grab_set()
        self.initial_lang = get_language()
        self.selected_lang = get_language()
        self.after(10, lambda: apply_window_settings(self))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        f_label = (MAIN_FONT_FAMILY, 12)
        f_entry = (MAIN_FONT_FAMILY, 12)
        f_btn = (MAIN_FONT_FAMILY, 13, "bold")
        f_code = ("Consolas", 14, "bold")

        self.sv_dict = {}
        self.lv = ctk.StringVar()
        self.pv = ctk.StringVar()
        self.tm_path_var = ctk.StringVar()
        self.offset_var = ctk.StringVar(value="0")

        self.pin_frame = SettingsGroup(self, title_key="group_access")
        self.pin_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        self.lbl_pin_s = ctk.CTkLabel(self.pin_frame, text=tr("label_pin_short"), font=f_label)
        self.lbl_pin_s.grid(row=1, column=0, padx=10, pady=10)
        self.pin_ent = ctk.CTkEntry(self.pin_frame, show="*", font=f_entry)
        self.pin_ent.grid(row=1, column=1, sticky="ew", padx=5)
        self.unlock_btn = ctk.CTkButton(self.pin_frame, text=tr("unlock_btn"), width=80, height=28,
                                        font=(MAIN_FONT_FAMILY, 11, "bold"), command=self.unlock)
        self.unlock_btn.grid(row=1, column=2, padx=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # Язык
        self.lang_frame = SettingsGroup(self.scroll_frame, title_key="lang_label")
        self.lang_frame.pack(fill="x", pady=(0, 10))
        self.lang_var = ctk.StringVar(value=LANG_NAMES.get(get_language(), "💩 Russian"))
        self.lang_combo = ctk.CTkOptionMenu(self.lang_frame, values=list(LANG_CODES.keys()), variable=self.lang_var,
                                            command=self.change_lang_setting, state="disabled", font=EMOJI_FONT,
                                            dropdown_font=EMOJI_FONT)
        self.lang_combo.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # --- БЛОК ВРЕМЕНИ И ОФФСЕТА ---
        self.time_frame = SettingsGroup(self.scroll_frame, title_key="group_time")
        self.time_frame.pack(fill="x", pady=(0, 10))

        self.lbl_offset_title = ctk.CTkLabel(self.time_frame, text=tr("offset_label"), font=f_label)
        self.lbl_offset_title.grid(row=1, column=0, padx=10, pady=10, sticky="w")

        self.offset_ent = ctk.CTkEntry(self.time_frame, textvariable=self.offset_var, state="disabled", font=f_entry,
                                       width=80)
        self.offset_ent.grid(row=1, column=1, sticky="w", padx=5)

        self.lbl_offset_hint = ctk.CTkLabel(self.time_frame, text=tr("offset_hint"), text_color="grey",
                                            font=(MAIN_FONT_FAMILY, 10))
        self.lbl_offset_hint.grid(row=1, column=2, sticky="w", padx=5)

        # --- ДИНАМИЧЕСКИЙ БЛОК VPN ---
        self.vpn_frame = SettingsGroup(self.scroll_frame, title_key="group_vpn")
        self.vpn_frame.pack(fill="x", pady=(0, 10))

        self.discovered_profiles = []
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                    self.discovered_profiles = json.load(f)
            except:
                pass

        self.secret_entries = {}
        self.totp_labels = {}

        if not self.discovered_profiles:
            self.lbl_no_prof = ctk.CTkLabel(self.vpn_frame, text=tr("error_no_profiles"),
                                            text_color="#FFD700", font=f_label)
            self.lbl_no_prof.grid(row=1, column=0, columnspan=3, pady=10)
        else:
            for idx, p_name in enumerate(self.discovered_profiles):
                row_idx = idx + 1
                is_last = (idx == len(self.discovered_profiles) - 1)
                pady_val = (5, 15) if is_last else 5

                # Имя
                lbl = ctk.CTkLabel(self.vpn_frame, text=p_name, font=f_label, anchor="w", width=120)
                lbl.grid(row=row_idx, column=0, sticky="w", padx=10, pady=pady_val)

                # Поле ввода
                sv = ctk.StringVar()
                self.sv_dict[p_name] = sv
                ent = ctk.CTkEntry(self.vpn_frame, textvariable=sv, show="*", state="disabled", font=f_entry, width=140)
                ent.grid(row=row_idx, column=1, sticky="ew", padx=(5, 5), pady=pady_val)
                self.secret_entries[p_name] = ent

                # Лейбл для кода
                code_lbl = ctk.CTkLabel(self.vpn_frame, text="--- ---", font=f_code, text_color="#00FF00", width=80)
                code_lbl.grid(row=row_idx, column=2, sticky="e", padx=(5, 10), pady=pady_val)
                self.totp_labels[p_name] = code_lbl

        # Telemart
        self.tm_frame = SettingsGroup(self.scroll_frame, title_key="group_tm")
        self.tm_frame.pack(fill="x", pady=(0, 10))
        self.cb = ctk.CTkCheckBox(self.tm_frame, text=tr("auto_start_tm"), state="disabled", font=f_label,
                                  command=self.upd)
        self.cb.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        self.lbl_path = ctk.CTkLabel(self.tm_frame, text=tr("tm_path_label"), font=f_label)
        self.lbl_path.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.path_ent = ctk.CTkEntry(self.tm_frame, textvariable=self.tm_path_var, state="disabled", font=f_entry)
        self.path_ent.grid(row=2, column=1, sticky="ew", padx=(10, 5), pady=5)
        self.browse_btn = ctk.CTkButton(self.tm_frame, text="📂", width=40, state="disabled", font=f_btn,
                                        command=self.browse_file)
        self.browse_btn.grid(row=2, column=2, padx=(0, 10), pady=5)

        self.lbl_login = ctk.CTkLabel(self.tm_frame, text=tr("login"), font=f_label)
        self.lbl_login.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.le = ctk.CTkEntry(self.tm_frame, textvariable=self.lv, state="disabled", font=f_entry)
        self.le.grid(row=3, column=1, columnspan=2, sticky="ew", padx=10, pady=5)
        self.lbl_pass = ctk.CTkLabel(self.tm_frame, text=tr("password"), font=f_label)
        self.lbl_pass.grid(row=4, column=0, padx=10, pady=(5, 15), sticky="w")
        self.pe = ctk.CTkEntry(self.tm_frame, textvariable=self.pv, show="*", state="disabled", font=f_entry)
        self.pe.grid(row=4, column=1, columnspan=2, sticky="ew", padx=10, pady=(5, 15))

        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=15)
        self.actions_frame.grid_columnconfigure(0, weight=1)
        self.save_btn = ctk.CTkButton(self.actions_frame, text=tr("save_changes_btn"), height=35, state="disabled",
                                      font=f_btn, command=self.save)
        self.save_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.del_btn = ctk.CTkButton(self.actions_frame, text=tr("delete_btn"), height=35, fg_color="#AA0000",
                                     hover_color="#880000", font=f_btn, command=self.delete)
        self.del_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.is_window_open = True
        self.update_totp_preview()

        if self.master_app.creds.get("start_telemart"): self.cb.select()
        if not self.master_app.creds.get("pin_hash"): self.pin_frame.grid_forget(); self.unlock(True)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.is_window_open = False
        self.destroy()

    def update_totp_preview(self):
        if not self.is_window_open: return

        try:
            offset_val = int(self.offset_var.get())
        except:
            offset_val = 0

        current_ts = time.time() + offset_val

        for p_name, lbl in self.totp_labels.items():
            secret = self.sv_dict[p_name].get().replace(" ", "")
            if secret:
                try:
                    totp = pyotp.TOTP(secret)
                    code = totp.at(current_ts)
                    lbl.configure(text=f"{code[:3]} {code[3:]}", text_color="#00FF00")
                except:
                    lbl.configure(text="Invalid", text_color="#FF0000")
            else:
                lbl.configure(text="--- ---", text_color="grey")

        self.after(1000, self.update_totp_preview)

    def change_lang_setting(self, lang):
        self.selected_lang = LANG_CODES[lang]
        # Для обновления на лету (частично, полная смена при перезагрузке)
        set_language(self.selected_lang)
        self.refresh_ui()

    def browse_file(self):
        filename = ctk.filedialog.askopenfilename(filetypes=[("Executables", "*.exe"), ("All files", "*.*")])
        if filename:
            self.tm_path_var.set(filename)

    def refresh_ui(self):
        self.title(tr("window_title_settings"))
        # Обновляем заголовки групп
        for frame in [self.lang_frame, self.time_frame, self.vpn_frame, self.tm_frame, self.pin_frame]:
            frame.refresh_text()

        self.lbl_pin_s.configure(text=tr("label_pin_short"))
        self.unlock_btn.configure(text=tr("unlock_btn"))

        self.lbl_offset_title.configure(text=tr("offset_label"))
        self.lbl_offset_hint.configure(text=tr("offset_hint"))

        if hasattr(self, 'lbl_no_prof'):
            self.lbl_no_prof.configure(text=tr("error_no_profiles"))

        self.cb.configure(text=tr("auto_start_tm"))
        self.lbl_path.configure(text=tr("tm_path_label"))
        self.lbl_login.configure(text=tr("login"))
        self.lbl_pass.configure(text=tr("password"))
        self.save_btn.configure(text=tr("save_changes_btn"))
        self.del_btn.configure(text=tr("delete_btn"))

    def upd(self):
        st = "normal" if (self.cb.get() == 1 and self.save_btn.cget("state") == "normal") else "disabled"
        self.le.configure(state=st)
        self.pe.configure(state=st)
        self.path_ent.configure(state=st)
        self.browse_btn.configure(state=st)
        self.offset_ent.configure(state=st)

    def unlock(self, no_pin=False):
        try:
            pin_val = None if no_pin else self.pin_ent.get().strip()
            d = decrypt_credentials(self.master_app.creds, pin_val)

            self.lv.set(d[0])
            self.pv.set(d[1])

            saved_secrets = d[2]
            for p_name, sv in self.sv_dict.items():
                if p_name in saved_secrets:
                    sv.set(saved_secrets[p_name])

            if d[3]: self.cb.select()
            if len(d) > 5: self.tm_path_var.set(d[5])
            if len(d) > 6: self.offset_var.set(str(d[6]))

            for w in self.secret_entries.values(): w.configure(state="normal")

            for w in [self.cb, self.lang_combo, self.path_ent, self.browse_btn, self.offset_ent]:
                w.configure(state="normal")
            self.save_btn.configure(state="normal")
            self.upd()
            if not no_pin: self.pin_frame.grid_forget()
            del d
        except Exception as e:
            # print(e)
            messagebox.showerror("Error", tr("error_wrong_pin"))

    def save(self):
        try:
            pin = self.pin_ent.get().strip() if self.master_app.creds.get("pin_hash") else None

            secrets_to_save = {}
            for p_name, sv in self.sv_dict.items():
                val = sv.get().strip()
                if val:
                    secrets_to_save[p_name] = val

            try:
                offset_to_save = int(self.offset_var.get())
            except:
                offset_to_save = 0

            save_credentials(self.lv.get(), self.pv.get(), pin, secrets_to_save,
                             self.cb.get() == 1, language=self.selected_lang,
                             telemart_path=self.tm_path_var.get(),
                             manual_offset=offset_to_save)

            self.master_app.creds = load_credentials()
            self.master_app.user_pin = pin
            self.master_app.update_main_window_buttons()
            if self.selected_lang != self.initial_lang: messagebox.showinfo(tr("restart_title"), tr("restart_msg"))
            self.on_close()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete(self):
        if messagebox.askyesno("Reset", tr("delete_confirm")): clear_credentials(); self.master_app.quit()