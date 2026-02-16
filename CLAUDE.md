# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TeleAuto is a Windows-only desktop automation tool (Python 3.11) that provides:
1. **Pritunl VPN autopilot** — manages VPN connections via `pritunl-client.exe` CLI, handles TOTP 2FA with NTP time sync, auto-reconnects
2. **Telemart client auto-login** — launches `Telemart.Client.exe` and performs UI-automated login via pywinauto

GitHub: `https://github.com/Shura4eburek/TeleAuto`

## Commands

```bash
# Run from source
python launcher.py

# Build standalone exe (requires TeleAuto.spec)
pyinstaller TeleAuto.spec
```

There are no test or lint commands configured.

## Architecture

**Entry point:** `launcher.py` → sets customtkinter dark theme → `App().mainloop()`

**Core orchestrator:** `src/teleauto/gui/app.py` — `App(ctk.CTk)` manages the full lifecycle:
- First-run: `ConfigWindow` → credentials setup
- PIN-protected: `PinWindow` → decrypt credentials → `MainView`
- Spawns daemon threads for VPN autopilot, Telemart login, network monitoring, update checking

**Threading pattern:** All background work runs in daemon threads. UI updates dispatch back to main thread via `widget.after(0, lambda: ...)`.

**Key modules:**
- `src/teleauto/vpn/pritunl_auto.py` — `PritunlAutopilot`: subprocess calls to `pritunl-client.exe list/start/stop`, TOTP generation, connection monitoring (5s interval), auto-import of `.ovpn` profiles
- `src/teleauto/login/login.py` — kills existing Telemart processes, launches exe, finds UI elements by automation ID (`LoginTextBox`, `PasswordBoxEdit`) via pywinauto UIA backend
- `src/teleauto/authenticator/totp_client.py` — TOTP with NTP correction (`pool.ntp.org`, fallback to Google HTTP `Date:` header)
- `src/teleauto/credentials.py` — AES-256-CBC encryption with Argon2id key derivation from PIN; all secrets stored in `credentials.json`
- `src/teleauto/updater.py` — checks GitHub Releases API, downloads new exe, generates `updater.bat` for self-replacement
- `src/teleauto/localization.py` — `TRANSLATIONS` dict with ru/en/ua; `tr(key, **kwargs)` for formatted messages
- `src/teleauto/gui/constants.py` — `VERSION`, color palette, font definitions

**Security model:** PIN → Argon2id (time_cost=3, memory_cost=65536, parallelism=4) → AES-256-CBC key. Each credential field gets a unique IV. PIN hash verified via bcrypt.

## Runtime Files (not in git)

- `credentials.json` — encrypted user credentials, TOTP secrets, settings
- `profiles.json` — discovered Pritunl profile names
- `profiles/` — `.ovpn` VPN profile files
- `launcher.py` — entry point (gitignored, user-customizable)

## Platform Constraints

Windows-only: uses `ctypes.windll` (DWM dark title bar), `subprocess.STARTUPINFO` (hidden console windows), `taskkill`, Windows GDI font loading, pywinauto UIA backend. No cross-platform support.

## Key Dependencies

customtkinter (UI framework), pywinauto 0.6.9 (UI automation), pyotp (TOTP), cryptography (AES), bcrypt/argon2 (PIN security), ntplib (NTP sync), psutil, pywin32
