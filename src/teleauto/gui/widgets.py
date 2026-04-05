# src/teleauto/gui/widgets.py
from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QPainterPath,
    QLinearGradient, QBrush,
)

from .constants import LED_BLINK_INTERVAL, BODY_FONT


# ---------------------------------------------------------------------------
# LED indicator
# ---------------------------------------------------------------------------
class LEDWidget(QWidget):
    _COLORS = {
        "off":         QColor("#151515"),
        "success":     QColor("#34C759"),
        "error":       QColor("#FF453A"),
        "working":     QColor("#FFD60A"),
        "working_dim": QColor("#7A6400"),
        "waiting":     QColor("#FFD60A"),
        "connecting":  QColor("#FFD60A"),
    }

    def __init__(self, size: int = 14, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = self._COLORS["off"]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._blink)
        self._blink_on = True

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.width()
        pad = max(1, s // 7)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#111111"))
        p.drawEllipse(0, 0, s, s)
        p.setBrush(self._color)
        p.drawEllipse(pad, pad, s - 2 * pad, s - 2 * pad)

    def set_state(self, state: str):
        self._timer.stop()
        self._blink_on = True
        if state in ("working", "connecting", "waiting"):
            self._color = self._COLORS["working"]
            self.update()
            self._timer.start(LED_BLINK_INTERVAL)
        else:
            self._color = self._COLORS.get(state, self._COLORS["off"])
            self.update()

    def _blink(self):
        self._blink_on = not self._blink_on
        self._color = self._COLORS["working"] if self._blink_on else self._COLORS["working_dim"]
        self.update()


# ---------------------------------------------------------------------------
# Gradient icon — 32×32 rounded rect with gradient bg + Lucide-style icon
# ---------------------------------------------------------------------------
class GradientIcon(QWidget):
    """32×32 macOS-style app icon with gradient background and vector icon."""

    _GRADIENTS = {
        "lock":     (QColor("#34C759"), QColor("#28A745")),
        "monitor":  (QColor("#5E5CE6"), QColor("#4B49B8")),
        "activity": (QColor("#8E8E93"), QColor("#636366")),
    }

    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self._kind = kind

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Gradient background
        c1, c2 = self._GRADIENTS.get(self._kind, (QColor("#555"), QColor("#333")))
        grad = QLinearGradient(QPointF(0, 0), QPointF(0, 32))
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(QRectF(0, 0, 32, 32), 8, 8)

        # Subtle border
        pen_b = QPen(QColor(255, 255, 255, 51), 1)
        p.setPen(pen_b)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, 31, 31), 7.5, 7.5)

        # Vector icon — drawn in 24-unit space, scaled to 16px, centered in 32px
        p.translate(8.0, 8.0)
        sc = 16.0 / 24.0
        p.scale(sc, sc)

        icon_pen = QPen(QColor(255, 255, 255), 2.5 / sc)
        icon_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        icon_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(icon_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        if self._kind == "lock":
            self._draw_lock(p)
        elif self._kind == "monitor":
            self._draw_monitor(p)
        elif self._kind == "activity":
            self._draw_activity(p)

    @staticmethod
    def _draw_lock(p: QPainter):
        # Body
        p.drawRoundedRect(QRectF(3, 11, 18, 11), 2, 2)
        # Shackle arc (top semicircle)
        path = QPainterPath()
        path.moveTo(7, 11)
        path.lineTo(7, 7)
        path.arcTo(QRectF(7, 2, 10, 10), 180, 180)
        path.lineTo(17, 11)
        p.drawPath(path)

    @staticmethod
    def _draw_monitor(p: QPainter):
        p.drawRoundedRect(QRectF(2, 3, 20, 14), 2, 2)
        p.drawLine(QPointF(12, 17), QPointF(12, 20))
        p.drawLine(QPointF(8, 20), QPointF(16, 20))

    @staticmethod
    def _draw_activity(p: QPainter):
        path = QPainterPath()
        for i, (x, y) in enumerate([(22,12),(18,12),(15,20),(9,4),(6,12),(2,12)]):
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        p.drawPath(path)


# ---------------------------------------------------------------------------
# Draggable header mixin (for frameless window)
# ---------------------------------------------------------------------------
class DragWidget(QWidget):
    """QWidget that drags the top-level window when left-clicked and dragged."""

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_global = event.globalPosition().toPoint()
            self._drag_win_origin = self.window().pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, '_drag_start_global'):
            delta = event.globalPosition().toPoint() - self._drag_start_global
            self.window().move(self._drag_win_origin + delta)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if hasattr(self, '_drag_start_global'):
            del self._drag_start_global
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# Settings group frame
# ---------------------------------------------------------------------------
class SettingsGroup(QFrame):
    def __init__(self, title_key: str, parent=None):
        super().__init__(parent)
        self.setObjectName("settings_group")
        self.setStyleSheet("""
            QFrame#settings_group {
                background: #2C2C2E;
                border: 1px solid #3A3A3C;
                border-radius: 12px;
            }
            QFrame#settings_group QLabel { border: none; background: transparent; }
        """)
        self._title_key = title_key

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._title_lbl = QLabel(self)
        self._title_lbl.setFont(QFont(BODY_FONT, 11))
        self._title_lbl.setStyleSheet("color: #AAAAAA; background: transparent; border: none;")
        self._title_lbl.setContentsMargins(10, 6, 10, 2)
        lay.addWidget(self._title_lbl)

        self.content = QFrame(self)
        self.content.setObjectName("settings_group")
        cl = QVBoxLayout(self.content)
        cl.setContentsMargins(10, 4, 10, 10)
        cl.setSpacing(6)
        lay.addWidget(self.content)

        self.refresh_text()

    def refresh_text(self):
        from src.teleauto.localization import tr
        self._title_lbl.setText(tr(self._title_key))

    def body_layout(self) -> QVBoxLayout:
        return self.content.layout()


# ---------------------------------------------------------------------------
# Small footer icons (WiFi + Activity waveform)
# ---------------------------------------------------------------------------
class WiFiIcon(QWidget):
    """Draws a 3-arc WiFi symbol."""

    def __init__(self, size: int = 16, color: str = "#8E8E93", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor(color)

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        w, h = self.width(), self.height()
        cx = w / 2

        # Three arcs, bottom-up (largest to smallest)
        for i, (r, y_offset) in enumerate([(w * 0.48, h * 0.12),
                                            (w * 0.32, h * 0.30),
                                            (w * 0.16, h * 0.48)]):
            span = 150  # degrees
            start = 195
            rect = QRectF(cx - r, y_offset, r * 2, r * 2)
            p.drawArc(rect, int(start * 16), int(span * 16))

        # Dot at bottom
        dot_r = w * 0.06
        p.setBrush(self._color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - dot_r, h * 0.72, dot_r * 2, dot_r * 2))


class ActivityIcon(QWidget):
    """Draws an EKG/activity waveform icon."""

    def __init__(self, size: int = 16, color: str = "#8E8E93", parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = QColor(color)

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        w, h = self.width(), self.height()
        # Points: flat left → spike up → spike down → flat right
        pts = [
            (0.0,  0.5),
            (0.25, 0.5),
            (0.38, 0.1),
            (0.5,  0.9),
            (0.62, 0.5),
            (1.0,  0.5),
        ]
        path = QPainterPath()
        for i, (rx, ry) in enumerate(pts):
            pt = QPointF(rx * w, ry * h)
            if i == 0:
                path.moveTo(pt)
            else:
                path.lineTo(pt)
        p.drawPath(path)
