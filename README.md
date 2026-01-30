<div align="center">

# TeleAuto 🤖

**Automation utility for Pritunl VPN & Telemart Client**

[![English](https://img.shields.io/badge/Language-English-blue?style=flat-square)](README.md)
[![Russian](https://img.shields.io/badge/Язык-Русский-gray?style=flat-square)](README.ru.md)
[![Ukrainian](https://img.shields.io/badge/Мова-Українська-gray?style=flat-square)](README.ua.md)

</div>

**TeleAuto** is a portable, secure Python application designed to automate routine network connection tasks. It handles secure VPN connections via Pritunl using dynamic profile discovery and 2FA (TOTP), and fully automates the login process for the Telemart client.

## ✨ Key Features

* **🛡️ Advanced VPN Automation (Pritunl):**
    * **Dynamic Discovery:** Automatically scans and detects all available Pritunl profiles (no hardcoded limits).
    * **Robust Time Sync:** Uses NTP with HTTP Fallback (Google/Microsoft) to bypass firewall blocks on port 123.
    * **Manual Offset:** Allows manual time correction (in seconds) if the VPN server clock is out of sync.
    * **Live TOTP Preview:** Real-time 2FA code preview in Settings to verify offset correctness.
    * **Auto-Reconnect:** Monitors connection status and automatically reconnects if dropped.
* **🛒 Telemart Automation:**
    * Auto-launch and secure auto-login to Telemart Client.
    * Smart window detection and input field handling.
* **🚀 Portable:**
    * Single standalone EXE file.
    * No installation required (fonts and assets included).
    * **Auto-Update:** Checks GitHub Releases and updates automatically over the air.
* **🌐 Localization:**
    * Interface available in English, Russian, and Ukrainian.

## 🔒 Security Architecture

Security is the core focus of this application:

* **AES-256-CBC Encryption:** All sensitive data (credentials, 2FA secrets) is encrypted using AES-256 with a unique Initialization Vector (IV) for every field, preventing pattern-based attacks.
* **Argon2id Key Derivation:** The master PIN is protected using the Argon2id hashing algorithm, providing superior resistance against GPU/ASIC-based brute-force attacks compared to legacy methods like PBKDF2 or SHA.
* **Memory Hygiene:** Decrypted credentials are never stored persistently in RAM. They are decrypted strictly on-demand and cleared from memory immediately after use.
* **Data Isolation:** Profile names (`profiles.json`) are separated from encrypted secrets (`credentials.json`), minimizing risk in case of file theft.
* **Log Sanitization:** The application masks sensitive information in all system outputs and logs.

## 🛠️ Tech Stack

* **Python 3.11**
* **GUI:** `CustomTkinter` (Modern Dark UI).
* **Automation:** `pywinauto` (Windows GUI automation).
* **Security:** `argon2-cffi`, `bcrypt`, `cryptography` (AES-256-CBC).
* **Network:** `pyotp` (2FA), `requests`, `ntplib`.

## 🚀 How to Use

1.  Download the latest `TeleAuto.exe` from the [Releases](../../releases) page.
2.  Run the application.
3.  **First Run:** Create a PIN code.
4.  Click the **Connect** button (this triggers the Pritunl profile scan).
5.  Open **Settings (⚙️)** and enter the 2FA secrets for the discovered profiles.
6.  Click **Save**. The app is now ready for fully automated operation.

---
*Developed by Mamoru*
