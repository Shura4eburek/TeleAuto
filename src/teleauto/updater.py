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
_PE_MAGIC = b"MZ"
_NEW_EXE_NAME = "TeleAuto_new.exe"


def _is_packaged():
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _get_new_exe_path():
    if _is_packaged():
        return os.path.join(os.path.dirname(sys.executable), _NEW_EXE_NAME)
    return _NEW_EXE_NAME


def _verify_download(file_path, asset, release_body):
    """Verify downloaded file: size, PE header, and optional SHA-256 from release body."""
    expected_size = asset.get("size")
    if expected_size:
        actual_size = os.path.getsize(file_path)
        if actual_size != expected_size:
            logger.error(tr("log_upd_size_err", expected=expected_size, actual=actual_size))
            return False

    with open(file_path, "rb") as f:
        header = f.read(2)
    if header != _PE_MAGIC:
        logger.error(tr("log_upd_not_pe"))
        return False

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


def check_for_update(current_ver):
    """
    Fast API-only check. Does NOT download anything.
    Returns (tag, asset_info) if update is available, or (None, None).
    """
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        resp = requests.get(url, timeout=UPDATER_API_TIMEOUT)

        if resp.status_code != 200:
            return None, None

        data = resp.json()
        remote_tag = data.get("tag_name", "v0.0")

        if version.parse(remote_tag.replace("v", "")) <= version.parse(current_ver.replace("v", "")):
            return None, None

        logger.info(tr("log_upd_found", tag=remote_tag))

        for asset in data.get("assets", []):
            if asset["name"].endswith(".exe"):
                return remote_tag, {"asset": asset, "body": data.get("body", "")}

        return None, None

    except Exception as e:
        logger.error(tr("log_upd_err", e=e))
        return None, None


def download_update(asset_info):
    """
    Download and verify new exe.
    Returns path to downloaded file, or None on failure.
    """
    asset = asset_info["asset"]
    body = asset_info.get("body", "")
    new_exe_path = _get_new_exe_path()

    try:
        logger.info(tr("log_upd_downloading"))
        with requests.get(asset["browser_download_url"], stream=True) as r:
            r.raise_for_status()
            with open(new_exe_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        if not _verify_download(new_exe_path, asset, body):
            logger.error(tr("log_upd_verify_fail"))
            os.remove(new_exe_path)
            return None

        logger.info(tr("log_upd_verified", tag=asset["name"]))
        return new_exe_path

    except Exception as e:
        logger.error(tr("log_upd_err", e=e))
        if os.path.exists(new_exe_path):
            os.remove(new_exe_path)
        return None


def apply_update(new_exe_path):
    """
    Launch a PowerShell script that waits for this process to exit,
    replaces the exe with the new one, and relaunches it.
    Only works when running as a packaged exe (PyInstaller).
    Returns True if the updater was launched successfully.
    """
    if not _is_packaged():
        logger.warning("Update skipped: not running as packaged exe")
        return False

    try:
        current_exe = os.path.abspath(sys.executable)
        new_exe_abs = os.path.abspath(new_exe_path)
        proc_name = os.path.splitext(os.path.basename(current_exe))[0]
        ps_path = os.path.join(os.path.dirname(current_exe), "updater.ps1")

        ps_script = (
            f"$old = '{current_exe}'\n"
            f"$new = '{new_exe_abs}'\n"
            f"$name = '{proc_name}'\n"
            "\n"
            "# Wait for the app to exit\n"
            "do {\n"
            "    Start-Sleep -Milliseconds 300\n"
            "} while (Get-Process -Name $name -ErrorAction SilentlyContinue)\n"
            "\n"
            "Start-Sleep -Milliseconds 500\n"
            "Remove-Item $old -Force -ErrorAction SilentlyContinue\n"
            "Move-Item $new $old -Force\n"
            "Start-Process $old\n"
            "Remove-Item $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue\n"
        )

        with open(ps_path, "w", encoding="utf-8") as f:
            f.write(ps_script)

        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", ps_path],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        logger.info(tr("log_upd_applying"))
        return True

    except Exception as e:
        logger.error(tr("log_upd_err", e=e))
        return False
