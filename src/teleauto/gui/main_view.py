# src/teleauto/gui/main_view.py
import sys
import logging

from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QPlainTextEdit,
    QVBoxLayout, QHBoxLayout, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QPainterPath,
)

from src.teleauto.localization import tr
from src.teleauto.logger import QtTextHandler, StdoutToLogger
from .constants import MAIN_FONT_FAMILY, BODY_FONT, VERSION
from .widgets import LEDWidget, GradientIcon, DragWidget, WiFiIcon, ActivityIcon

# ── Palette ────────────────────────────────────────────────────────────────
_WIN_BG    = "#1E1E1E"          # window background
_WIN_BORD  = "rgba(255,255,255,51)"  # ~20% white border
_TEXT      = "#FFFFFF"
_TEXT70    = "rgba(255,255,255,178)"  # white/70
_TEXT60    = "rgba(255,255,255,153)"  # white/60
_TEXT50    = "rgba(255,255,255,128)"  # white/50
_TEXT40    = "rgba(255,255,255,102)"  # white/40
_GREEN     = "#34C759"
_BLUE      = "#0A84FF"
_ORANGE    = "#FF9F0A"
_RED_LIGHT = "#FF5F56"
_YLW_LIGHT = "#FFBD2E"
_GRN_LIGHT = "#27C93F"

# Group container colour
_GRP_BG   = "rgba(255,255,255,15)"   # white/6
_GRP_BORD = "rgba(255,255,255,20)"   # white/8
_ROW_BORD = "rgba(255,255,255,15)"   # white/6

# State → text colour
_STATE_COLOR = {
    "success":    _GREEN,
    "error":      "#FF453A",
    "working":    _ORANGE,
    "connecting": _ORANGE,
    "off":        _TEXT60,
    "waiting":    _TEXT60,
}

# ── Button stylesheets ────────────────────────────────────────────────────
_BTN_PRIMARY = f"""
    QPushButton {{
        background: {_BLUE}; color: {_TEXT};
        border: 1px solid {_BLUE};
        border-radius: 6px;
        font-family: "{BODY_FONT}"; font-size: 12px; font-weight: 600;
        padding: 4px 12px;
    }}
    QPushButton:hover  {{ background: #007AFF; }}
    QPushButton:disabled {{ background: rgba(255,255,255,20); color: {_TEXT50}; border-color: transparent; }}
"""
_BTN_MUTED = f"""
    QPushButton {{
        background: rgba(255,255,255,25); color: {_TEXT};
        border: 1px solid rgba(255,255,255,25);
        border-radius: 6px;
        font-family: "{BODY_FONT}"; font-size: 12px; font-weight: 600;
        padding: 4px 12px;
    }}
    QPushButton:hover {{ background: rgba(255,255,255,50); }}
    QPushButton:disabled {{ color: {_TEXT50}; }}
"""
_BTN_CANCEL = f"""
    QPushButton {{
        background: rgba(255,79,58,0.2); color: #FF453A;
        border: 1px solid rgba(255,79,58,0.3);
        border-radius: 6px;
        font-family: "{BODY_FONT}"; font-size: 12px; font-weight: 600;
        padding: 4px 12px;
    }}
    QPushButton:hover {{ background: rgba(255,79,58,0.35); }}
"""
_BTN_ICON = f"""
    QPushButton {{
        background: transparent; color: {_TEXT50};
        border: none; border-radius: 6px;
        font-size: 14px; padding: 3px;
    }}
    QPushButton:hover {{ background: rgba(255,255,255,20); color: {_TEXT}; }}
"""
_BTN_TRAFFIC = """
    QPushButton {{
        background: {color}; border: 1px solid {border};
        border-radius: 6px; min-width: 12px; max-width: 12px;
        min-height: 12px; max-height: 12px;
    }}
    QPushButton:hover {{ background: {hover}; }}
"""


