# src/teleauto/gui/fonts.py
import os
import sys
import ctypes


def resource_path(relative_path):
    """Get absolute path — works for both source and PyInstaller EXE."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def load_custom_font(font_name="Unbounded-VariableFont_wght.ttf"):
    """Load font into Qt font database and GDI (Windows) for this session."""
    font_path = resource_path(font_name)
    if not os.path.exists(font_path):
        return False

    try:
        from PyQt6.QtGui import QFontDatabase
        font_id = QFontDatabase.addApplicationFont(font_path)
        # Also register via GDI for system-level font availability
        if sys.platform == "win32":
            ctypes.windll.gdi32.AddFontResourceExW(
                ctypes.c_wchar_p(font_path), ctypes.c_uint(0x10), 0
            )
        return font_id >= 0
    except Exception:
        return False
