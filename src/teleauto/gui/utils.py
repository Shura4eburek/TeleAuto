import sys
import ctypes

def apply_window_settings(window):
    """Применяет темный заголовок (Windows) и модальность."""
    # 1. Dark Title Bar
    if sys.platform.startswith("win"):
        try:
            window.update()
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            get_parent = ctypes.windll.user32.GetParent
            hwnd = get_parent(window.winfo_id())
            value = 2
            set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(value)), 4)
        except Exception: pass

    # 2. Modality
    try:
        window.lift()
        window.focus_force()
        window.grab_set()
    except Exception: pass