def _traffic_btn(color: str, border: str, hover: str) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(12, 12)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {color};
            border: 1px solid {border};
            border-radius: 6px;
        }}
        QPushButton:hover {{ background: {hover}; }}
    """)
    return btn


def _row_separator() -> QFrame:
    sep = QFrame()
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background: {_ROW_BORD}; border: none;")
    return sep


# ── Small helper widgets ───────────────────────────────────────────────────
class _GlowDot(QWidget):
    def __init__(self, color: str = "#34C759", size: int = 8, parent=None):
        super().__init__(parent)
        s = size + 8
        self.setFixedSize(s, s)
        self._c = QColor(color)
        self._s = size

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() / 2; cy = self.height() / 2
        gc = QColor(self._c); gc.setAlpha(60)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(gc)
        r = self._s / 2 + 3
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        p.setBrush(self._c)
        r2 = self._s / 2
        p.drawEllipse(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2))


class _PulseDot(QWidget):
    """Animated pulsing dot for monitor status."""

    def __init__(self, color: str = "#34C759", size: int = 8, parent=None):
        super().__init__(parent)
        self.setFixedSize(size + 8, size + 8)
        self._color = QColor(color)
        self._off_color = QColor("#333333")
        self._size = size
        self._on = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._active = False

    def set_state(self, state: str):
        if state == "success":
            self._color = QColor("#34C759")
            self._active = True
            self._timer.start(800)
        elif state == "working":
            self._color = QColor("#FFD60A")
            self._active = True
            self._timer.start(400)
        elif state == "error":
            self._color = QColor("#FF453A")
            self._active = False
            self._timer.stop()
        else:
            self._active = False
            self._timer.stop()
        self.update()

    def _tick(self):
        self._on = not self._on
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx = self.width() / 2; cy = self.height() / 2
        c = self._color if (not self._active or self._on) else QColor(self._color.red(), self._color.green(), self._color.blue(), 80)
        if self._active and self._on:
            gc = QColor(c); gc.setAlpha(80)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(gc)
            r = self._size / 2 + 3
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c if self._active else QColor("#333333"))
        r2 = self._size / 2
        p.drawEllipse(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2))


class _FooterBar(QWidget):
    """Footer with painted top border."""

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        p.drawLine(0, 0, self.width(), 0)


# ═══════════════════════════════════════════════════════════════════════════
class MainWindow(QWidget):
    """Central widget — matches the new macOS-style frameless design."""

    def __init__(self, master_app):
        super().__init__()
        self.master_app = master_app
        self.is_expanded = False
        self._telemart_mode = "start"

        # Window background (painted in paintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        # Scrollable content area
        content = QWidget()
        content.setStyleSheet("QWidget { background: transparent; }")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.setSpacing(16)
        cl.addWidget(self._build_service_group())
        self._log_frame = self._build_log()
        self._log_frame.hide()
        cl.addWidget(self._log_frame, stretch=1)
        cl.addStretch(0)
        root.addWidget(content, stretch=1)

        root.addWidget(self._build_footer())

    # ─────────────────────────────────────────── paintEvent (window bg + border)
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Fill rounded rect
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(_WIN_BG))
        p.drawRoundedRect(QRectF(self.rect()), 12, 12)
        # Border
        p.setPen(QPen(QColor(255, 255, 255, 51), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 11.5, 11.5)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    # ─────────────────────────────────────────── header
    def _build_header(self) -> QWidget:
        hdr = DragWidget()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet("QWidget { background: transparent; }")

        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(0)

        # Traffic lights
        tl_wrap = QWidget()
        tl_wrap.setStyleSheet("QWidget { background: transparent; }")
        tl = QHBoxLayout(tl_wrap)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(8)

        btn_close = _traffic_btn(_RED_LIGHT, "#E0443E", "#E04040")
        btn_close.clicked.connect(self.master_app.on_close_btn)
        btn_min = _traffic_btn(_YLW_LIGHT, "#DEA123", "#DFAE20")
        btn_min.clicked.connect(self.master_app.showMinimized)
        btn_max = _traffic_btn(_GRN_LIGHT, "#1AAB29", "#20C030")
        btn_max.clicked.connect(self.master_app.toggle_maximize)
        for b in (btn_close, btn_min, btn_max):
            tl.addWidget(b)
        lay.addWidget(tl_wrap)

        lay.addStretch()

        # Centered title
        title = QLabel("TeleAuto")
        title.setFont(QFont(MAIN_FONT_FAMILY, 13))
        title.setStyleSheet(f"color: rgba(255,255,255,230); font-weight: 600; border: none; background: transparent;")
        lay.addWidget(title)
        lay.addSpacing(6)
        badge = QLabel(f" {VERSION} ")
        badge.setFont(QFont(BODY_FONT, 10))
        badge.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        badge.setContentsMargins(0, 2, 0, 2)
        badge.setStyleSheet("""
            color: rgba(255,255,255,178);
            background: rgba(255,255,255,25);
            border: 1px solid rgba(255,255,255,12);
            border-radius: 4px;
        """)
        lay.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)

        lay.addStretch()

        # Right: LED + settings
        self._status_dot = _GlowDot(_GREEN, 8)
        lay.addWidget(self._status_dot)
        lay.addSpacing(10)

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(26, 26)
        settings_btn.setStyleSheet(_BTN_ICON)
        settings_btn.clicked.connect(self.master_app.open_settings_window)
        lay.addWidget(settings_btn)

        return hdr

    # ─────────────────────────────────────────── service group
    def _build_service_group(self) -> QWidget:
        grp = QFrame()
        grp.setStyleSheet(f"""
            QFrame#service_group {{
                background: {_GRP_BG};
                border: 1px solid {_GRP_BORD};
                border-radius: 10px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        grp.setObjectName("service_group")

        lay = QVBoxLayout(grp)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._pritunl_row  = self._build_pritunl_row()
        self._telemart_row = self._build_telemart_row()
        self._monitor_row  = self._build_monitor_row()

        lay.addWidget(self._pritunl_row)
        lay.addWidget(_row_separator())
        lay.addWidget(self._telemart_row)
        lay.addWidget(_row_separator())
        lay.addWidget(self._monitor_row)

        return grp

    def _row(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("QWidget { background: transparent; } QLabel { border: none; background: transparent; }")
        return w

    def _build_pritunl_row(self) -> QWidget:
        row = self._row()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        lay.addWidget(GradientIcon("lock"))

        text = QVBoxLayout()
        text.setSpacing(2)
        t = QLabel("Pritunl VPN")
        t.setFont(QFont(BODY_FONT, 14, QFont.Weight.Medium))
        t.setStyleSheet(f"color: {_TEXT}; border: none; background: transparent;")
        self._pritunl_status = QLabel(tr("status_waiting"))
        self._pritunl_status.setFont(QFont(BODY_FONT, 12))
        self._pritunl_status.setStyleSheet(f"color: {_TEXT60}; border: none; background: transparent;")
        text.addWidget(t)
        text.addWidget(self._pritunl_status)
        lay.addLayout(text)
        lay.addStretch()

        self.pritunl_connect_btn = QPushButton("Connect")
        self.pritunl_connect_btn.setStyleSheet(_BTN_PRIMARY)
        self.pritunl_connect_btn.clicked.connect(self.master_app.on_pritunl_connect_click)
        lay.addWidget(self.pritunl_connect_btn)

        self.pritunl_cancel_btn = QPushButton(tr("btn_cancel"))
        self.pritunl_cancel_btn.setStyleSheet(_BTN_CANCEL)
        self.pritunl_cancel_btn.clicked.connect(self.master_app.on_cancel_pritunl_click)
        self.pritunl_cancel_btn.hide()
        lay.addWidget(self.pritunl_cancel_btn)

        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setStyleSheet(_BTN_MUTED)
        self.disconnect_button.clicked.connect(self.master_app.on_disconnect_click)
        self.disconnect_button.hide()
        lay.addWidget(self.disconnect_button)

        return row

    def _build_telemart_row(self) -> QWidget:
        row = self._row()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        lay.addWidget(GradientIcon("monitor"))

        text = QVBoxLayout()
        text.setSpacing(2)
        t = QLabel("Telemart App")
        t.setFont(QFont(BODY_FONT, 14, QFont.Weight.Medium))
        t.setStyleSheet(f"color: {_TEXT}; border: none; background: transparent;")
        self._telemart_status = QLabel(tr("status_waiting"))
        self._telemart_status.setFont(QFont(BODY_FONT, 12))
        self._telemart_status.setStyleSheet(f"color: {_TEXT60}; border: none; background: transparent;")
        text.addWidget(t)
        text.addWidget(self._telemart_status)
        lay.addLayout(text)
        lay.addStretch()

        self.start_telemart_button = QPushButton(tr("btn_start"))
        self.start_telemart_button.setStyleSheet(_BTN_PRIMARY)
        self.start_telemart_button.clicked.connect(self._on_telemart_btn)
        lay.addWidget(self.start_telemart_button)

        return row

    def _build_monitor_row(self) -> QWidget:
        row = self._row()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        lay.addWidget(GradientIcon("activity"))

        text = QVBoxLayout()
        text.setSpacing(2)
        t = QLabel("System Monitor")
        t.setFont(QFont(BODY_FONT, 14, QFont.Weight.Medium))
        t.setStyleSheet(f"color: {_TEXT}; border: none; background: transparent;")
        self._monitor_status = QLabel(tr("status_waiting"))
        self._monitor_status.setFont(QFont(BODY_FONT, 12))
        self._monitor_status.setStyleSheet(f"color: {_TEXT60}; border: none; background: transparent;")
        text.addWidget(t)
        text.addWidget(self._monitor_status)
        lay.addLayout(text)
        lay.addStretch()

        self.monitor_led = _PulseDot(_GREEN, 8)
        lay.addWidget(self.monitor_led)
        self.monitor_led.set_state("off")

        return row

    # ─────────────────────────────────────────── log
    def _build_log(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("QWidget { background: transparent; }")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        hdr_row = QWidget()
        hdr_row.setStyleSheet("QWidget { background: transparent; }")
        hr_lay = QHBoxLayout(hdr_row)
        hr_lay.setContentsMargins(2, 0, 2, 0)
        hr_lay.setSpacing(6)
        term_lbl = QLabel("›")
        term_lbl.setFont(QFont(BODY_FONT, 12))
        term_lbl.setStyleSheet(f"color: {_TEXT50}; border: none; background: transparent;")
        hr_lay.addWidget(term_lbl)
        log_title = QLabel("ACTIVITY LOG")
        log_title.setFont(QFont(BODY_FONT, 11))
        log_title.setStyleSheet(f"color: {_TEXT50}; letter-spacing: 1px; font-weight: 600; border: none; background: transparent;")
        hr_lay.addWidget(log_title)
        hr_lay.addStretch()
        lay.addWidget(hdr_row)

        self.log_textbox = QPlainTextEdit()
        self.log_textbox.setReadOnly(True)
        self.log_textbox.setFont(QFont("Consolas", 11))
        self.log_textbox.setStyleSheet(f"""
            QPlainTextEdit {{
                background: rgba(0,0,0,102);
                color: rgba(255,255,255,178);
                border: 1px solid rgba(255,255,255,13);
                border-radius: 10px;
                padding: 10px;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 4px; margin: 4px 2px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,60); border-radius: 2px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        lay.addWidget(self.log_textbox)
        return w

    def expand_log(self):
        if self.is_expanded:
            return
        self.is_expanded = True
        self._log_frame.show()
        handler = QtTextHandler(self.log_textbox)
        logging.getLogger().addHandler(handler)
        log = logging.getLogger("stdout")
        sys.stdout = StdoutToLogger(log, logging.INFO)
        sys.stderr = StdoutToLogger(log, logging.ERROR)

    # ─────────────────────────────────────────── footer
    def _build_footer(self) -> QWidget:
        bar = _FooterBar()
        bar.setFixedHeight(40)
        bar.setStyleSheet("""
            QWidget { background: rgba(255,255,255,5); }
            QLabel  { border: none; background: transparent; }
        """)

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        # Internet status
        self._wifi_icon = WiFiIcon(size=16, color=_TEXT50)
        lay.addWidget(self._wifi_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.net_label = QLabel(tr("net_status_label"))
        self.net_label.setFont(QFont(BODY_FONT, 11))
        self.net_label.setStyleSheet(f"color: {_TEXT60}; border: none; background: transparent;")
        lay.addWidget(self.net_label)

        lay.addStretch()

        # Ping
        self._ping_icon = ActivityIcon(size=16, color=_TEXT50)
        lay.addWidget(self._ping_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        ping_prefix = QLabel("Ping:")
        ping_prefix.setFont(QFont(BODY_FONT, 11))
        ping_prefix.setStyleSheet(f"color: {_TEXT60}; border: none; background: transparent;")
        lay.addWidget(ping_prefix)
        self.ping_value_label = QLabel("-- ms")
        self.ping_value_label.setFont(QFont(BODY_FONT, 11, QFont.Weight.Bold))
        self.ping_value_label.setStyleSheet(f"color: {_TEXT60}; border: none; background: transparent;")
        lay.addWidget(self.ping_value_label)

        return bar

    # ─────────────────────────────────────────── public API
    def after(self, ms: int, callback):
        QTimer.singleShot(ms, callback)

    def update_panel_safe(self, panel_name: str, state: str, text_key: str):
        color = _STATE_COLOR.get(state, _TEXT60)
        text = tr(text_key)
        ss = f"color: {color}; border: none; background: transparent;"

        def _apply():
            if panel_name == "pritunl":
                self._pritunl_status.setText(text)
                self._pritunl_status.setStyleSheet(ss)
            elif panel_name == "telemart":
                self._telemart_status.setText(text)
                self._telemart_status.setStyleSheet(ss)
            elif panel_name == "monitor":
                self._monitor_status.setText(text)
                self._monitor_status.setStyleSheet(ss)
                self.monitor_led.set_state(state)

        QTimer.singleShot(0, _apply)

    def update_net_status(self, is_connected: bool, ping_ms):
        if is_connected:
            self._wifi_icon.set_color(_GREEN)
            self.net_label.setText("Internet Connected")
            self.net_label.setStyleSheet(f"color: {_TEXT60}; border: none; background: transparent;")
            self.ping_value_label.setText(f"{ping_ms} ms")
            self.ping_value_label.setStyleSheet(f"color: {_TEXT}; border: none; background: transparent;")
            self._ping_icon.set_color(_TEXT)
        else:
            self._wifi_icon.set_color(_TEXT50)
            self.net_label.setText(tr("net_status_label"))
            self.net_label.setStyleSheet(f"color: {_TEXT60}; border: none; background: transparent;")
            self.ping_value_label.setText("-- ms")
            self.ping_value_label.setStyleSheet(f"color: {_TEXT60}; border: none; background: transparent;")
            self._ping_icon.set_color(_TEXT50)

    def show_update_ready(self, version_tag: str):
        self._status_dot.hide()
        btn = QPushButton(f"↑ {version_tag}")
        btn.setFixedHeight(20)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(52,199,89,0.15); color: #34C759;
                border: 1px solid rgba(52,199,89,0.3); border-radius: 10px;
                font-size: 11px; font-weight: bold; padding: 0 8px;
            }
            QPushButton:hover { background: rgba(52,199,89,0.25); }
        """)
        btn.clicked.connect(self.master_app.install_update_now)
        # Insert before spacer in header
        header = self.layout().itemAt(0).widget()
        header.layout().insertWidget(header.layout().count() - 2, btn)

    def toggle_pritunl_ui(self, state: str):
        if state == "working":
            self.pritunl_connect_btn.hide()
            self.disconnect_button.hide()
            self.pritunl_cancel_btn.show()
        else:
            self.pritunl_cancel_btn.hide()
            self.disconnect_button.hide()
            self.pritunl_connect_btn.show()

    def toggle_telemart_ui(self, state: str):
        if state == "working":
            self._telemart_mode = "cancel"
            self.start_telemart_button.setText(tr("btn_cancel"))
            self.start_telemart_button.setStyleSheet(_BTN_CANCEL)
        else:
            self._telemart_mode = "start"
            self.start_telemart_button.setText(tr("btn_start"))
            self.start_telemart_button.setStyleSheet(_BTN_PRIMARY)
        self.start_telemart_button.setEnabled(True)

    def _on_telemart_btn(self):
        if self._telemart_mode == "start":
            self.master_app.on_start_telemart_click()
        else:
            self.master_app.on_cancel_telemart_click()
