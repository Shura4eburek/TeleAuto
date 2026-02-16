# src/teleauto/logger.py
import sys
import logging
from logging.handlers import RotatingFileHandler

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"
LOG_FILE = "teleauto.log"
LOG_MAX_BYTES = 1_000_000  # 1 MB
LOG_BACKUP_COUNT = 3


def setup_logging():
    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(logging.DEBUG)

    # Suppress noisy third-party loggers
    logging.getLogger("PIL").setLevel(logging.WARNING)

    # Console handler
    console = logging.StreamHandler(sys.__stdout__)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    root.addHandler(console)

    # File handler (rotating)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        root.addHandler(file_handler)
    except Exception:
        pass


class TextboxHandler(logging.Handler):
    """Logging handler that writes to a CTkTextbox widget via .after() for thread safety."""

    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        try:
            msg = self.format(record)
            if not msg.endswith("\n"):
                msg += "\n"
            self.textbox.after(0, self._write, msg)
        except Exception:
            self.handleError(record)

    def _write(self, msg):
        try:
            if self.textbox.winfo_exists():
                self.textbox.insert("end", msg)
                self.textbox.see("end")
        except Exception:
            pass


class StdoutToLogger:
    """Redirect stdout/stderr to logging.info() for print() compatibility."""

    def __init__(self, logger, level=logging.INFO):
        self._logger = logger
        self._level = level

    def write(self, message):
        if message and message.strip():
            self._logger.log(self._level, message.rstrip())

    def flush(self):
        pass
