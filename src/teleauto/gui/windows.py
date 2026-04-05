# src/teleauto/gui/windows.py
import json
import os
import time
import logging

import pyotp
from PyQt6.QtWidgets import (
    QDialog, QWidget, QFrame, QLabel, QLineEdit, QPushButton,
    QCheckBox, QComboBox, QScrollArea, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFileDialog, QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from src.teleauto.credentials import (
    save_credentials, load_credentials, verify_pin,
    decrypt_credentials, clear_credentials,
)
from src.teleauto.localization import tr, set_language, get_language, LANG_CODES, LANG_NAMES
from .constants import BODY_FONT, MAIN_FONT_FAMILY
from .utils import apply_window_settings
from .widgets import SettingsGroup

logger = logging.getLogger(__name__)

PROFILES_FILE = "profiles.json"

BG = "#1C1C1E"
CARD_BG = "#2C2C2E"
BORDER = "#3A3A3C"
TEXT = "#FFFFFF"
SECONDARY = "#8E8E93"
ACCENT = "#0A84FF"
ERROR = "#FF453A"

_DIALOG_STYLE = f"""
    QDialog {{ background: {BG}; color: {TEXT}; }}
    QWidget {{ background: transparent; color: {TEXT}; font-family: "{BODY_FONT}"; }}
    QLineEdit {{
        background: {CARD_BG}; color: {TEXT};
        border: 1px solid {BORDER}; border-radius: 8px;
        padding: 6px 10px; font-size: 13px;
    }}
    QLineEdit:focus {{ border-color: {ACCENT}; }}
    QLineEdit:disabled {{ color: {SECONDARY}; }}
    QCheckBox {{ color: {TEXT}; spacing: 8px; }}
    QCheckBox::indicator {{
        width: 18px; height: 18px; border-radius: 4px;
        border: 1px solid {BORDER}; background: {CARD_BG};
    }}
    QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
    QComboBox {{
        background: {CARD_BG}; color: {TEXT};
        border: 1px solid {BORDER}; border-radius: 8px;
        padding: 6px 10px; font-size: 13px;
    }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background: {CARD_BG}; color: {TEXT};
        border: 1px solid {BORDER}; selection-background-color: {ACCENT};
    }}
    QPushButton {{
        background: {ACCENT}; color: {TEXT};
        border: none; border-radius: 8px;
        padding: 8px 16px; font-size: 13px; font-weight: bold;
    }}
    QPushButton:hover {{ background: #0070E0; }}
    QPushButton:disabled {{ background: #3A3A3C; color: {SECONDARY}; }}
    QScrollBar:vertical {{
        background: {CARD_BG}; width: 6px; border-radius: 3px;
    }}
    QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QLabel {{ color: {TEXT}; background: transparent; }}
"""

_BTN_DANGER = f"""
    QPushButton {{
        background: #AA0000; color: {TEXT};
        border: none; border-radius: 8px;
        padding: 8px 16px; font-size: 13px; font-weight: bold;
    }}
    QPushButton:hover {{ background: #880000; }}
"""
_BTN_SECONDARY = f"""
    QPushButton {{
        background: #3A3A3C; color: {SECONDARY};
        border: none; border-radius: 8px;
        padding: 8px 16px; font-size: 13px; font-weight: bold;
    }}
    QPushButton:hover {{ background: #4A4A4E; }}
"""


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont(BODY_FONT, 11))
    lbl.setStyleSheet(f"color: {SECONDARY}; background: transparent;")
    return lbl


def _input(placeholder: str = "", password: bool = False) -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setFixedHeight(38)
    if password:
        e.setEchoMode(QLineEdit.EchoMode.Password)
    return e


