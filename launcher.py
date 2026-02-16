# launcher.py
import sys
import os

# Add current directory to path so Python can find src package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Hidden imports for PyInstaller
import bcrypt
import _cffi_backend  # bcrypt depends on this

from src.teleauto.logger import setup_logging
from src.teleauto.gui.app import App
import customtkinter

if __name__ == "__main__":
    setup_logging()

    customtkinter.set_appearance_mode("Dark")
    customtkinter.set_default_color_theme("blue")

    app = App()
    app.mainloop()
