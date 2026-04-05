# src/teleauto/gui/utils.py
import sys
import ctypes


def apply_dark_title_bar(widget):
    """Apply DWM dark title bar on Windows for a Qt widget."""
    if not sys.platform.startswith("win"):
        return
    try:
        hwnd = int(widget.winId())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), 4
        )
    except Exception:
        pass


def apply_window_settings(widget):
    """Apply dark title bar and bring window to front."""
    apply_dark_title_bar(widget)
    try:
        widget.raise_()
        widget.activateWindow()
    except Exception:
        pass
