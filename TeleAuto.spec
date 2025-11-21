# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import sys
import os

# --- НАСТРОЙКА ---
# Убедитесь, что путь к шрифту правильный
font_name = 'Unbounded-VariableFont_wght.ttf' 
# -----------------

datas = [(font_name, '.')]
binaries = []
hiddenimports = [
    'bcrypt', 
    '_cffi_backend',  # Критически важно для bcrypt
    'cffi',
    'src.teleauto.gui', # Помогаем найти наши пакеты
    'src.teleauto.credentials'
]

# Сбор всех данных из библиотек (bcrypt, cffi, customtkinter)
for lib in ['bcrypt', 'cffi', 'customtkinter']:
    tmp_ret = collect_all(lib)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

block_cipher = None

a = Analysis(
    ['launcher.py'],  # <--- СОБИРАЕМ ЧЕРЕЗ НОВЫЙ ФАЙЛ
    pathex=[os.getcwd()], # Явно указываем текущую папку как корень
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TeleAuto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Ставьте True, если хотите видеть ошибки в консоли при запуске
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)