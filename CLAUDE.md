# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TeleAuto is a Windows-only desktop automation tool (Python 3.11 + React) that provides:
1. **Pritunl VPN autopilot** — manages VPN connections via `pritunl-client.exe` CLI, handles TOTP 2FA with NTP time sync, auto-reconnects
2. **Telemart client auto-login** — launches `Telemart.Client.exe` and performs UI-automated login via pywinauto

GitHub: `https://github.com/Shura4eburek/TeleAuto`

## Setup (fresh clone)

### Python
```bash
pip install -r requirements.txt
```

### Frontend (React)
```bash
cd design
npm install
npm run build   # produces design/dist/ — required for launcher.py and PyInstaller
cd ..
```

### Runtime files (create manually, not in git)
- `profiles/` — place `.ovpn` files here for VPN profiles
- `credentials.json` — created automatically on first run

## Commands

```bash
# Run from source (auto-installs missing pip packages on first run)
python launcher.py

# Build standalone exe
pyinstaller TeleAuto.spec

# Frontend dev server (hot reload, no Python backend)
cd design && npm run dev

# Lint Python
ruff check src/
```

There are no test commands configured.

## Architecture

### Frontend — `design/`
React + TypeScript + Vite + Tailwind + framer-motion.

- `design/src/App.tsx` — single-file SPA: all views (Config, Pin, Main, Shutdown), state management, pywebview JS API calls via `window.pywebview.api.*`
- `design/src/i18n.ts` — all UI strings for ua/ru/en. **Single source of truth for frontend translations.** Add keys here when adding new UI text.
- `design/src/index.css` — global styles, scrollbar suppression
- `design/dist/` — built output (gitignored, regenerate with `npm run build`)

**View transitions:** framer-motion `AnimatePresence` with opacity-only fade (no transforms — transforms cause WebView2 scrollbar flash).

### Python bridge — `src/teleauto/webapi.py`
`App` class exposed to JS via `js_api=app` in `webview.create_window()`.
- All public methods are callable from JS as `window.pywebview.api.method_name()`
- Push events to frontend via `self._push({"type": "...", ...})` → JS receives via `window.__pushEvent`
- `update_net_status(connected, ping)` → pushes `net_status` event
- `get_initial_state()` → called on window load to hydrate frontend state
- `save_config()` — validates PIN (required, min 4 chars, must match), saves credentials
- `save_settings()` — handles settings updates including PIN change
- `open_url(url)` — only allows `https://` URLs (security constraint)

### Entry point — `launcher.py`
1. Checks and installs missing pip packages (source mode only, skipped in `.exe`)
2. Injects tkinter shim (controller.py uses `messagebox` — redirected to logger)
3. Creates `webview.create_window()` with `js_api=App()`
4. On window load: calls `app.get_initial_state()` and pushes `init` event

### Business logic — `src/teleauto/controller.py`
`AppController` owns all non-UI state and background threads.
- `App` (webapi.py) holds a reference as `self.ctrl`
- Threading: `ThreadPoolExecutor(max_workers=4)` via `AppController.submit(fn)`
- UI updates: controller calls `self.ui._push({"type": "..."})` — never touch DOM directly
- Do NOT spawn raw threads from webapi.py — always use `ctrl.submit()`

### Key Python modules
- `src/teleauto/vpn/pritunl_auto.py` — `PritunlAutopilot`: subprocess calls to `pritunl-client.exe list/start/stop`, TOTP generation, 5s monitoring loop, auto-import `.ovpn`
- `src/teleauto/login/login.py` — kills existing Telemart processes, launches exe, finds UI elements by automation ID (`LoginTextBox`, `PasswordBoxEdit`) via pywinauto UIA backend
- `src/teleauto/authenticator/totp_client.py` — TOTP with NTP correction (`pool.ntp.org`, fallback to Google HTTP `Date:` header)
- `src/teleauto/credentials.py` — AES-256-CBC + Argon2id key derivation from PIN. PIN is **mandatory** — `save_credentials()` raises `ValueError` if PIN is empty
- `src/teleauto/updater.py` — checks GitHub Releases API, downloads new exe, generates `updater.bat` for self-replacement. Paths are PS-escaped to prevent injection.
- `src/teleauto/localization.py` — `TRANSLATIONS` dict with ru/en/ua for **backend log/error messages**. `tr(key, **kwargs)` for formatted strings. (UI strings live in `design/src/i18n.ts`)
- `src/teleauto/gui/constants.py` — `VERSION`, color palette, timing constants. **Bump `VERSION` here when releasing.**
- `src/teleauto/network/network_utils.py` — `check_internet_ping()`, `wait_for_internet()`: subprocess ping, cancellable via threading.Event
- `src/teleauto/unable/service_ui.py` — pywinauto wrapper for Telemart navigation
- `src/teleauto/unable/work_place.py` — automates workplace ComboBox selection post-login
- `src/teleauto/utilities/` — dev/debug helpers (element_viewer, TOTP offset tester, etc.)

## Security model

- PIN → Argon2id (time_cost=3, memory_cost=65536, parallelism=4) → AES-256-CBC key
- Each credential field encrypted with a unique IV
- PIN hash verified via bcrypt
- PIN is mandatory (min 4 chars) — no plaintext fallback
- Logger writes INFO+ to file (no DEBUG to prevent sensitive data leakage)
- `open_url()` blocks non-https URLs

## Build pipeline

1. `cd design && npm run build` — produces `design/dist/`
2. `pyinstaller TeleAuto.spec` — bundles Python + `design/dist/` + WebView2 DLLs into single `dist/TeleAuto.exe`

`TeleAuto.spec` includes:
- `design/dist/` as data (React frontend)
- `webview/lib/` — WebView2Loader.dll, .NET assemblies
- `webview/js/` — pywebview JS bridge
- Hidden imports: `webview.platforms.winforms`, `clr`, `pythonnet`, `PIL`, `pystray`

## Runtime files (not in git)

- `credentials.json` — encrypted credentials (auto-created on first run)
- `profiles.json` — discovered Pritunl profile names (auto-created)
- `profiles/` — `.ovpn` VPN profile files (place manually)
- `dist/TeleAuto.exe` — build artifact

## Platform constraints

Windows-only: WebView2 (EdgeChromium), pywinauto UIA backend, `ctypes.windll`, `subprocess.STARTUPINFO`, `taskkill`, pywin32, Windows GDI fonts.

## Key dependencies

| Package | Purpose |
|---|---|
| pywebview ≥ 5.3 | Native window with WebView2 backend |
| pythonnet / clr | .NET interop for WebView2 WinForms |
| pywinauto 0.6.9 | UI automation for Telemart |
| pyotp | TOTP generation |
| cryptography | AES-256-CBC |
| argon2-cffi | Argon2id key derivation |
| bcrypt | PIN hash verification |
| ntplib | NTP time sync |
| psutil | Process management |
| pywin32 | Windows API |
| pystray | System tray icon |
| pillow | Tray icon image handling |
| requests | GitHub API for updates |
| packaging | Version comparison |
