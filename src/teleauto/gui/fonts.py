# src/teleauto/gui/fonts.py
import os
import sys
import ctypes

def resource_path(relative_path):
    """Для работы внутри PyInstaller EXE"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ИСПРАВЛЕНО: Обновлено имя файла по умолчанию
def load_custom_font(font_name="Unbounded-VariableFont_wght.ttf"):
    """Загружает шрифт в память только для этой сессии"""
    font_path = resource_path(font_name)
    if not os.path.exists(font_path):
        return False

    try:
        # FR_PRIVATE = 0x10
        num = ctypes.windll.gdi32.AddFontResourceExW(
            ctypes.c_wchar_p(font_path),
            ctypes.c_uint(0x10),
            0
        )
        return num > 0
    except Exception:
        return False