# ---------------------------------------------------------------------------
# PIN Dialog
# ---------------------------------------------------------------------------
class PinDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.pin: str | None = None
        self.setWindowTitle(tr("window_title_pin"))
        self.setFixedSize(340, 200)
        self.setStyleSheet(_DIALOG_STYLE)
        self._setup_ui()
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        QTimer.singleShot(50, lambda: apply_window_settings(self))

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {CARD_BG}; border: 1px solid {BORDER};
                border-radius: 12px;
            }}
        """)
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(16, 20, 16, 16)
        fl.setSpacing(10)

        msg = QLabel(tr("pin_enter_msg"))
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setFont(QFont(BODY_FONT, 13))
        fl.addWidget(msg)

        self._pin_entry = _input(password=True)
        self._pin_entry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pin_entry.setFont(QFont(BODY_FONT, 14, QFont.Weight.Bold))
        self._pin_entry.returnPressed.connect(self._check)
        fl.addWidget(self._pin_entry)

        btn = QPushButton(tr("unlock_btn"))
        btn.setFixedHeight(38)
        btn.clicked.connect(self._check)
        fl.addWidget(btn)

        lay.addWidget(frame)
        QTimer.singleShot(100, self._pin_entry.setFocus)

    def _check(self):
        entered = self._pin_entry.text()
        pin_hash = self.parent().ctrl.creds.get("pin_hash")
        if verify_pin(pin_hash, entered):
            self.pin = entered
            self.accept()
        else:
            QMessageBox.critical(self, "Error", tr("error_wrong_pin"))
            self._pin_entry.clear()
            self._pin_entry.setFocus()

    def closeEvent(self, event):
        self.reject()
        event.accept()


# ---------------------------------------------------------------------------
# Config Dialog (first-run setup)
# ---------------------------------------------------------------------------
class ConfigDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.pin_used: bool = False
        self.setWindowTitle(tr("window_title_setup"))
        self.resize(460, 700)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self._setup_ui()
        QTimer.singleShot(50, lambda: apply_window_settings(self))

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        inner = QWidget()
        inner.setStyleSheet(f"QWidget {{ background: {BG}; }}")
        fl = QVBoxLayout(inner)
        fl.setContentsMargins(16, 16, 16, 16)
        fl.setSpacing(12)

        # Language
        lang_grp = SettingsGroup("lang_label")
        lang_lay = lang_grp.body_layout()
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(list(LANG_CODES.keys()))
        current_lang_name = LANG_NAMES.get(get_language(), list(LANG_CODES.keys())[0])
        idx = self._lang_combo.findText(current_lang_name)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.currentTextChanged.connect(self._change_lang)
        lang_lay.addWidget(self._lang_combo)
        fl.addWidget(lang_grp)

        # Security
        sec_grp = SettingsGroup("group_security")
        sec_lay = sec_grp.body_layout()
        sec_lay.addWidget(_section_label(tr("pin_label")))
        self._pin_entry = _input(password=True)
        sec_lay.addWidget(self._pin_entry)
        sec_lay.addWidget(_section_label(tr("pin_repeat")))
        self._pin_repeat = _input(password=True)
        sec_lay.addWidget(self._pin_repeat)
        fl.addWidget(sec_grp)

        # VPN instruction
        vpn_grp = SettingsGroup("group_vpn")
        vpn_lay = vpn_grp.body_layout()
        info = QLabel(tr("vpn_instruction"))
        info.setWordWrap(True)
        info.setStyleSheet(f"color: #FFD700; background: transparent;")
        info.setFont(QFont(BODY_FONT, 11))
        vpn_lay.addWidget(info)
        fl.addWidget(vpn_grp)

        # Telemart
        tm_grp = SettingsGroup("group_tm")
        tm_lay = tm_grp.body_layout()
        self._tm_check = QCheckBox(tr("auto_start_tm"))
        self._tm_check.stateChanged.connect(self._toggle_tm)
        tm_lay.addWidget(self._tm_check)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self._path_entry = _input(tr("tm_path_label"))
        self._path_entry.setEnabled(False)
        path_row.addWidget(self._path_entry)
        browse = QPushButton("📂")
        browse.setFixedSize(38, 38)
        browse.setFont(QFont("Segoe UI Emoji", 14))
        browse.setEnabled(False)
        browse.clicked.connect(self._browse)
        self._browse_btn = browse
        path_row.addWidget(browse)
        tm_lay.addLayout(path_row)

        tm_lay.addWidget(_section_label(tr("login")))
        self._login_entry = _input()
        self._login_entry.setEnabled(False)
        tm_lay.addWidget(self._login_entry)

        tm_lay.addWidget(_section_label(tr("password")))
        self._pass_entry = _input(password=True)
        self._pass_entry.setEnabled(False)
        tm_lay.addWidget(self._pass_entry)
        fl.addWidget(tm_grp)

        fl.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

        # Save button
        save_row = QWidget()
        save_row.setStyleSheet(f"QWidget {{ background: {BG}; }}")
        save_rl = QVBoxLayout(save_row)
        save_rl.setContentsMargins(16, 8, 16, 16)
        self._save_btn = QPushButton(tr("save_btn"))
        self._save_btn.setFixedHeight(40)
        self._save_btn.clicked.connect(self._save)
        save_rl.addWidget(self._save_btn)
        root.addWidget(save_row)

    def _change_lang(self, choice):
        code = LANG_CODES.get(choice)
        if code:
            set_language(code)

    def _toggle_tm(self):
        enabled = self._tm_check.isChecked()
        for w in (self._path_entry, self._browse_btn, self._login_entry, self._pass_entry):
            w.setEnabled(enabled)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select executable", "", "Executables (*.exe);;All files (*.*)"
        )
        if path:
            self._path_entry.setText(path)

    def _save(self):
        pin = self._pin_entry.text()
        if pin != self._pin_repeat.text():
            QMessageBox.critical(self, "Error", tr("error_pin_mismatch"))
            return
        try:
            save_credentials(
                self._login_entry.text(), self._pass_entry.text(),
                pin or None, {},
                self._tm_check.isChecked(),
                language=get_language(),
                telemart_path=self._path_entry.text(),
                manual_offset=0,
            )
            self.pin_used = bool(pin)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def closeEvent(self, event):
        self.reject()
        event.accept()


# ---------------------------------------------------------------------------
# Settings Dialog
# ---------------------------------------------------------------------------
class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("window_title_settings"))
        self.resize(500, 780)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._selected_lang = get_language()
        self._initial_lang = get_language()
        self._unlocked = False
        self._sv_dict: dict[str, QLineEdit] = {}
        self._totp_labels: dict[str, QLabel] = {}
        self._totp_timer = QTimer(self)
        self._totp_timer.timeout.connect(self._update_totp)

        self._discovered_profiles: list[str] = []
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                    self._discovered_profiles = json.load(f)
            except Exception:
                pass

        self._setup_ui()
        self._load_public_data()
        QTimer.singleShot(50, lambda: apply_window_settings(self))
        self._totp_timer.start(1000)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # PIN unlock bar
        pin_bar = QWidget()
        pin_bar.setStyleSheet(f"QWidget {{ background: {BG}; }}")
        pb_lay = QHBoxLayout(pin_bar)
        pb_lay.setContentsMargins(16, 12, 16, 8)
        pb_lay.setSpacing(8)

        self._pin_lbl = QLabel(tr("label_pin_short"))
        self._pin_lbl.setFont(QFont(BODY_FONT, 12))
        pb_lay.addWidget(self._pin_lbl)

        self._pin_ent = _input(password=True)
        self._pin_ent.setFixedWidth(140)
        self._pin_ent.returnPressed.connect(self._unlock)
        pb_lay.addWidget(self._pin_ent)

        self._unlock_btn = QPushButton(tr("unlock_btn"))
        self._unlock_btn.setFixedHeight(36)
        self._unlock_btn.setFixedWidth(90)
        self._unlock_btn.clicked.connect(self._unlock)
        pb_lay.addWidget(self._unlock_btn)
        pb_lay.addStretch()

        self._pin_bar = pin_bar
        root.addWidget(pin_bar)

        # Scroll content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        inner = QWidget()
        inner.setStyleSheet(f"QWidget {{ background: {BG}; }}")
        self._fl = QVBoxLayout(inner)
        self._fl.setContentsMargins(16, 8, 16, 8)
        self._fl.setSpacing(12)

        # Language
        lang_grp = SettingsGroup("lang_label")
        lang_lay = lang_grp.body_layout()
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(list(LANG_CODES.keys()))
        cur = LANG_NAMES.get(get_language(), list(LANG_CODES.keys())[0])
        idx = self._lang_combo.findText(cur)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.setEnabled(False)
        self._lang_combo.currentTextChanged.connect(self._change_lang)
        lang_lay.addWidget(self._lang_combo)
        self._fl.addWidget(lang_grp)

        # Time / offset
        time_grp = SettingsGroup("group_time")
        time_lay = time_grp.body_layout()
        offset_row = QHBoxLayout()
        self._offset_lbl = QLabel(tr("offset_label"))
        self._offset_lbl.setFont(QFont(BODY_FONT, 12))
        offset_row.addWidget(self._offset_lbl)
        self._offset_ent = QLineEdit("0")
        self._offset_ent.setFixedWidth(80)
        self._offset_ent.setFixedHeight(34)
        self._offset_ent.setEnabled(False)
        offset_row.addWidget(self._offset_ent)
        hint = QLabel(tr("offset_hint"))
        hint.setFont(QFont(BODY_FONT, 10))
        hint.setStyleSheet(f"color: grey; background: transparent;")
        offset_row.addWidget(hint)
        offset_row.addStretch()
        time_lay.addLayout(offset_row)
        self._fl.addWidget(time_grp)

        # VPN profiles
        vpn_grp = SettingsGroup("group_vpn")
        vpn_lay = vpn_grp.body_layout()
        if not self._discovered_profiles:
            no_prof = QLabel(tr("error_no_profiles"))
            no_prof.setStyleSheet("color: #FFD700; background: transparent;")
            vpn_lay.addWidget(no_prof)
        else:
            grid = QGridLayout()
            grid.setSpacing(6)
            for idx, p_name in enumerate(self._discovered_profiles):
                name_lbl = QLabel(p_name)
                name_lbl.setFont(QFont(BODY_FONT, 12))
                grid.addWidget(name_lbl, idx, 0)

                ent = _input(password=True)
                ent.setEnabled(False)
                self._sv_dict[p_name] = ent
                grid.addWidget(ent, idx, 1)

                code_lbl = QLabel("--- ---")
                code_lbl.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
                code_lbl.setStyleSheet("color: #00FF00; background: transparent;")
                code_lbl.setFixedWidth(80)
                self._totp_labels[p_name] = code_lbl
                grid.addWidget(code_lbl, idx, 2)
            vpn_lay.addLayout(grid)
        self._fl.addWidget(vpn_grp)

        # Telemart
        tm_grp = SettingsGroup("group_tm")
        tm_lay = tm_grp.body_layout()
        self._cb = QCheckBox(tr("auto_start_tm"))
        self._cb.setEnabled(False)
        self._cb.stateChanged.connect(self._toggle_tm)
        tm_lay.addWidget(self._cb)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self._path_ent = _input()
        self._path_ent.setEnabled(False)
        path_row.addWidget(self._path_ent)
        self._browse_btn = QPushButton("📂")
        self._browse_btn.setFixedSize(38, 38)
        self._browse_btn.setFont(QFont("Segoe UI Emoji", 14))
        self._browse_btn.setEnabled(False)
        self._browse_btn.clicked.connect(self._browse)
        path_row.addWidget(self._browse_btn)
        tm_lay.addLayout(path_row)

        tm_lay.addWidget(_section_label(tr("login")))
        self._login_ent = _input()
        self._login_ent.setEnabled(False)
        tm_lay.addWidget(self._login_ent)

        tm_lay.addWidget(_section_label(tr("password")))
        self._pass_ent = _input(password=True)
        self._pass_ent.setEnabled(False)
        tm_lay.addWidget(self._pass_ent)
        self._fl.addWidget(tm_grp)

        self._fl.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, stretch=1)

        # Action buttons
        btn_bar = QWidget()
        btn_bar.setStyleSheet(f"QWidget {{ background: {BG}; }}")
        bb_lay = QHBoxLayout(btn_bar)
        bb_lay.setContentsMargins(16, 8, 16, 16)
        bb_lay.setSpacing(8)

        self._save_btn = QPushButton(tr("save_changes_btn"))
        self._save_btn.setFixedHeight(40)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save)
        bb_lay.addWidget(self._save_btn)

        self._del_btn = QPushButton(tr("delete_btn"))
        self._del_btn.setFixedHeight(40)
        self._del_btn.setStyleSheet(_BTN_DANGER)
        self._del_btn.clicked.connect(self._delete)
        bb_lay.addWidget(self._del_btn)

        root.addWidget(btn_bar)

        # Hide PIN bar if no PIN hash
        if not self.parent().ctrl.creds.get("pin_hash"):
            self._pin_bar.hide()
            self._unlock(no_pin=True)

    def _load_public_data(self):
        creds = self.parent().ctrl.creds
        if creds.get("start_telemart"):
            self._cb.setChecked(True)

    def _change_lang(self, choice):
        code = LANG_CODES.get(choice)
        if code:
            self._selected_lang = code
            set_language(code)

    def _toggle_tm(self):
        if not self._unlocked:
            return
        enabled = self._cb.isChecked()
        for w in (self._path_ent, self._browse_btn, self._login_ent, self._pass_ent):
            w.setEnabled(enabled)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select executable", "", "Executables (*.exe);;All files (*.*)"
        )
        if path:
            self._path_ent.setText(path)

    def _unlock(self, no_pin: bool = False):
        try:
            pin_val = None if no_pin else self._pin_ent.text().strip()
            d = decrypt_credentials(self.parent().ctrl.creds, pin_val)

            self._login_ent.setText(d[0])
            self._pass_ent.setText(d[1])

            saved_secrets = d[2]
            for p_name, ent in self._sv_dict.items():
                if p_name in saved_secrets:
                    ent.setText(saved_secrets[p_name])

            if d[3]:
                self._cb.setChecked(True)
            if len(d) > 5 and d[5]:
                self._path_ent.setText(d[5])
            if len(d) > 6:
                self._offset_ent.setText(str(d[6]))

            self._unlocked = True
            for ent in self._sv_dict.values():
                ent.setEnabled(True)
            for w in (self._cb, self._lang_combo, self._offset_ent):
                w.setEnabled(True)
            self._save_btn.setEnabled(True)
            self._toggle_tm()

            if not no_pin:
                self._pin_bar.hide()
            del d
        except Exception:
            QMessageBox.critical(self, "Error", tr("error_wrong_pin"))

    def _update_totp(self):
        if not self.isVisible():
            return
        try:
            offset = int(self._offset_ent.text())
        except ValueError:
            offset = 0
        ts = time.time() + offset
        for p_name, lbl in self._totp_labels.items():
            secret = self._sv_dict[p_name].text().replace(" ", "")
            if secret:
                try:
                    code = pyotp.TOTP(secret).at(ts)
                    lbl.setText(f"{code[:3]} {code[3:]}")
                    lbl.setStyleSheet("color: #00FF00; background: transparent;")
                except Exception:
                    lbl.setText("Invalid")
                    lbl.setStyleSheet("color: #FF0000; background: transparent;")
            else:
                lbl.setText("--- ---")
                lbl.setStyleSheet("color: grey; background: transparent;")

    def _save(self):
        try:
            pin = self._pin_ent.text().strip() if self.parent().ctrl.creds.get("pin_hash") else None
            secrets = {
                p: ent.text().strip()
                for p, ent in self._sv_dict.items()
                if ent.text().strip()
            }
            try:
                offset = int(self._offset_ent.text())
            except ValueError:
                offset = 0

            save_credentials(
                self._login_ent.text(), self._pass_ent.text(),
                pin, secrets,
                self._cb.isChecked(),
                language=self._selected_lang,
                telemart_path=self._path_ent.text(),
                manual_offset=offset,
            )
            self.parent().ctrl.creds = load_credentials()
            self.parent().ctrl.user_pin = pin
            self.parent().update_main_window_buttons()

            if self._selected_lang != self._initial_lang:
                QMessageBox.information(self, tr("restart_title"), tr("restart_msg"))
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _delete(self):
        reply = QMessageBox.question(self, "Reset", tr("delete_confirm"))
        if reply == QMessageBox.StandardButton.Yes:
            clear_credentials()
            self.parent().on_closing()

    def closeEvent(self, event):
        self._totp_timer.stop()
        event.accept()


# ---------------------------------------------------------------------------
# Update Dialog
# ---------------------------------------------------------------------------
class UpdateDialog(QDialog):
    def __init__(self, parent, tag: str, on_now, on_later):
        super().__init__(parent)
        self._on_later_cb = on_later
        self.setWindowTitle(tr("update_dialog_title"))
        self.setFixedSize(420, 190)
        self.setStyleSheet(_DIALOG_STYLE)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        self._msg = QLabel(tr("update_dialog_msg", tag=tag))
        self._msg.setWordWrap(True)
        self._msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg.setFont(QFont(BODY_FONT, 12))
        lay.addWidget(self._msg)

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setFont(QFont(BODY_FONT, 11))
        self._status.setStyleSheet(f"color: {SECONDARY}; background: transparent;")
        lay.addWidget(self._status)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._now_btn = QPushButton(tr("update_now_btn"))
        self._now_btn.setFixedHeight(38)
        self._now_btn.clicked.connect(lambda: on_now(self))
        btn_row.addWidget(self._now_btn)

        self._later_btn = QPushButton(tr("update_later_btn"))
        self._later_btn.setFixedHeight(38)
        self._later_btn.setStyleSheet(_BTN_SECONDARY)
        self._later_btn.clicked.connect(self._on_later)
        btn_row.addWidget(self._later_btn)

        lay.addLayout(btn_row)
        QTimer.singleShot(50, lambda: apply_window_settings(self))

    def _on_later(self):
        self.close()
        if self._on_later_cb:
            self._on_later_cb()

    def set_status(self, text: str, color: str = "#888888"):
        self._status.setText(text)
        self._status.setStyleSheet(f"color: {color}; background: transparent;")

    def disable_buttons(self):
        self._now_btn.setEnabled(False)
        self._later_btn.setEnabled(False)

    def closeEvent(self, event):
        self._on_later()
        event.accept()
