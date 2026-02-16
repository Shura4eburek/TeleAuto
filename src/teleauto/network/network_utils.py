# src/teleauto/network/network_utils.py
import subprocess
import logging
import time
import re
import platform
from src.teleauto.localization import tr
from src.teleauto.gui.constants import PING_TIMEOUT

logger = logging.getLogger(__name__)


def wait_for_internet(host="1.1.1.1", timeout=5, retry_interval=5, cancel_event=None):
    logger.info(tr("log_net_checking", host=host))
    while True:
        if cancel_event and cancel_event.is_set():
            return False

        try:
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(timeout * 1000), host],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            if "TTL=" in result.stdout:
                logger.info(tr("log_net_available"))
                return True
            else:
                logger.info(tr("log_net_unavailable"))
        except Exception as e:
            logger.error(tr("log_net_ping_err", e=e))

        for _ in range(retry_interval * 2):
            if cancel_event and cancel_event.is_set():
                return False
            time.sleep(0.5)


def check_internet_ping(host="1.1.1.1", timeout=None):
    if timeout is None:
        timeout = PING_TIMEOUT
    try:
        startupinfo = None
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        command = ["ping", "-n", "1", "-w", str(timeout), host]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )

        output = result.stdout
        if "TTL=" in output:
            match = re.search(r"(?:time|время)[=<]([\d\.]+)\s*(?:ms|мс)", output.lower())
            ping = int(float(match.group(1))) if match else 0
            return True, ping
        else:
            return False, None
    except Exception:
        return False, None
