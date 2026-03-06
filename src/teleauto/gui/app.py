# src/teleauto/gui/app.py
import os
import sys
import logging
import threading
import customtkinter as ctk
from tkinter import messagebox

import pystray
from PIL import Image

from src.teleauto.localization import tr, set_language
from src.teleauto.controller import AppController
from src.teleauto.gui.windows import ConfigWindow, PinWindow, SettingsWindow, UpdateDialog
from src.teleauto.gui.main_view import MainWindow
from src.teleauto.gui.utils import apply_window_settings, apply_dark_title_bar
from src.teleauto.gui.constants import VERSION
from src.teleauto.gui.fonts import load_custom_font

logger = logging.getLogger(__name__)


class App(ctk.CTk):
    def __init__(self):
        load_custom_font("Unbounded-VariableFont_wght.ttf")
        super().__init__()

        self.ctrl = AppController(ui=self)
        self.main_frame = None

        if self.ctrl.creds:
            set_language(self.ctrl.creds.get("language", "ru"))

        self.title("TeleAuto")
        self.geometry("550x280")
        self.resizable(False, False)
        self.after(10, lambda: apply_dark_title_bar(self))

        # Start background tasks (update check, network monitor)
        self.ctrl.start_background_tasks()

        if not self.ctrl.creds:
            self.withdraw()
            ConfigWindow(self)
        else:
            if self.ctrl.creds.get("pin_hash"):
                self.withdraw()
                PinWindow(self)
            else:
                self.show_main_window()

        self.protocol("WM_DELETE_WINDOW", self._on_close_button)

        # Tray icon reference
        self._tray_icon = None

    def config_saved(self, pin_used):
        self.ctrl.load_creds()
        if pin_used:
            PinWindow(self)
        else:
            self.show_main_window()

    def pin_unlocked(self, pin):
        try:
            self.ctrl.decrypt_and_set_language(pin)
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
        logger.info(tr("log_system_start"))

        # Stop everything on startup
        self.on_disconnect_click(startup=True)

        if self.ctrl.update_ready and self.ctrl.new_version_tag:
            self.after(400, lambda: self._show_update_dialog(self.ctrl.new_version_tag))

        # Setup system tray
        self._setup_tray()

    def update_main_window_buttons(self, is_busy=False):
        if not self.main_frame: return
        self.main_frame.toggle_pritunl_ui('normal')

        state_connect = "disabled" if (is_busy or self.ctrl.vpn_is_connected) else "normal"
        self.main_frame.pritunl_connect_btn.configure(state=state_connect)

        if not is_busy:
            self.main_frame.toggle_telemart_ui('normal')

        state_disconnect = "normal" if self.ctrl.vpn_is_connected else "disabled"
        state_telemart = "disabled" if is_busy else "normal"

        self.main_frame.start_telemart_button.configure(state=state_telemart)
        self.main_frame.disconnect_button.configure(state=state_disconnect)

    # --- VPN ---
    def on_pritunl_connect_click(self):
        if not self.main_frame.is_expanded: self.main_frame.expand_log()
        self.main_frame.toggle_pritunl_ui('working')
        self.update_main_window_buttons(is_busy=True)
        self.ctrl.start_autopilot()

    def on_cancel_pritunl_click(self):
        self.ctrl.stop_autopilot()
        logger.info(tr("log_op_cancelled"))

    def on_disconnect_click(self, startup=False):
        if not startup:
            logger.info(tr("log_ctrl_stopping"))
        self.ctrl.stop_autopilot()
        if not startup:
            self.main_frame.disconnect_button.configure(state="disabled")

    # --- Telemart ---
    def on_start_telemart_click(self):
        if not self.main_frame.is_expanded: self.main_frame.expand_log()
        self.main_frame.toggle_telemart_ui('working')
        self.ctrl.start_telemart()

    def on_cancel_telemart_click(self):
        self.ctrl.stop_telemart()
        logger.info(tr("log_op_cancelled"))

    # --- Utils ---
    def set_ui_status(self, target, state, text_key):
        if self.main_frame: self.main_frame.update_panel_safe(target, state, text_key)

    def open_settings_window(self):
        SettingsWindow(self)

    # --- System Tray ---
    def _setup_tray(self):
        try:
            image = self._get_tray_image()
            menu = pystray.Menu(
                pystray.MenuItem(tr("tray_show"), self._show_from_tray, default=True),
                pystray.MenuItem(tr("tray_quit"), self._quit_from_tray),
            )
            self._tray_icon = pystray.Icon("TeleAuto", image, "TeleAuto", menu)
            tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
            tray_thread.start()
        except Exception as e:
            logger.warning("Failed to setup tray: %s", e)

    @staticmethod
    def _get_tray_image():
        """Load icon.ico if it exists, otherwise generate a simple fallback icon."""
        icon_path = App._get_icon_path()
        if icon_path and os.path.exists(icon_path):
            return Image.open(icon_path)
        # Fallback: blue circle — works without icon.ico in dev mode
        from PIL import ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse([4, 4, 60, 60], fill=(30, 144, 255, 255))
        return img

    @staticmethod
    def _get_icon_path():
        # PyInstaller bundled: files are in sys._MEIPASS
        try:
            return os.path.join(sys._MEIPASS, "icon.ico")
        except AttributeError:
            pass
        # Development: look relative to this file's location (src/teleauto/gui/ → project root)
        here = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
        candidate = os.path.join(project_root, "icon.ico")
        return candidate if os.path.exists(candidate) else None

    def _on_close_button(self):
        """Close button minimizes to tray if tray is running, otherwise quits."""
        if self._tray_icon:
            self._minimize_to_tray()
        else:
            self.on_closing()

    def _minimize_to_tray(self):
        self.withdraw()

    def _show_from_tray(self, icon=None, item=None):
        self.after(0, self.deiconify)

    def _quit_from_tray(self, icon=None, item=None):
        self.after(0, self.on_closing)

    def on_update_found(self, tag):
        """Called from controller (via after()) when a new version is detected."""
        if self.main_frame:
            self._show_update_dialog(tag)
        # If main_frame not ready yet — show_main_window() will handle it via update_ready flag

    def _show_update_dialog(self, tag):
        UpdateDialog(self, tag, on_now=self._do_update_now, on_later=self._do_update_later)

    def _do_update_now(self, dialog):
        dialog.disable_buttons()
        dialog.set_status(tr("update_downloading"))

        def _worker():
            success = self.ctrl.do_download_and_apply()
            if success:
                dialog.after(0, lambda: dialog.set_status(tr("update_applying"), color="#00CC44"))
                dialog.after(800, self.on_closing)
            else:
                dialog.after(0, lambda: dialog.set_status(tr("update_failed"), color="#FF4444"))
                dialog.after(0, lambda: dialog.later_btn.configure(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

    def _do_update_later(self):
        if self.main_frame and self.ctrl.new_version_tag:
            self.main_frame.show_update_ready(self.ctrl.new_version_tag)

    def install_update_now(self):
        """Called from the header update button in MainWindow."""
        if self.ctrl.new_version_tag:
            self._show_update_dialog(self.ctrl.new_version_tag)

    def on_closing(self):
        # Stop tray icon if running
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass

        self.ctrl.shutdown()
        self.quit()


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()
