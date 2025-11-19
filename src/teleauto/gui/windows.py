import customtkinter as ctk
from tkinter import messagebox
from src.teleauto.credentials import save_credentials, load_credentials, verify_pin, decrypt_credentials, \
    clear_credentials
from src.teleauto.localization import tr, set_language, get_language, LANG_CODES, LANG_NAMES
from .constants import FRAME_BG, BORDER_COLOR, CORNER_RADIUS
from .utils import apply_window_settings
from .widgets import SettingsGroup, LanguageSelector


class ConfigWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.title(tr("window_title_setup"))
        self.geometry("450x680")
        self.transient(master_app)
        self.after(10, lambda: apply_window_settings(self))

        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Lang
        self.lang_frame = SettingsGroup(self.main_frame, title_key="lang_label")
        self.lang_frame.pack(fill="x", pady=(0, 10))
        self.lang_selector = LanguageSelector(self.lang_frame, current_lang=get_language(), callback=self.change_lang)
        self.lang_selector.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        # Security
        self.sec_frame = SettingsGroup(self.main_frame, title_key="group_security")
        self.sec_frame.pack(fill="x", pady=(0, 10))
        self.lbl_pin = ctk.CTkLabel(self.sec_frame, text=tr("pin_label"));
        self.lbl_pin.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pin_entry = ctk.CTkEntry(self.sec_frame, show="*");
        self.pin_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.lbl_pin_rep = ctk.CTkLabel(self.sec_frame, text=tr("pin_repeat"));
        self.lbl_pin_rep.grid(row=2, column=0, padx=10, pady=(5, 15), sticky="w")
        self.pin_repeat_entry = ctk.CTkEntry(self.sec_frame, show="*");
        self.pin_repeat_entry.grid(row=2, column=1, padx=10, pady=(5, 15), sticky="ew")

        # VPN
        self.vpn_frame = SettingsGroup(self.main_frame, title_key="group_vpn")
        self.vpn_frame.pack(fill="x", pady=(0, 10))
        self.lbl_sec1 = ctk.CTkLabel(self.vpn_frame, text=tr("secret_1"));
        self.lbl_sec1.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.secret_entry_1 = ctk.CTkEntry(self.vpn_frame, show="*");
        self.secret_entry_1.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.lbl_sec2 = ctk.CTkLabel(self.vpn_frame, text=tr("secret_2"));
        self.lbl_sec2.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.secret_entry_2 = ctk.CTkEntry(self.vpn_frame, show="*");
        self.secret_entry_2.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.lbl_sec3 = ctk.CTkLabel(self.vpn_frame, text=tr("secret_3"));
        self.lbl_sec3.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.secret_entry_3 = ctk.CTkEntry(self.vpn_frame, show="*");
        self.secret_entry_3.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        self.lbl_hint = ctk.CTkLabel(self.vpn_frame, text=tr("secret_hint"), font=ctk.CTkFont(size=10),
                                     text_color="gray");
        self.lbl_hint.grid(row=4, column=0, columnspan=2, pady=(5, 15))

        # Telemart
        self.tm_frame = SettingsGroup(self.main_frame, title_key="group_tm")
        self.tm_frame.pack(fill="x", pady=(0, 10))
        self.telemart_checkbox = ctk.CTkCheckBox(self.tm_frame, text=tr("auto_start_tm"),
                                                 command=self.toggle_login_fields)
        self.telemart_checkbox.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        self.lbl_login = ctk.CTkLabel(self.tm_frame, text=tr("login"));
        self.lbl_login.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.login_entry = ctk.CTkEntry(self.tm_frame);
        self.login_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.lbl_pass = ctk.CTkLabel(self.tm_frame, text=tr("password"));
        self.lbl_pass.grid(row=3, column=0, padx=10, pady=(5, 15), sticky="w")
        self.password_entry = ctk.CTkEntry(self.tm_frame, show="*");
        self.password_entry.grid(row=3, column=1, padx=10, pady=(5, 15), sticky="ew")

        self.save_btn = ctk.CTkButton(self, text=tr("save_btn"), height=35, command=self.save_config);
        self.save_btn.pack(padx=20, pady=20, fill="x")

        self.toggle_login_fields()
        self.protocol("WM_DELETE_WINDOW", self.master_app.quit)

    def change_lang(self, lang):
        set_language(lang)
        self.refresh_ui()

    def refresh_ui(self):
        self.title(tr("window_title_setup"))
        for frame in [self.lang_frame, self.sec_frame, self.vpn_frame, self.tm_frame]: frame.refresh_text()
        self.lbl_pin.configure(text=tr("pin_label"));
        self.lbl_pin_rep.configure(text=tr("pin_repeat"))
        self.lbl_sec1.configure(text=tr("secret_1"));
        self.lbl_sec2.configure(text=tr("secret_2"));
        self.lbl_sec3.configure(text=tr("secret_3"));
        self.lbl_hint.configure(text=tr("secret_hint"))
        self.telemart_checkbox.configure(text=tr("auto_start_tm"));
        self.lbl_login.configure(text=tr("login"));
        self.lbl_pass.configure(text=tr("password"))
        self.save_btn.configure(text=tr("save_btn"))

    def toggle_login_fields(self):
        st = "normal" if self.telemart_checkbox.get() == 1 else "disabled"
        self.login_entry.configure(state=st);
        self.password_entry.configure(state=st)

    def save_config(self):
        pin = self.pin_entry.get()
        if pin != self.pin_repeat_entry.get(): return messagebox.showerror("Error", tr("error_pin_mismatch"))
        secrets = [self.secret_entry_1.get().strip(), self.secret_entry_2.get().strip(),
                   self.secret_entry_3.get().strip()]
        if not any(secrets): return messagebox.showerror("Error", tr("error_no_secret"))
        try:
            save_credentials(self.login_entry.get(), self.password_entry.get(), pin or None, secrets,
                             self.telemart_checkbox.get() == 1, language=get_language())
            self.destroy();
            self.master_app.config_saved(pin or None)
        except Exception as e:
            messagebox.showerror("Error", str(e))


class PinWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app);
        self.master_app = master_app
        self.title(tr("window_title_pin"));
        self.geometry("320x180");
        self.transient(master_app)
        self.after(10, lambda: apply_window_settings(self))
        self.frame = ctk.CTkFrame(self, fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR,
                                  corner_radius=CORNER_RADIUS);
        self.frame.pack(expand=True, fill="both", padx=15, pady=15)
        ctk.CTkLabel(self.frame, text=tr("pin_enter_msg"), font=ctk.CTkFont(size=13)).pack(pady=(20, 5))
        self.pin_entry = ctk.CTkEntry(self.frame, show="*", width=200, justify="center");
        self.pin_entry.pack(pady=10)
        self.pin_entry.bind("<Return>", self.check);
        self.pin_entry.focus()
        ctk.CTkButton(self.frame, text=tr("unlock_btn"), height=35, width=200, command=self.check).pack(pady=10)
        self.protocol("WM_DELETE_WINDOW", self.master_app.quit)

    def check(self, event=None):
        entered_pin = self.pin_entry.get()
        if verify_pin(self.master_app.creds.get("pin_hash"), entered_pin):
            try:
                data = decrypt_credentials(self.master_app.creds, entered_pin)
                self.destroy()
                self.master_app.pin_unlocked(data)
            except Exception as e:
                messagebox.showerror("Error", str(e))
        else:
            messagebox.showerror("Error", tr("error_wrong_pin"))


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master_app):
        super().__init__(master_app);
        self.master_app = master_app
        self.title(tr("window_title_settings"));
        self.geometry("450x680");
        self.transient(master_app)
        self.initial_lang = get_language();
        self.selected_lang = get_language()
        self.after(10, lambda: apply_window_settings(self))
        self.grid_columnconfigure(0, weight=1);
        self.grid_rowconfigure(1, weight=1)

        self.sv1 = ctk.StringVar();
        self.sv2 = ctk.StringVar();
        self.sv3 = ctk.StringVar();
        self.lv = ctk.StringVar();
        self.pv = ctk.StringVar()

        self.pin_frame = SettingsGroup(self, title_key="group_access");
        self.pin_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        ctk.CTkLabel(self.pin_frame, text="PIN:").grid(row=1, column=0, padx=10, pady=10)
        self.pin_ent = ctk.CTkEntry(self.pin_frame, show="*");
        self.pin_ent.grid(row=1, column=1, sticky="ew", padx=5)
        self.unlock_btn = ctk.CTkButton(self.pin_frame, text=tr("unlock_btn"), width=80, height=28,
                                        command=self.unlock);
        self.unlock_btn.grid(row=1, column=2, padx=10)

        self.content_wrapper = ctk.CTkFrame(self, fg_color="transparent");
        self.content_wrapper.grid(row=1, column=0, sticky="nsew", padx=15, pady=5);
        self.content_wrapper.grid_columnconfigure(0, weight=1)
        self.lang_frame = SettingsGroup(self.content_wrapper, title_key="lang_label");
        self.lang_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.lang_selector = LanguageSelector(self.lang_frame, current_lang=get_language(),
                                              callback=self.change_lang_setting);
        self.lang_selector.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        for btn in self.lang_selector.buttons.values(): btn.configure(state="disabled")

        self.vpn_frame = SettingsGroup(self.content_wrapper, title_key="group_vpn");
        self.vpn_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.lbl_sec1 = ctk.CTkLabel(self.vpn_frame, text=tr("secret_1"));
        self.lbl_sec1.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.e1 = ctk.CTkEntry(self.vpn_frame, textvariable=self.sv1, show="*", state="disabled");
        self.e1.grid(row=1, column=1, sticky="ew", padx=10, pady=5)
        self.lbl_sec2 = ctk.CTkLabel(self.vpn_frame, text=tr("secret_2"));
        self.lbl_sec2.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.e2 = ctk.CTkEntry(self.vpn_frame, textvariable=self.sv2, show="*", state="disabled");
        self.e2.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        self.lbl_sec3 = ctk.CTkLabel(self.vpn_frame, text=tr("secret_3"));
        self.lbl_sec3.grid(row=3, column=0, padx=10, pady=(5, 15), sticky="w")
        self.e3 = ctk.CTkEntry(self.vpn_frame, textvariable=self.sv3, show="*", state="disabled");
        self.e3.grid(row=3, column=1, sticky="ew", padx=10, pady=(5, 15))

        self.tm_frame = SettingsGroup(self.content_wrapper, title_key="group_tm");
        self.tm_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.cb = ctk.CTkCheckBox(self.tm_frame, text=tr("auto_start_tm"), state="disabled", command=self.upd);
        self.cb.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        self.lbl_login = ctk.CTkLabel(self.tm_frame, text=tr("login"));
        self.lbl_login.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.le = ctk.CTkEntry(self.tm_frame, textvariable=self.lv, state="disabled");
        self.le.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        self.lbl_pass = ctk.CTkLabel(self.tm_frame, text=tr("password"));
        self.lbl_pass.grid(row=3, column=0, padx=10, pady=(5, 15), sticky="w")
        self.pe = ctk.CTkEntry(self.tm_frame, textvariable=self.pv, show="*", state="disabled");
        self.pe.grid(row=3, column=1, sticky="ew", padx=10, pady=(5, 15))

        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent");
        self.actions_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=15);
        self.actions_frame.grid_columnconfigure(0, weight=1)
        self.save_btn = ctk.CTkButton(self.actions_frame, text=tr("save_changes_btn"), height=35, state="disabled",
                                      command=self.save);
        self.save_btn.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.del_btn = ctk.CTkButton(self.actions_frame, text=tr("delete_btn"), height=35, fg_color="#AA0000",
                                     hover_color="#880000", command=self.delete);
        self.del_btn.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        if self.master_app.creds.get("start_telemart"): self.cb.select()
        if not self.master_app.creds.get("pin_hash"): self.pin_frame.grid_forget(); self.unlock(True)

    def change_lang_setting(self, lang):
        self.selected_lang = lang

    def upd(self):
        st = "normal" if (self.cb.get() == 1 and self.save_btn.cget("state") == "normal") else "disabled"
        self.le.configure(state=st);
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
            for w in [self.e1, self.e2, self.e3, self.cb]: w.configure(state="normal")
            for btn in self.lang_selector.buttons.values(): btn.configure(state="normal")
            self.save_btn.configure(state="normal");
            self.upd()
            if not no_pin: self.pin_frame.grid_forget()
        except:
            messagebox.showerror("Error", tr("error_wrong_pin"))

    def save(self):
        try:
            pin = self.pin_ent.get() if self.master_app.creds.get("pin_hash") else None
            save_credentials(self.lv.get(), self.pv.get(), pin, [self.sv1.get(), self.sv2.get(), self.sv3.get()],
                             self.cb.get() == 1, language=self.selected_lang)
            self.master_app.creds = load_credentials()
            self.master_app.decrypted_creds = decrypt_credentials(self.master_app.creds, pin)
            self.master_app.update_main_window_buttons()
            if self.selected_lang != self.initial_lang: messagebox.showinfo(tr("restart_title"), tr("restart_msg"))
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete(self):
        if messagebox.askyesno("Reset", tr("delete_confirm")): clear_credentials(); self.master_app.quit()