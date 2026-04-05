# launcher.py
import sys
import os
import types

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Hidden imports for PyInstaller
import bcrypt
import _cffi_backend  # bcrypt depends on this

# ---------------------------------------------------------------------------
# Tkinter shim — controller.py uses messagebox for one error dialog.
# With pywebview, errors go to the log instead.
# ---------------------------------------------------------------------------
class _MsgBox:
    @staticmethod
    def showerror(title="Error", message="", **kw):
        import logging
        logging.getLogger(__name__).error("%s: %s", title, message)

    @staticmethod
    def showinfo(title="Info", message="", **kw):
        import logging
        logging.getLogger(__name__).info("%s: %s", title, message)

    @staticmethod
    def askyesno(title="", message="", **kw):
        return False


if "tkinter" not in sys.modules:
    sys.modules["tkinter"] = types.ModuleType("tkinter")
sys.modules["tkinter"].messagebox = _MsgBox()         # type: ignore[attr-defined]
sys.modules["tkinter.messagebox"] = _MsgBox()         # type: ignore[assignment]

# ---------------------------------------------------------------------------
import webview

from src.teleauto.logger import setup_logging
from src.teleauto.controller import AppController
from src.teleauto.webapi import App


def _get_html_path() -> str:
    try:
        base = sys._MEIPASS  # PyInstaller bundle
    except AttributeError:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "design", "dist")
    return os.path.join(base, "index.html")


if __name__ == "__main__":
    setup_logging()

    app = App()
    ctrl = AppController(ui=app)
    app.ctrl = ctrl

    html_path = _get_html_path()

    window = webview.create_window(
        title="TeleAuto",
        url=html_path,
        js_api=app,
        width=650,
        height=580,
        min_size=(320, 300),
        resizable=True,
        frameless=True,
        background_color="#0d0d0d",
    )

    def on_loaded():
        app.set_window(window)
        state = app.get_initial_state()
        app._push({"type": "init", **state})

    window.events.loaded += on_loaded

    webview.start(debug=False)
