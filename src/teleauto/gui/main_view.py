# src/teleauto/gui/main_view.py
import sys
import webbrowser
import customtkinter as ctk
from src.teleauto.localization import tr
from .constants import ROW_HEIGHT, CORNER_RADIUS, FRAME_BG, BORDER_COLOR, MAIN_FONT_FAMILY
from .widgets import LEDCircle, TitleBox, StatusBox, TextboxLogger
from .constants import VERSION


class MainWindow(ctk.CTkFrame):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.grid_columnconfigure(0, weight=1);
        self.grid_columnconfigure(1, weight=1);
        self.grid_columnconfigure(2, weight=0)

        f_label = (MAIN_FONT_FAMILY, 12)
        f_btn = (MAIN_FONT_FAMILY, 13, "bold")

        # Top Bar
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=(5, 0), sticky="ew")
        self.top_frame.grid_columnconfigure(0, weight=1);
        self.top_frame.grid_columnconfigure(1, weight=1);
        self.top_frame.grid_columnconfigure(2, weight=0)

        # Version
        self.version_frame = ctk.CTkFrame(self.top_frame, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                                          fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR)
        self.version_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5));
        self.version_frame.pack_propagate(False)

        self.ver_label = ctk.CTkLabel(self.version_frame, text=VERSION, text_color="#666666", font=f_label,
                                      cursor="hand2")
        self.ver_label.place(relx=0.5, rely=0.43, anchor="center")
        self.ver_label.bind("<Button-1>",
                            lambda e: webbrowser.open("https://github.com/Shura4eburek/TeleAuto/releases"))

        # Update Status
        self.update_frame = ctk.CTkFrame(self.top_frame, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                                         fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR)
        self.update_frame.grid(row=0, column=1, sticky="ew", padx=(5, 5));
        self.update_frame.pack_propagate(False)

        self.update_inner = ctk.CTkFrame(self.update_frame, fg_color="transparent");
        self.update_inner.place(relx=0.5, rely=0.43, anchor="center")

        ctk.CTkLabel(self.update_inner, text=tr("update_label"), text_color="#AAAAAA", font=f_label).pack(side="left",
                                                                                                          padx=(0, 8))
        self.update_led = LEDCircle(self.update_inner, size=15, fg_color=FRAME_BG);
        self.update_led.pack(side="left", padx=(0, 8), pady=(4, 0));
        self.update_led.set_state("success")
        self.update_label = ctk.CTkLabel(self.update_inner, text=tr("update_actual"), text_color="#666666",
                                         font=f_label);
        self.update_label.pack(side="left")

        # Settings Button
        self.settings_btn = ctk.CTkButton(self.top_frame, text="⚙️", width=35, height=ROW_HEIGHT, fg_color=FRAME_BG,
                                          border_width=1, border_color=BORDER_COLOR, text_color="#AAA",
                                          hover_color="#333", command=self.master_app.open_settings_window)
        self.settings_btn.grid(row=0, column=2, sticky="e", padx=(5, 0))

        # Content
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent");
        self.content_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="nsew");
        self.content_frame.grid_columnconfigure(0, weight=1);
        self.content_frame.grid_columnconfigure(1, weight=1);
        self.content_frame.grid_columnconfigure(2, weight=0)

        # Telemart
        self.telemart_title = TitleBox(self.content_frame, title="Telemart");
        self.telemart_title.grid(row=0, column=0, padx=(0, 5), pady=8, sticky="ew")
        self.telemart_status = StatusBox(self.content_frame, text_key="status_waiting");
        self.telemart_status.grid(row=0, column=1, padx=(5, 5), pady=8, sticky="ew")
        self.start_telemart_button = ctk.CTkButton(self.content_frame, text=tr("btn_start"), width=125,
                                                   height=ROW_HEIGHT, corner_radius=CORNER_RADIUS, state="disabled",
                                                   font=f_btn, command=self.master_app.on_start_telemart_click)
        self.start_telemart_button.grid(row=0, column=2, padx=(5, 0), pady=8, sticky="e")

        # Pritunl
        self.pritunl_title = TitleBox(self.content_frame, title="Pritunl");
        self.pritunl_title.grid(row=1, column=0, padx=(0, 5), pady=8, sticky="ew")
        self.pritunl_status = StatusBox(self.content_frame, text_key="status_waiting");
        self.pritunl_status.grid(row=1, column=1, padx=(5, 5), pady=8, sticky="ew")
        self.pritunl_buttons_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent");
        self.pritunl_buttons_frame.grid(row=1, column=2, padx=(5, 0), pady=8, sticky="e")

        # Кнопки профилей
        self.pritunl_btn_1 = ctk.CTkButton(self.pritunl_buttons_frame, text="P1", height=ROW_HEIGHT,
                                           corner_radius=CORNER_RADIUS, font=f_btn,
                                           command=lambda: self.master_app.on_pritunl_connect_click(0));
        self.pritunl_btn_2 = ctk.CTkButton(self.pritunl_buttons_frame, text="P2", height=ROW_HEIGHT,
                                           corner_radius=CORNER_RADIUS, font=f_btn,
                                           command=lambda: self.master_app.on_pritunl_connect_click(1));
        self.pritunl_btn_3 = ctk.CTkButton(self.pritunl_buttons_frame, text="P3", height=ROW_HEIGHT,
                                           corner_radius=CORNER_RADIUS, font=f_btn,
                                           command=lambda: self.master_app.on_pritunl_connect_click(2))

        # --- НОВАЯ КНОПКА ОТМЕНЫ PRITUNL (скрыта по умолчанию) ---
        self.pritunl_cancel_btn = ctk.CTkButton(self.pritunl_buttons_frame, text=tr("btn_cancel"), width=125,
                                                height=ROW_HEIGHT,
                                                corner_radius=CORNER_RADIUS, fg_color="#AA0000", hover_color="#880000",
                                                font=f_btn,
                                                command=self.master_app.on_cancel_pritunl_click)

        # Monitor
        self.monitor_title = TitleBox(self.content_frame, title="Monitor");
        self.monitor_title.grid(row=2, column=0, padx=(0, 5), pady=8, sticky="ew")
        self.monitor_status = StatusBox(self.content_frame, text_key="status_waiting");
        self.monitor_status.grid(row=2, column=1, padx=(5, 5), pady=8, sticky="ew")
        self.disconnect_button = ctk.CTkButton(self.content_frame, text=tr("btn_disconnect"), width=125,
                                               height=ROW_HEIGHT, corner_radius=CORNER_RADIUS, state="disabled",
                                               fg_color="grey", font=f_btn, command=self.master_app.on_disconnect_click)
        self.disconnect_button.grid(row=2, column=2, padx=(5, 0), pady=8, sticky="e")

        # Log
        self.log_textbox = ctk.CTkTextbox(self, state=ctk.NORMAL, height=200, fg_color="#111", text_color="#CCC",
                                          font=("Consolas", 12))
        self.is_expanded = False

        # Bottom Status Bar
        self.bottom_bar = ctk.CTkFrame(self, height=ROW_HEIGHT, fg_color="transparent")
        self.bottom_bar.grid(row=3, column=0, columnspan=3, padx=10, pady=(5, 10), sticky="ew")

        # Left: Internet Status
        self.net_frame = ctk.CTkFrame(self.bottom_bar, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                                      fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR)
        self.net_frame.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.net_frame.pack_propagate(False)

        self.net_inner = ctk.CTkFrame(self.net_frame, fg_color="transparent")
        self.net_inner.place(relx=0.5, rely=0.43, anchor="center")

        ctk.CTkLabel(self.net_inner, text=tr("net_status_label"), text_color="#AAAAAA",
                     font=(MAIN_FONT_FAMILY, 12)).pack(side="left", padx=(0, 8))

        self.net_led = LEDCircle(self.net_inner, size=15, fg_color=FRAME_BG)
        self.net_led.pack(side="left", pady=(4, 0))
        self.net_led.set_state("error")

        # Right: Ping
        self.ping_frame = ctk.CTkFrame(self.bottom_bar, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                                       fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR)
        self.ping_frame.pack(side="right", fill="x", expand=True, padx=(5, 0))
        self.ping_frame.pack_propagate(False)

        self.ping_inner = ctk.CTkFrame(self.ping_frame, fg_color="transparent")
        self.ping_inner.place(relx=0.5, rely=0.43, anchor="center")

        ctk.CTkLabel(self.ping_inner, text=tr("net_ping_label"), text_color="#AAAAAA",
                     font=(MAIN_FONT_FAMILY, 12)).pack(side="left", padx=(0, 5))

        self.ping_value_label = ctk.CTkLabel(self.ping_inner, text="-- ms", text_color="#666666",
                                             font=(MAIN_FONT_FAMILY, 12, "bold"))
        self.ping_value_label.pack(side="left")

    def expand_log(self):
        if self.is_expanded: return
        self.is_expanded = True;
        current_w = self.master_app.winfo_width();
        self.master_app.geometry(f"{current_w}x600")
        self.log_textbox.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew");
        self.grid_rowconfigure(2, weight=1)
        logger = TextboxLogger(self.log_textbox);
        sys.stdout = logger;
        sys.stderr = logger

    def update_panel_safe(self, panel_name, state, text_key):
        title_box, status_box = None, None
        if panel_name == 'telemart':
            title_box, status_box = self.telemart_title, self.telemart_status
        elif panel_name == 'pritunl':
            title_box, status_box = self.pritunl_title, self.pritunl_status
        elif panel_name == 'monitor':
            title_box, status_box = self.monitor_title, self.monitor_status
        if title_box and status_box:
            self.after(0, lambda: title_box.set_led(state))
            self.after(0, lambda: status_box.set_text_key(text_key, state))

    def update_net_status(self, is_connected, ping_ms):
        if is_connected:
            self.net_led.set_state("success")
            self.ping_value_label.configure(text=f"{ping_ms} ms", text_color="#E0E0E0")
        else:
            self.net_led.set_state("error")
            self.ping_value_label.configure(text="-- ms", text_color="#666666")

    def show_update_ready(self, version_tag):
        self.update_led.set_state("working")
        self.update_label.destroy()
        self.update_btn = ctk.CTkButton(self.update_inner, text=f"🔄 {version_tag}", width=80, height=20,
                                        fg_color="#228B22", hover_color="#006400",
                                        font=(MAIN_FONT_FAMILY, 11, "bold"),
                                        command=self.master_app.install_update_now)
        self.update_btn.pack(side="left")

    # --- НОВЫЕ МЕТОДЫ УПРАВЛЕНИЯ КНОПКАМИ ---
    def toggle_pritunl_ui(self, state):
        """state: 'working' (показать Cancel) или 'normal' (вернуть как было)"""
        if state == 'working':
            self.pritunl_btn_1.pack_forget()
            self.pritunl_btn_2.pack_forget()
            self.pritunl_btn_3.pack_forget()
            self.pritunl_cancel_btn.pack(side="left", padx=0)
        else:
            self.pritunl_cancel_btn.pack_forget()
            # Кнопки P1-P3 восстановятся через update_main_window_buttons в App

    def toggle_telemart_ui(self, state):
        if state == 'working':
            self.start_telemart_button.configure(text=tr("btn_cancel"), fg_color="#AA0000", hover_color="#880000",
                                                 state="normal", command=self.master_app.on_cancel_telemart_click)
        else:
            self.start_telemart_button.configure(text=tr("btn_start"), fg_color=["#3B8ED0", "#1F6AA5"],
                                                 hover_color=["#36719F", "#144870"],
                                                 command=self.master_app.on_start_telemart_click)