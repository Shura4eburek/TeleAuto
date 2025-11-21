# launcher.py
import sys
import os

# Добавляем текущую директорию в путь, чтобы Python видел папку src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Явный импорт bcrypt, чтобы PyInstaller его точно заметил
import bcrypt
import _cffi_backend  # bcrypt зависит от этого, часто теряется

from src.teleauto.gui.app import App
import customtkinter

if __name__ == "__main__":
    # Настройки темы (на всякий случай дублируем)
    customtkinter.set_appearance_mode("Dark")
    customtkinter.set_default_color_theme("blue")

    app = App()
    app.mainloop()