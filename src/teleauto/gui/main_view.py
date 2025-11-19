import sys  # <--- ДОБАВЛЕНО
import customtkinter as ctk
from src.teleauto.localization import tr
from .constants import ROW_HEIGHT, CORNER_RADIUS, FRAME_BG, BORDER_COLOR
from .widgets import LEDCircle, TitleBox, StatusBox, TextboxLogger


class MainWindow(ctk.CTkFrame):
    def __init__(self, master_app):
        super().__init__(master_app)
        self.master_app = master_app
        self.grid_columnconfigure(0, weight=1);
        self.grid_columnconfigure(1, weight=1);
        self.grid_columnconfigure(2, weight=0)

        # Top Bar
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=(5, 0), sticky="ew")
        self.top_frame.grid_columnconfigure(0, weight=1);
        self.top_frame.grid_columnconfigure(1, weight=1);
        self.top_frame.grid_columnconfigure(2, weight=0)

        self.version_frame = ctk.CTkFrame(self.top_frame, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                                          fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR)
        self.version_frame.grid(row=0, column=0, sticky="ew", padx=(0, 5));
        self.version_frame.pack_propagate(False)
        ctk.CTkLabel(self.version_frame, text="v1.0 release", text_color="#666666", font=ctk.CTkFont(size=12)).place(
            relx=0.5, rely=0.53, anchor="center")

        self.update_frame = ctk.CTkFrame(self.top_frame, height=ROW_HEIGHT, corner_radius=CORNER_RADIUS,
                                         fg_color=FRAME_BG, border_width=1, border_color=BORDER_COLOR)
        self.update_frame.grid(row=0, column=1, sticky="ew", padx=(5, 5));
        self.update_frame.pack_propagate(False)
        self.update_inner = ctk.CTkFrame(self.update_frame, fg_color="transparent");
        self.update_inner.place(relx=0.5, rely=0.53, anchor="center")
        ctk.CTkLabel(self.update_inner, text=tr("update_label"), text_color="#AAAAAA", font=ctk.CTkFont(size=12)).pack(
            side="left", padx=(0, 8))
        self.update_led = LEDCircle(self.update_inner, size=15, fg_color=FRAME_BG);
        self.update_led.pack(side="left", padx=(0, 8));
        self.update_led.set_state("success")
        self.update_label = ctk.CTkLabel(self.update_inner, text=tr("update_actual"), text_color="#666666",
                                         font=ctk.CTkFont(size=12));
        self.update_label.pack(side="left")

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
                                                   command=self.master_app.on_start_telemart_click)
        self.start_telemart_button.grid(row=0, column=2, padx=(5, 0), pady=8, sticky="e")

        # Pritunl
        self.pritunl_title = TitleBox(self.content_frame, title="Pritunl");
        self.pritunl_title.grid(row=1, column=0, padx=(0, 5), pady=8, sticky="ew")
        self.pritunl_status = StatusBox(self.content_frame, text_key="status_waiting");
        self.pritunl_status.grid(row=1, column=1, padx=(5, 5), pady=8, sticky="ew")
        self.pritunl_buttons_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent");
        self.pritunl_buttons_frame.grid(row=1, column=2, padx=(5, 0), pady=8, sticky="e")
        self.pritunl_btn_1 = ctk.CTkButton(self.pritunl_buttons_frame, text="P1", height=ROW_HEIGHT,
                                           corner_radius=CORNER_RADIUS,
                                           command=lambda: self.master_app.on_pritunl_connect_click(0));
        self.pritunl_btn_2 = ctk.CTkButton(self.pritunl_buttons_frame, text="P2", height=ROW_HEIGHT,
                                           corner_radius=CORNER_RADIUS,
                                           command=lambda: self.master_app.on_pritunl_connect_click(1));
        self.pritunl_btn_3 = ctk.CTkButton(self.pritunl_buttons_frame, text="P3", height=ROW_HEIGHT,
                                           corner_radius=CORNER_RADIUS,
                                           command=lambda: self.master_app.on_pritunl_connect_click(2))

        # Monitor
        self.monitor_title = TitleBox(self.content_frame, title="Monitor");
        self.monitor_title.grid(row=2, column=0, padx=(0, 5), pady=8, sticky="ew")
        self.monitor_status = StatusBox(self.content_frame, text_key="status_waiting");
        self.monitor_status.grid(row=2, column=1, padx=(5, 5), pady=8, sticky="ew")
        self.disconnect_button = ctk.CTkButton(self.content_frame, text=tr("btn_disconnect"), width=125,
                                               height=ROW_HEIGHT, corner_radius=CORNER_RADIUS, state="disabled",
                                               fg_color="grey", command=self.master_app.on_disconnect_click)
        self.disconnect_button.grid(row=2, column=2, padx=(5, 0), pady=8, sticky="e")

        # Log
        self.log_textbox = ctk.CTkTextbox(self, state=ctk.NORMAL, height=200, fg_color="#111", text_color="#CCC")
        self.is_expanded = False

    def expand_log(self):
        if self.is_expanded: return
        self.is_expanded = True
        current_w = self.master_app.winfo_width()
        self.master_app.geometry(f"{current_w}x600")
        self.log_textbox.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.grid_rowconfigure(2, weight=1)

        # Здесь используется sys
        logger = TextboxLogger(self.log_textbox)
        sys.stdout = logger
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