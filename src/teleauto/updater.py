# src/teleauto/updater.py
import logging
import requests
import sys
import os
import re
import hashlib
import subprocess
from packaging import version
from src.teleauto.gui.constants import UPDATER_API_TIMEOUT
from src.teleauto.localization import tr

logger = logging.getLogger(__name__)

GITHUB_REPO = "Shura4eburek/TeleAuto"

# PE executable magic bytes
_PE_MAGIC = b"MZ"


def _verify_download(file_path, asset, release_body):
    """Verify downloaded file: size, PE header, and optional SHA-256 from release body."""
    # Check file size matches asset size
    expected_size = asset.get("size")
    if expected_size:
        actual_size = os.path.getsize(file_path)
        if actual_size != expected_size:
            logger.error(tr("log_upd_size_err", expected=expected_size, actual=actual_size))
            return False

    # Check PE header (MZ magic)
    with open(file_path, "rb") as f:
        header = f.read(2)
    if header != _PE_MAGIC:
        logger.error(tr("log_upd_not_pe"))
        return False

    # Check SHA-256 if present in release body
    if release_body:
        sha_match = re.search(r"SHA256:\s*([a-fA-F0-9]{64})", release_body)
        if sha_match:
            expected_hash = sha_match.group(1).lower()
            sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)
            actual_hash = sha256.hexdigest()
            if actual_hash != expected_hash:
                logger.error(tr("log_upd_sha_fail", expected=expected_hash, actual=actual_hash))
                return False
            logger.info(tr("log_upd_sha_ok"))

    return True


def check_and_download(current_ver):
    """Check GitHub for updates and download if newer version exists."""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        resp = requests.get(url, timeout=UPDATER_API_TIMEOUT)

        if resp.status_code != 200:
            return False, None

        data = resp.json()
        remote_tag = data.get("tag_name", "v0.0")

        if version.parse(remote_tag.replace("v", "")) <= version.parse(current_ver.replace("v", "")):
            return False, None

        logger.info(tr("log_upd_found", tag=remote_tag))

        exe_asset = None
        for asset in data.get("assets", []):
            if asset["name"].endswith(".exe"):
                exe_asset = asset
                break

        if not exe_asset:
            return False, None

        exe_url = exe_asset["browser_download_url"]
        new_exe_path = "TeleAuto_new.exe"
        with requests.get(exe_url, stream=True) as r:
            r.raise_for_status()
            with open(new_exe_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        # Verify the download
        release_body = data.get("body", "")
        if not _verify_download(new_exe_path, exe_asset, release_body):
            logger.error(tr("log_upd_verify_fail"))
            os.remove(new_exe_path)
            return False, None

        logger.info(tr("log_upd_verified", tag=remote_tag))
        return True, remote_tag

    except Exception as e:
        logger.error(tr("log_upd_err", e=e))
        return False, None


def create_update_batch():
    """Create BAT file for exe replacement on exit."""
    current_exe = os.path.basename(sys.executable)
    new_exe = "TeleAuto_new.exe"

    vbs_msg = 'MsgBox "TeleAuto updated successfully!", 64, "TeleAuto Update"'

    bat_content = f"""
@echo off
timeout /t 2 /nobreak > NUL
:loop
tasklist | find /i "{current_exe}" >nul
if %errorlevel%==0 (
    timeout /t 1 >nul
    goto loop
)
if exist "{current_exe}" del "{current_exe}"
if exist "{new_exe}" move "{new_exe}" "{current_exe}"

echo {vbs_msg} > success.vbs
cscript //nologo success.vbs
del success.vbs
del "%~f0"
"""
    with open("updater.bat", "w") as f:
        f.write(bat_content)


def schedule_update_on_exit():
    """Launch update mechanism silently."""
    create_update_batch()
    subprocess.Popen(["updater.bat"], shell=True, creationflags=0x08000000)
