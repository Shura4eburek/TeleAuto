# src/teleauto/gui/app.py
import os
import sys
import logging

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QApplication, QMessageBox, QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction

from src.teleauto.localization import tr, set_language
from src.teleauto.controller import AppController
from src.teleauto.gui.windows import ConfigDialog, PinDialog, SettingsDialog, UpdateDialog
from src.teleauto.gui.main_view import MainWindow
from src.teleauto.gui.utils import apply_window_settings, apply_dark_title_bar
from src.teleauto.gui.constants import VERSION

logger = logging.getLogger(__name__)


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ctrl = AppController(ui=self)
        self.main_frame: MainWindow | None = None
        self._tray_icon: QSystemTrayIcon | None = None

        if self.ctrl.creds:
            set_language(self.ctrl.creds.get("language", "ru"))

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("TeleAuto")
        self.setMinimumSize(400, 300)
        self.resize(550, 280)
        self.setWindowIcon(self._make_icon())

        central = QWidget()
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(central)

        # Start background tasks (update check, network monitor)
        self.ctrl.start_background_tasks()

        # Defer startup flow to after event loop starts
        QTimer.singleShot(0, self._startup_flow)

    # ------------------------------------------------------------------ startup
    def _startup_flow(self):
        if not self.ctrl.creds:
            dlg = ConfigDialog(self)
            if dlg.exec() != dlg.DialogCode.Accepted:
                self.on_closing()
                return
            self.ctrl.load_creds()
            if dlg.pin_used:
                self._show_pin_dialog()
            else:
                self._do_show_main()
        else:
            if self.ctrl.creds.get("pin_hash"):
                self._show_pin_dialog()
            else:
                self._do_show_main()

    def _show_pin_dialog(self):
        dlg = PinDialog(self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            self.on_closing()
            return
        try:
            self.ctrl.decrypt_and_set_language(dlg.pin)
            self._do_show_main()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.on_closing()

    def _do_show_main(self):
        self.show_main_window()

    # ------------------------------------------------------------------ main window
    def show_main_window(self):
        self.main_frame = MainWindow(self)
        self.setCentralWidget(self.main_frame)
        self.resize(650, 580)
        self.setMinimumSize(500, 480)
        self.setResizable(True)
        self.show()

        self.main_frame.expand_log()
        self._update_buttons_impl()
        logger.info(tr("log_system_start"))
        self.on_disconnect_click(startup=True)

        if self.ctrl.update_ready and self.ctrl.new_version_tag:
            QTimer.singleShot(400, lambda: self._show_update_dialog(self.ctrl.new_version_tag))

        self._setup_tray()
        self._add_dropshadow()

    def setResizable(self, resizable: bool):
        if resizable:
            self.setMinimumSize(500, 480)
            self.setMaximumSize(16777215, 16777215)
        else:
            fixed = self.size()
            self.setFixedSize(fixed)

    def on_close_btn(self):
        if self._tray_icon and self._tray_icon.isVisible():
            self.hide()
        else:
            self.on_closing()

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _add_dropshadow(self):
        """Windows DWM drop-shadow for frameless window."""
        try:
            import ctypes
            hwnd = int(self.winId())
            DWMWA_NCRENDERING_POLICY = 2
            DWMNCRP_ENABLED = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_NCRENDERING_POLICY,
                ctypes.byref(ctypes.c_int(DWMNCRP_ENABLED)), ctypes.sizeof(ctypes.c_int)
            )
            margins = (ctypes.c_int * 4)(1, 1, 1, 1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, margins)
        except Exception as e:
            logger.debug("DWM shadow failed: %s", e)

    # ------------------------------------------------------------------ compat: after()
    def after(self, ms: int, callback):
        """Tkinter-compatible after() → QTimer.singleShot for controller compat."""
        QTimer.singleShot(ms, callback)

    # ------------------------------------------------------------------ buttons
    def update_main_window_buttons(self, is_busy: bool = False):
        """Thread-safe: always schedule on main thread."""
        QTimer.singleShot(0, lambda: self._update_buttons_impl(is_busy))

    def _update_buttons_impl(self, is_busy: bool = False):
        if not self.main_frame:
            return
        if is_busy:
            pass  # caller already set toggle_pritunl_ui('working')
        elif self.ctrl.vpn_is_connected:
            self.main_frame.pritunl_connect_btn.hide()
            self.main_frame.pritunl_cancel_btn.hide()
            self.main_frame.disconnect_button.show()
        else:
            self.main_frame.toggle_pritunl_ui("normal")

        if not is_busy:
            self.main_frame.toggle_telemart_ui("normal")

        self.main_frame.start_telemart_button.setEnabled(not is_busy)

    # ------------------------------------------------------------------ VPN
    def on_pritunl_connect_click(self):
        if not self.main_frame.is_expanded:
            self.main_frame.expand_log()
        self.main_frame.toggle_pritunl_ui("working")
        self.update_main_window_buttons(is_busy=True)
        self.ctrl.start_autopilot()

    def on_cancel_pritunl_click(self):
        self.ctrl.stop_autopilot()
        logger.info(tr("log_op_cancelled"))

    def on_disconnect_click(self, startup: bool = False):
        if not startup:
            logger.info(tr("log_ctrl_stopping"))
        self.ctrl.stop_autopilot()
        if not startup and self.main_frame:
            self.main_frame.disconnect_button.setEnabled(False)

    # ------------------------------------------------------------------ Telemart
    def on_start_telemart_click(self):
        if not self.main_frame.is_expanded:
            self.main_frame.expand_log()
        self.main_frame.toggle_telemart_ui("working")
        self.ctrl.start_telemart()

    def on_cancel_telemart_click(self):
        self.ctrl.stop_telemart()
        logger.info(tr("log_op_cancelled"))

    # ------------------------------------------------------------------ status
    def set_ui_status(self, target: str, state: str, text_key: str):
        if self.main_frame:
            self.main_frame.update_panel_safe(target, state, text_key)

    # ------------------------------------------------------------------ settings
    def open_settings_window(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    # ------------------------------------------------------------------ update
    def on_update_found(self, tag: str):
        """Called from controller via self.ui.after(0, ...)."""
        if self.main_frame:
            self._show_update_dialog(tag)

    def _show_update_dialog(self, tag: str):
        UpdateDialog(self, tag, on_now=self._do_update_now, on_later=self._do_update_later)

    def _do_update_now(self, dialog: UpdateDialog):
        dialog.disable_buttons()
        dialog.set_status(tr("update_downloading"))

        def _worker():
            success = self.ctrl.do_download_and_apply()
            if success:
                QTimer.singleShot(0, lambda: dialog.set_status(tr("update_applying"), color="#00CC44"))
                QTimer.singleShot(800, self.on_closing)
            else:
                QTimer.singleShot(0, lambda: dialog.set_status(tr("update_failed"), color="#FF4444"))
                QTimer.singleShot(0, lambda: dialog._later_btn.setEnabled(True))

        import threading
        threading.Thread(target=_worker, daemon=True).start()

    def _do_update_later(self):
        if self.main_frame and self.ctrl.new_version_tag:
            self.main_frame.show_update_ready(self.ctrl.new_version_tag)

    def install_update_now(self):
        if self.ctrl.new_version_tag:
            self._show_update_dialog(self.ctrl.new_version_tag)

    # ------------------------------------------------------------------ tray
    def _setup_tray(self):
        try:
            icon = self._make_icon()
            self._tray_icon = QSystemTrayIcon(icon, self)

            menu = QMenu()
            show_act = QAction(tr("tray_show"), self)
            show_act.triggered.connect(self._show_from_tray)
            quit_act = QAction(tr("tray_quit"), self)
            quit_act.triggered.connect(self.on_closing)
            menu.addAction(show_act)
            menu.addSeparator()
            menu.addAction(quit_act)
            menu.setStyleSheet("""
                QMenu {
                    background: #2C2C2E; color: #FFFFFF;
                    border: 1px solid #3A3A3C; border-radius: 8px; padding: 4px;
                }
                QMenu::item { padding: 6px 16px; border-radius: 4px; }
                QMenu::item:selected { background: #0A84FF; }
                QMenu::separator { background: #3A3A3C; height: 1px; margin: 4px 8px; }
            """)

            self._tray_icon.setContextMenu(menu)
            self._tray_icon.setToolTip(f"TeleAuto {VERSION}")
            self._tray_icon.activated.connect(self._on_tray_activated)
            self._tray_icon.show()
        except Exception as e:
            logger.warning("Tray setup failed: %s", e)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _make_icon(self) -> QIcon:
        path = self._get_icon_path()
        if path:
            return QIcon(path)
        # Fallback: blue circle
        px = QPixmap(64, 64)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(30, 144, 255))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(4, 4, 56, 56)
        p.end()
        return QIcon(px)

    @staticmethod
    def _get_icon_path() -> str | None:
        try:
            path = os.path.join(sys._MEIPASS, "icon.ico")
            return path if os.path.exists(path) else None
        except AttributeError:
            pass
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.abspath(os.path.join(here, "..", "..", ".."))
        path = os.path.join(root, "icon.ico")
        return path if os.path.exists(path) else None

    # ------------------------------------------------------------------ close
    def closeEvent(self, event):
        if self._tray_icon and self._tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            self.on_closing()
            event.accept()

    def on_closing(self):
        if self._tray_icon:
            try:
                self._tray_icon.hide()
            except Exception:
                pass
        self.ctrl.shutdown()
        QApplication.quit()
