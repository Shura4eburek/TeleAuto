# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# pywebview data: DLLs, JS bridge, .NET assemblies
webview_datas    = collect_data_files('webview', subdir='lib')
webview_datas   += collect_data_files('webview', subdir='js')
webview_binaries = collect_dynamic_libs('webview')

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=webview_binaries,
    datas=[
        # App icon
        ('icon.ico', '.'),
        # Custom font
        ('src/teleauto/gui/fonts/Unbounded-VariableFont_wght.ttf', '.'),
        # React frontend
        ('design/dist', '.'),
        # pywebview runtime files
        *webview_datas,
    ],
    hiddenimports=[
        # crypto / auth
        'bcrypt',
        '_cffi_backend',
        # pywebview Windows backends
        'webview',
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'webview.platforms.mshtml',
        # pythonnet (required by winforms backend)
        'clr',
        'clr_loader',
        'pythonnet',
        # PIL / pystray
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'pystray',
        # misc
        'psutil',
        'win32api',
        'win32con',
        'win32gui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TeleAuto',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
