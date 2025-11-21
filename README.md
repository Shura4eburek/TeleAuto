<div align="center">

# TeleAuto 🤖

**Automation utility for Pritunl VPN & Telemart Client**

[![English](https://img.shields.io/badge/Language-English-blue?style=flat-square)](README.md)
[![Russian](https://img.shields.io/badge/Язык-Русский-gray?style=flat-square)](README.ru.md)
[![Ukrainian](https://img.shields.io/badge/Мова-Українська-gray?style=flat-square)](README.ua.md)

</div>

**TeleAuto** is a portable Python application designed to automate routine network connection tasks. It handles secure VPN connections via Pritunl using 2FA (TOTP) and automates the login process for the Telemart client.

## ✨ Key Features

* **🛡️ Automated VPN Connection:**
    * Automatically detects Pritunl status.
    * Connects to specified profiles (P1, P2, P3).
    * **Auto-2FA:** Generates and enters TOTP codes automatically.
    * **Auto-Reconnect:** Monitors connection status and reconnects if dropped.
* **🛒 Telemart Automation:**
    * Auto-launch and auto-login to Telemart Client.
    * Handles window detection and input fields securely.
* **🔒 Security:**
    * **AES Encryption:** Credentials and secrets are encrypted.
    * **PIN Protection:** Application startup and settings are protected by a PIN code.
* **🚀 Portable:**
    * Single EXE file.
    * No installation required (fonts included).
    * **Auto-Update:** Checks GitHub Releases for new versions and updates automatically.
* **🌐 Localization:**
    * Interface available in English, Russian, and Ukrainian.

## 🛠️ Tech Stack

* **Python 3.11**
* **GUI:** `CustomTkinter` (Modern Dark UI).
* **Automation:** `pywinauto` (Windows GUI automation).
* **Security:** `bcrypt`, `cryptography` (Fernet).
* **Network:** `pyotp` (2FA), `requests`.

## 🚀 How to Use

1.  Download the latest `TeleAuto.exe` from the [Releases](../../releases) page.
2.  Run the application.
3.  **First Run:** Set up your PIN code and enter your credentials (VPN secrets, Login/Pass).
4.  The application will minimize to tray or run in the background, keeping your connection alive.

---
*Developed by Mamoru*
