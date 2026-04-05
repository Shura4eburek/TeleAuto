# src/teleauto/webapi.py
"""
pywebview JS API bridge + UI callbacks for AppController.
Replaces PyQt6 App from gui/app.py.
"""
import json
import logging
import os
import sys
import threading

from src.teleauto.localization import tr, set_language, get_language, LANG_CODES
from src.teleauto.gui.constants import VERSION
from src.teleauto.credentials import (
    save_credentials, load_credentials, verify_pin,
    decrypt_credentials, clear_credentials,
)

logger = logging.getLogger(__name__)

# Window sizes per view
_SIZES = {
    "config": (650, 580),
    "pin":    (650, 580),
    "main":   (650, 580),
}


class WebviewLogHandler(logging.Handler):
    """Forwards log records to the JS frontend via _push."""

    def __init__(self, app: "App"):
        super().__init__()
        self.setFormatter(logging.Formatter("%(message)s"))
        self._app = app

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self._app._push({"type": "log", "message": msg})
        except Exception:
            pass


class App:
    """
    Acts as:
      - 'ui' for AppController  (controller calls ui.set_ui_status, etc.)
      - pywebview JS API        (JS calls window.pywebview.api.*)
    """

    def __init__(self):
        self._window = None
        self.main_frame = self      # controller does ui.main_frame.after(0, ...)
        self.ctrl = None            # set by launcher after construction
        self._bg_started = False
        self._log_handler: WebviewLogHandler | None = None
        self._tray = None
        self._is_maximized = False

    # ---------------------------------------------------------------- window
    def set_window(self, window):
        self._window = window
        self._log_handler = WebviewLogHandler(self)
        self._log_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(self._log_handler)
        self._apply_acrylic()

    def _apply_acrylic(self):
        """Apply dark acrylic blur + rounded corners via Windows API."""
        import ctypes

        hwnd = ctypes.windll.user32.FindWindowW(None, "TeleAuto")
        if not hwnd:
            return

        # Rounded corners (Windows 11)
        try:
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            val = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(val), ctypes.sizeof(val)
            )
        except Exception:
            pass

        # Dark acrylic blur via SetWindowCompositionAttribute (Win10+)
        # Skipping DWMWA_SYSTEMBACKDROP_TYPE — it uses system grey tint, not customizable
        try:
            class ACCENTPOLICY(ctypes.Structure):
                _fields_ = [
                    ('AccentState', ctypes.c_int),
                    ('AccentFlags', ctypes.c_int),
                    ('GradientColor', ctypes.c_int),  # AABBGGRR
                    ('AnimationId', ctypes.c_int),
                ]

            class WCAD(ctypes.Structure):
                _fields_ = [
                    ('Attribute', ctypes.c_int),
                    ('pData', ctypes.c_void_p),
                    ('cbData', ctypes.c_size_t),
                ]

            accent = ACCENTPOLICY()
            accent.AccentState = 4            # ACCENT_ENABLE_ACRYLICBLURBEHIND
            accent.GradientColor = 0xBB111111 # AA=0xBB(73% opacity), тёмный тинт

            data = WCAD()
            data.Attribute = 19               # WCA_ACCENT_POLICY
            data.cbData = ctypes.sizeof(accent)
            data.pData = ctypes.addressof(accent)

            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        except Exception:
            pass

    def _push(self, data: dict):
        if self._window:
            try:
                js = f"window.__update && window.__update({json.dumps(data, ensure_ascii=False)})"
                self._window.evaluate_js(js)
            except Exception as e:
                logger.debug("_push error: %s", e)

    def _resize(self, view: str):
        """Resize window to the preset size for a given view."""
        if self._window:
            w, h = _SIZES.get(view, (650, 580))
            try:
                self._window.resize(w, h)
            except Exception as e:
                logger.debug("resize error: %s", e)

    # ---------------------------------------------------------------- after() compat
    def after(self, ms: int, callback):
        """Tkinter-compat after() — schedule callback on a daemon thread."""
        if ms == 0:
            t = threading.Thread(target=callback, daemon=True)
            t.start()
        else:
            t = threading.Timer(ms / 1000.0, callback)
            t.daemon = True
            t.start()

    # ---------------------------------------------------------------- controller → UI
    def set_ui_status(self, target: str, state: str, text_key: str):
        self._push({"type": "status", "target": target, "state": state, "text": tr(text_key)})

    def update_main_window_buttons(self, is_busy: bool = False):
        self._push({
            "type": "buttons",
            "is_busy": is_busy,
            "vpn_connected": bool(self.ctrl and self.ctrl.vpn_is_connected),
        })

    def on_update_found(self, tag: str):
        self._push({"type": "update_found", "tag": tag})

    def update_net_status(self, is_connected: bool, ping_ms):
        self._push({"type": "net_status", "connected": is_connected, "ping": ping_ms})

    # ---------------------------------------------------------------- helpers
    def _start_bg(self):
        if not self._bg_started:
            self._bg_started = True
            self.ctrl.start_background_tasks()
            self._setup_tray()

    # ---------------------------------------------------------------- tray
    def _make_tray_image(self):
        from PIL import Image, ImageDraw
        try:
            try:
                base = sys._MEIPASS
            except AttributeError:
                base = os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "..", "..", ".."
                ))
            path = os.path.join(base, "icon.ico")
            if os.path.exists(path):
                return Image.open(path).convert("RGBA")
        except Exception:
            pass
        # Fallback: blue circle
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([4, 4, 60, 60], fill=(10, 132, 255, 255))
        return img

    def _setup_tray(self):
        try:
            import pystray
            img = self._make_tray_image()
            menu = pystray.Menu(
                pystray.MenuItem(tr("tray_show"), self._show_from_tray, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(tr("tray_quit"), self._quit_from_tray),
            )
            self._tray = pystray.Icon("TeleAuto", img, "TeleAuto", menu)
            t = threading.Thread(target=self._tray.run, daemon=True)
            t.start()
        except Exception as e:
            logger.warning("Tray setup failed: %s", e)

    def _show_from_tray(self, icon=None, item=None):
        if self._window:
            self._window.show()

    def _quit_from_tray(self, icon=None, item=None):
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        self._do_quit()

    # ---------------------------------------------------------------- JS API: init
    def get_initial_state(self) -> dict:
        base = {"version": VERSION, "language": get_language()}
        if not self.ctrl.creds:
            self._resize("config")
            return {**base, "view": "config", "languages": list(LANG_CODES.keys())}
        elif self.ctrl.creds.get("pin_hash"):
            self._resize("pin")
            return {**base, "view": "pin"}
        else:
            self._resize("main")
            self._start_bg()
            start_telemart = self.ctrl.creds.get("start_telemart", False)
            return {**base, "view": "main", "start_telemart": start_telemart}

    # ---------------------------------------------------------------- JS API: config
    def save_config(self, login: str, password: str, pin: str, pin_repeat: str,
                    start_telemart: bool, telemart_path: str, language: str) -> dict:
        if not pin or len(pin) < 4:
            return {"ok": False, "error": tr("error_pin_mismatch")}
        if pin != pin_repeat:
            return {"ok": False, "error": tr("error_pin_mismatch")}
        try:
            set_language(language)
            save_credentials(
                login, password,
                pin or None, {},
                start_telemart,
                language=language,
                telemart_path=telemart_path,
                manual_offset=0,
            )
            self.ctrl.load_creds()
            next_view = "pin" if pin else "main"
            self._resize(next_view)
            if next_view == "main":
                self._start_bg()
            return {"ok": True, "view": next_view}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------------------------------------------------------- JS API: PIN
    def verify_pin_input(self, pin: str) -> dict:
        pin_hash = self.ctrl.creds.get("pin_hash")
        if not verify_pin(pin_hash, pin):
            return {"ok": False, "error": tr("error_wrong_pin")}
        try:
            self.ctrl.decrypt_and_set_language(pin)
            self._resize("main")
            self._start_bg()
            start_telemart = self.ctrl.creds.get("start_telemart", False)
            return {"ok": True, "start_telemart": start_telemart, "language": get_language()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------------------------------------------------------- JS API: VPN
    def vpn_connect(self):
        self.ctrl.start_autopilot()

    def vpn_disconnect(self):
        self.ctrl.stop_autopilot()

    # ---------------------------------------------------------------- JS API: Telemart
    def telemart_start(self):
        self.ctrl.start_telemart()

    def telemart_cancel(self):
        self.ctrl.stop_telemart()

    # ---------------------------------------------------------------- JS API: Settings
    def get_settings(self, pin: str) -> dict:
        try:
            data = decrypt_credentials(self.ctrl.creds, pin or None)
            profiles = []
            if os.path.exists("profiles.json"):
                import json as _json
                with open("profiles.json", "r", encoding="utf-8") as f:
                    profiles = _json.load(f)
            secrets = {p: data.secrets.get(p, "") for p in profiles}
            return {
                "ok": True,
                "login": data.username,
                "password": data.password,
                "start_telemart": data.start_telemart,
                "telemart_path": data.telemart_path or "",
                "language": data.language or get_language(),
                "manual_offset": data.manual_offset or 0,
                "profiles": profiles,
                "secrets": secrets,
                "has_pin": bool(self.ctrl.creds.get("pin_hash")),
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def save_settings(self, pin: str, login: str, password: str,
                      secrets: dict, start_telemart: bool,
                      telemart_path: str, language: str, manual_offset: int) -> dict:
        try:
            save_credentials(
                login, password,
                pin or None, secrets,
                start_telemart,
                language=language,
                telemart_path=telemart_path,
                manual_offset=int(manual_offset),
            )
            self.ctrl.creds = load_credentials()
            self.ctrl.user_pin = pin or None
            set_language(language)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def delete_credentials(self) -> dict:
        try:
            clear_credentials()
            for f in ("profiles.json",):
                if os.path.exists(f):
                    os.remove(f)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_totp_preview(self, secret: str) -> dict:
        try:
            import pyotp
            code = pyotp.TOTP(secret.strip()).now()
            return {"ok": True, "code": code}
        except Exception:
            return {"ok": False, "code": ""}

    # ---------------------------------------------------------------- JS API: Update
    def do_update(self) -> dict:
        def _worker():
            success = self.ctrl.do_download_and_apply()
            self._push({"type": "update_done" if success else "update_failed"})
            if success:
                self._do_quit()
        threading.Thread(target=_worker, daemon=True).start()
        return {"ok": True}

    # ---------------------------------------------------------------- JS API: window
    def minimize(self):
        if self._window:
            self._window.minimize()

    def maximize(self):
        """Toggle maximize / restore."""
        if not self._window:
            return
        try:
            if self._is_maximized:
                self._window.restore()
                self._is_maximized = False
            else:
                self._window.maximize()
                self._is_maximized = True
        except Exception as e:
            logger.debug("maximize error: %s", e)

    def resize_window(self, width: int, height: int):
        if self._window:
            try:
                self._window.resize(int(width), int(height))
            except Exception:
                pass

    def open_url(self, url: str):
        if not url.startswith("https://"):
            logger.warning("open_url blocked non-https URL: %s", url)
            return
        import webbrowser
        webbrowser.open(url)

    def hide_to_tray(self):
        """Hide window to tray (close button behavior when tray is active)."""
        if self._tray and self._window:
            self._window.hide()
        else:
            self._do_quit()

    def quit(self):
        """Called from JS (red button in config/pin views or tray quit)."""
        threading.Thread(target=self._do_quit, daemon=True).start()

    def _do_quit(self):
        # Show shutdown screen before closing
        if self._window:
            try:
                self._window.show()
                self._push({"type": "shutdown"})
            except Exception:
                pass
            import time
            time.sleep(4)
        if self._log_handler:
            logging.getLogger().removeHandler(self._log_handler)
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        if self.ctrl:
            try:
                self.ctrl.shutdown()
            except Exception:
                pass
        if self._window:
            self._window.destroy()
