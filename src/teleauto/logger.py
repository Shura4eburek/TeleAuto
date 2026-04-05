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

    # Console handler — skipped in windowed exe where sys.__stdout__ is None
    if sys.__stdout__ is not None:
        console = logging.StreamHandler(sys.__stdout__)
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        root.addHandler(console)

    # File handler (rotating)
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        root.addHandler(file_handler)
    except Exception:
        pass


# ------------------------------------------------------------------
# Qt-based handler (thread-safe via pyqtSignal)
# ------------------------------------------------------------------
try:
    from PyQt6.QtCore import QObject, pyqtSignal, Qt as _Qt

    class _LogBridge(QObject):
        msg = pyqtSignal(str)

    class QtTextHandler(logging.Handler):
        """Thread-safe logging handler for QPlainTextEdit via Qt queued signal."""

        def __init__(self, text_edit):
            super().__init__()
            self.setFormatter(logging.Formatter("%(message)s"))
            self._text_edit = text_edit
            self._bridge = _LogBridge()
            self._bridge.msg.connect(self._write, _Qt.ConnectionType.QueuedConnection)

        def emit(self, record):
            try:
                text = self.format(record)
                if not text.endswith("\n"):
                    text += "\n"
                self._bridge.msg.emit(text)
            except Exception:
                self.handleError(record)

        def _write(self, text):
            try:
                te = self._text_edit
                if te is not None:
                    from PyQt6.QtGui import QTextCursor
                    te.moveCursor(QTextCursor.MoveOperation.End)
                    te.insertPlainText(text)
                    sb = te.verticalScrollBar()
                    sb.setValue(sb.maximum())
            except Exception:
                pass

except ImportError:
    pass  # PyQt6 not available — QtTextHandler won't exist


# ------------------------------------------------------------------
# Legacy CTk handler (kept for compatibility)
# ------------------------------------------------------------------
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
