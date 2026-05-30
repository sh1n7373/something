import sys
import re
import json
import asyncio
import threading
import sqlite3
import urllib.request
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

APP_VERSION = "3.0"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/sh1n7373/something/main/Lagos.py"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/sh1n7373/something/main/version.txt"

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QDialog, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QPlainTextEdit,
        QListWidget, QListWidgetItem, QScrollArea, QFrame, QStackedWidget,
        QAbstractItemView, QMessageBox, QComboBox, QProgressBar, QSizePolicy,
        QGraphicsEffect
    )
    from PyQt5.QtCore import (
        Qt, QTimer, QTime, QPropertyAnimation, QParallelAnimationGroup,
        QEasingCurve, pyqtSignal, pyqtProperty, QRect, QPointF, QObject, QSize
    )
    from PyQt5.QtGui import (
        QPainter, QColor, QLinearGradient, QPen, QFont, QIcon, QPixmap
    )
except ImportError as e:
    print(f"PyQt5 не установлен: {e}", file=sys.stderr)
    print("Установите: pip3 install PyQt5", file=sys.stderr)
    sys.exit(1)

try:
    from telethon import TelegramClient
    from telethon.errors import (
        FloodWaitError, UserPrivacyRestrictedError,
        UsernameNotOccupiedError, PeerFloodError,
        SessionPasswordNeededError
    )
    from telethon.tl.types import User
except ImportError as e:
    print(f"Telethon не установлен: {e}", file=sys.stderr)
    print("Установите: pip3 install telethon", file=sys.stderr)
    sys.exit(1)

try:
    import socks
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False

def _get_app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent

APP_DIR = _get_app_dir()
DATA_FILE = APP_DIR / "data.json"
SESSION_DIR = APP_DIR / "sessions"
SESSION_DIR.mkdir(exist_ok=True)


def _set_session_wal(phone, chat_mode=False):
    base = phone.replace("+", "")
    path = SESSION_DIR / (base + ("_chat" if chat_mode else "") + ".session")
    if chat_mode and not path.exists():
        src = SESSION_DIR / f"{base}.session"
        if src.exists():
            import shutil
            shutil.copy2(str(src), str(path))
    if path.exists():
        try:
            con = sqlite3.connect(str(path), timeout=30)
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA busy_timeout=30000")
            con.close()
        except Exception:
            pass

STYLE = """
QMainWindow, QDialog {
    background: #1a1d26;
}
QWidget {
    background: #1a1d26;
    color: #dde3f0;
    font-family: 'Helvetica Neue', 'Segoe UI', sans-serif;
    font-size: 13px;
}
QPushButton {
    background: #1e2230;
    color: #dde3f0;
    border: 1px solid #323a52;
    border-radius: 10px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background: #252c42;
    border-color: #4a6fa5;
    color: #ffffff;
}
QPushButton:pressed {
    background: #2d3650;
    color: #fff;
}
QPushButton#primary {
    background: #1e2230;
    border: 1px solid #323a52;
    color: #dde3f0;
    font-weight: 500;
}
QPushButton#primary:hover {
    background: #252c42;
    border-color: #4a6fa5;
    color: #ffffff;
}
QPushButton#danger {
    background: #1e2230;
    border: 1px solid #323a52;
    color: #dde3f0;
}
QPushButton#danger:hover {
    background: #252c42;
    border-color: #4a6fa5;
    color: #ffffff;
}
QLabel {
    background: transparent;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background: #141720;
    border: 1px solid #2c3348;
    border-radius: 8px;
    padding: 8px 12px;
    color: #dde3f0;
    selection-background-color: #4a6fa5;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #4a6fa5;
    background: #161a24;
}
QListWidget {
    background: #141720;
    border: 1px solid #2c3348;
    border-radius: 8px;
    outline: none;
    padding: 4px;
}
QListWidget::item {
    border-radius: 6px;
    padding: 7px 10px;
    margin: 1px 2px;
    color: #a8b8d8;
}
QListWidget::item:selected {
    background: #2a3a5a;
    color: #e8eef8;
}
QListWidget::item:hover {
    background: #202535;
}
QScrollBar:vertical {
    background: #141720;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #2c3a5a;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #4a6fa5;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QLabel#header {
    font-size: 22px;
    font-weight: 700;
    color: #e8eef8;
    letter-spacing: -0.5px;
}
QLabel#subheader {
    font-size: 12px;
    color: #4e5a78;
}
QLabel#section {
    font-size: 10px;
    font-weight: 700;
    color: #6b82c0;
    letter-spacing: 1.8px;
}
QFrame#card {
    background: #1e2230;
    border: 1px solid #272f42;
    border-radius: 12px;
}
QFrame#separator {
    background: #252c3e;
    max-height: 1px;
    min-height: 1px;
}
QProgressBar {
    background: #1e2230;
    border: none;
    border-radius: 3px;
    height: 5px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4a6fa5, stop:1 #6b9ed4);
    border-radius: 3px;
}
QComboBox {
    background: #141720;
    border: 1px solid #2c3348;
    border-radius: 8px;
    padding: 8px 12px;
    color: #dde3f0;
    min-height: 34px;
}
QComboBox:focus {
    border-color: #4a6fa5;
}
QComboBox:on {
    border-color: #4a6fa5;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #2c3348;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    background: #1a1f30;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #6b82c0;
}
QComboBox QAbstractItemView {
    background: #141720;
    border: 1px solid #4a6fa5;
    border-radius: 6px;
    selection-background-color: #2a3a5a;
    selection-color: #e8eef8;
    color: #dde3f0;
    outline: none;
    padding: 4px;
}
QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    min-height: 30px;
    border-radius: 4px;
    margin: 1px 3px;
    background: transparent;
    color: #a8b8d8;
}
QComboBox QAbstractItemView::item:hover {
    background: #1e2538;
    color: #dde3f0;
}
QComboBox QAbstractItemView::item:selected {
    background: #2a3a5a;
    color: #e8eef8;
}
"""

ARROW_BTN_STYLE = """
QPushButton {
    background: #1e2538;
    border: none;
    border-left: 1px solid #2c3348;
    color: #6b82c0;
    font-size: 9px;
    padding: 0px;
    min-width: 26px;
    max-width: 26px;
}
QPushButton:hover {
    background: #253050;
    color: #a0b8e0;
}
QPushButton:pressed {
    background: #3d5080;
}
"""


def load_data():
    if DATA_FILE.exists():
        try:
            d = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            for key in ("proxies", "chat_log", "account_proxies", "account_recipients"):
                if key not in d:
                    d[key] = {} if key in ("chat_log", "account_proxies", "account_recipients") else []
            if "tag_interval_min" not in d:
                d["tag_interval_min"] = 0
            if "recipient_dbs" not in d:
                d["recipient_dbs"] = {}
            if "app_proxy" not in d:
                d["app_proxy"] = None
            return d
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "accounts": [],
        "recipients": [],
        "pastes": [],
        "pastes_per_recipient": 1,
        "proxies": [],
        "chat_log": {},
        "account_proxies": {},
        "account_recipients": {},
        "recipient_dbs": {},
        "tag_interval_min": 0,
        "app_proxy": None,
    }


def recipient_tag(r):
    if isinstance(r, dict):
        return r.get("tag", "")
    return r


def recipient_token(r):
    if isinstance(r, dict):
        return r.get("token", "")
    return ""


def apply_token(text, token):
    return re.sub(r'\$token', token, text, flags=re.IGNORECASE)


def _parse_recipient_line(line):
    line = line.strip()
    m = re.match(r'^(@?\S+)\s*[-]\s*(\$\S+)$', line)
    if m:
        tag = m.group(1)
        token = m.group(2)
    else:
        tag = line
        token = ""
    if not tag.startswith("@"):
        tag = "@" + tag
    return tag, token


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_client(acc, proxy=None, chat_mode=False):
    phone = acc["phone"].replace("+", "")
    sess = str(SESSION_DIR / (phone + ("_chat" if chat_mode else "")))
    kwargs = {
        "connection_retries": 5,
        "retry_delay": 2,
    }
    if proxy and SOCKS_AVAILABLE:
        ptype = proxy.get("type", "socks5").lower()
        pt = socks.SOCKS5
        if ptype == "socks4":
            pt = socks.SOCKS4
        elif ptype == "http":
            pt = socks.HTTP
        kwargs["proxy"] = (
            pt,
            proxy["host"],
            int(proxy["port"]),
            True,
            proxy.get("user") or None,
            proxy.get("password") or None,
        )
    return TelegramClient(sess, acc["api_id"], acc["api_hash"], **kwargs)


class StyledSpinBox(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min = 0
        self._max = 99
        self._val = 0
        self._suffix = ""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._edit = QLineEdit()
        self._edit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._edit.editingFinished.connect(self._on_edit)
        layout.addWidget(self._edit)
        btn_col = QVBoxLayout()
        btn_col.setContentsMargins(0, 0, 0, 0)
        btn_col.setSpacing(0)
        self._up = QPushButton("^")
        self._up.setFixedSize(28, 24)
        self._up.setStyleSheet(ARROW_BTN_STYLE + "QPushButton { border-top-right-radius: 8px; border-bottom: 1px solid #2c3348; }")
        self._up.clicked.connect(self._inc)
        self._dn = QPushButton("v")
        self._dn.setFixedSize(28, 24)
        self._dn.setStyleSheet(ARROW_BTN_STYLE + "QPushButton { border-bottom-right-radius: 8px; }")
        self._dn.clicked.connect(self._dec)
        btn_col.addWidget(self._up)
        btn_col.addWidget(self._dn)
        layout.addLayout(btn_col)
        self.setFixedHeight(36)
        self._edit.setFixedHeight(36)
        self.setStyleSheet("""
            QWidget { background: transparent; }
            QLineEdit {
                background:
                border: 1px solid
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                padding: 8px 12px;
                color:
            }
            QLineEdit:focus { border-color:
        """)

    def setRange(self, mn, mx):
        self._min = mn
        self._max = mx

    def setValue(self, v):
        self._val = max(self._min, min(self._max, v))
        self._edit.setText(f"{self._val}{self._suffix}")

    def setSuffix(self, s):
        self._suffix = s
        self.setValue(self._val)

    def value(self):
        return self._val

    def _inc(self):
        self.setValue(self._val + 1)
        self.valueChanged.emit(self._val)

    def _dec(self):
        self.setValue(self._val - 1)
        self.valueChanged.emit(self._val)

    def _on_edit(self):
        text = self._edit.text().replace(self._suffix, "").strip()
        try:
            self.setValue(int(text))
        except ValueError:
            self.setValue(self._val)
        self._edit.setText(f"{self._val}{self._suffix}")
        self.valueChanged.emit(self._val)


class StyledTimeEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._edit = QLineEdit()
        self._edit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._edit.editingFinished.connect(self._on_edit)
        layout.addWidget(self._edit)
        btn_col = QVBoxLayout()
        btn_col.setContentsMargins(0, 0, 0, 0)
        btn_col.setSpacing(0)
        self._up = QPushButton("^")
        self._up.setFixedSize(28, 24)
        self._up.setStyleSheet(ARROW_BTN_STYLE + "QPushButton { border-top-right-radius: 8px; border-bottom: 1px solid #2c3348; }")
        self._up.clicked.connect(self._inc)
        self._dn = QPushButton("v")
        self._dn.setFixedSize(28, 24)
        self._dn.setStyleSheet(ARROW_BTN_STYLE + "QPushButton { border-bottom-right-radius: 8px; }")
        self._dn.clicked.connect(self._dec)
        btn_col.addWidget(self._up)
        btn_col.addWidget(self._dn)
        layout.addLayout(btn_col)
        self.setFixedHeight(36)
        self._edit.setFixedHeight(36)
        self.setStyleSheet("""
            QWidget { background: transparent; }
            QLineEdit {
                background:
                border: 1px solid
                border-top-right-radius: 0px;
                border-bottom-right-radius: 0px;
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
                padding: 8px 12px;
                color:
            }
            QLineEdit:focus { border-color:
        """)
        self._h = 0
        self._m = 0

    def setTime(self, t):
        self._h = t.hour()
        self._m = t.minute()
        self._refresh()

    def time(self):
        return QTime(self._h, self._m)

    def _refresh(self):
        self._edit.setText(f"{self._h:02d}:{self._m:02d}")

    def _inc(self):
        self._m += 1
        if self._m >= 60:
            self._m = 0
            self._h = (self._h + 1) % 24
        self._refresh()

    def _dec(self):
        self._m -= 1
        if self._m < 0:
            self._m = 59
            self._h = (self._h - 1) % 24
        self._refresh()

    def _on_edit(self):
        text = self._edit.text().strip()
        parts = text.split(":")
        try:
            h = int(parts[0]) % 24
            m = int(parts[1]) % 60 if len(parts) > 1 else 0
            self._h = h
            self._m = m
        except (ValueError, IndexError):
            self._h = 0
            self._m = 0
        self._refresh()


class SlideEffect(QGraphicsEffect):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dx = 0.0
        self._opacity = 1.0

    def _get_dx(self): return self._dx
    def _set_dx(self, v): self._dx = v; self.update()
    dx = pyqtProperty(float, _get_dx, _set_dx)

    def _get_opacity(self): return self._opacity
    def _set_opacity(self, v): self._opacity = v; self.update()
    opacity = pyqtProperty(float, _get_opacity, _set_opacity)

    def boundingRectFor(self, r):
        return r

    def draw(self, painter):
        pixmap, offset = self.sourcePixmap(Qt.LogicalCoordinates)
        painter.save()
        painter.setOpacity(self._opacity)
        painter.drawPixmap(QPointF(offset.x() + self._dx, offset.y()), pixmap)
        painter.restore()


class FadeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._eff = SlideEffect(self)
        self.setGraphicsEffect(self._eff)

        self._dx_anim = QPropertyAnimation(self._eff, b"dx")
        self._dx_anim.setDuration(420)
        self._dx_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._op_anim = QPropertyAnimation(self._eff, b"opacity")
        self._op_anim.setDuration(380)
        self._op_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._group = QParallelAnimationGroup()
        self._group.addAnimation(self._dx_anim)
        self._group.addAnimation(self._op_anim)

    def fade_in(self):
        self._group.stop()
        self._dx_anim.setStartValue(-52.0)
        self._dx_anim.setEndValue(0.0)
        self._op_anim.setStartValue(0.0)
        self._op_anim.setEndValue(1.0)
        self._group.start()


class SidebarButton(QPushButton):
    def __init__(self, text, icon_char="", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        label = f"   {icon_char}  {text}" if icon_char else f"   {text}"
        self.setText(label)
        self.setFixedHeight(38)
        self.setCursor(Qt.PointingHandCursor)

        self._bg = QColor("#141720")
        self._fg = QColor("#4e5a78")
        self._indicator = 0.0

        self._bg_anim = QPropertyAnimation(self, b"_bg_prop")
        self._bg_anim.setDuration(300)
        self._bg_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._fg_anim = QPropertyAnimation(self, b"_fg_prop")
        self._fg_anim.setDuration(300)
        self._fg_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._ind_anim = QPropertyAnimation(self, b"_ind_prop")
        self._ind_anim.setDuration(350)
        self._ind_anim.setEasingCurve(QEasingCurve.OutCubic)

    def _get_bg(self): return self._bg
    def _set_bg(self, c): self._bg = c; self.update()
    _bg_prop = pyqtProperty(QColor, _get_bg, _set_bg)

    def _get_fg(self): return self._fg
    def _set_fg(self, c): self._fg = c; self.update()
    _fg_prop = pyqtProperty(QColor, _get_fg, _set_fg)

    def _get_ind(self): return self._indicator
    def _set_ind(self, v): self._indicator = v; self.update()
    _ind_prop = pyqtProperty(float, _get_ind, _set_ind)

    def _run_anim(self, bg_to, fg_to, ind_to):
        for a in (self._bg_anim, self._fg_anim, self._ind_anim):
            a.stop()
        self._bg_anim.setStartValue(self._bg)
        self._bg_anim.setEndValue(bg_to)
        self._fg_anim.setStartValue(self._fg)
        self._fg_anim.setEndValue(fg_to)
        self._ind_anim.setStartValue(self._indicator)
        self._ind_anim.setEndValue(ind_to)
        for a in (self._bg_anim, self._fg_anim, self._ind_anim):
            a.start()

    def enterEvent(self, e):
        if not self.isChecked():
            self._run_anim(QColor("#1e2334"), QColor("#8898c8"), 0.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self.isChecked():
            self._run_anim(QColor("#141720"), QColor("#4e5a78"), 0.0)
        super().leaveEvent(e)

    def setChecked(self, v):
        super().setChecked(v)
        if v:
            self._run_anim(QColor("#1e2a48"), QColor("#6b9ed4"), 1.0)
        else:
            self._run_anim(QColor("#141720"), QColor("#4e5a78"), 0.0)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg)
        p.drawRoundedRect(r, 8, 8)
        if self._indicator > 0:
            bar_h = int(r.height() * 0.5 * self._indicator)
            bar_y = (r.height() - bar_h) // 2
            p.setBrush(QColor("#4a6fa5"))
            p.drawRoundedRect(QRect(0, bar_y, 3, bar_h), 1, 1)
        p.setPen(self._fg)
        font = self.font()
        font.setPixelSize(13)
        if self.isChecked():
            font.setWeight(QFont.DemiBold)
        p.setFont(font)
        p.drawText(r.adjusted(14, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        p.end()

class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._glow = 0.0
        self._anim = QPropertyAnimation(self, b"_glow_val")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._border_color = QColor("#323a52")
        self._bc_anim = QPropertyAnimation(self, b"_bc_val")
        self._bc_anim.setDuration(300)
        self._bc_anim.setEasingCurve(QEasingCurve.OutCubic)

    def _get_glow(self): return self._glow
    def _set_glow(self, v):
        self._glow = v
        self.update()
    _glow_val = pyqtProperty(float, _get_glow, _set_glow)

    def _get_bc(self): return self._border_color
    def _set_bc(self, c):
        self._border_color = c
        self.update()
    _bc_val = pyqtProperty(QColor, _get_bc, _set_bc)

    def enterEvent(self, e):
        self._anim.stop(); self._bc_anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(1.0)
        self._bc_anim.setStartValue(self._border_color)
        self._bc_anim.setEndValue(QColor("#4a6fa5"))
        self._anim.start(); self._bc_anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._anim.stop(); self._bc_anim.stop()
        self._anim.setStartValue(self._glow)
        self._anim.setEndValue(0.0)
        self._bc_anim.setStartValue(self._border_color)
        self._bc_anim.setEndValue(QColor("#323a52"))
        self._anim.start(); self._bc_anim.start()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        base = QColor("#1e2230")
        hover = QColor("#252c42")
        bg = QColor(
            int(base.red()   + (hover.red()   - base.red())   * self._glow),
            int(base.green() + (hover.green() - base.green()) * self._glow),
            int(base.blue()  + (hover.blue()  - base.blue())  * self._glow),
        )
        p.setPen(QPen(self._border_color, 1))
        p.setBrush(bg)
        p.drawRoundedRect(r.adjusted(1,1,-1,-1), 10, 10)
        if self._glow > 0:
            glow_pen = QPen(QColor(74, 111, 165, int(80 * self._glow)), 1)
            p.setPen(glow_pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(0,0,-1,-1), 10, 10)
        p.setPen(QColor("#dde3f0"))
        font = self.font()
        font.setPointSize(10)
        p.setFont(font)
        p.drawText(r, Qt.AlignCenter, self.text())
        p.end()


class AnimatedProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._display_val = 0.0
        self._smooth_anim = QPropertyAnimation(self, b"_smooth_val")
        self._smooth_anim.setDuration(600)
        self._smooth_anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setTextVisible(False)
        self.setFixedHeight(5)

    def _get_sv(self): return self._display_val
    def _set_sv(self, v):
        self._display_val = v
        self.update()
    _smooth_val = pyqtProperty(float, _get_sv, _set_sv)

    def setValue(self, v):
        super().setValue(v)
        self._smooth_anim.stop()
        self._smooth_anim.setStartValue(self._display_val)
        self._smooth_anim.setEndValue(float(v))
        self._smooth_anim.start()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1e2230"))
        p.drawRoundedRect(r, 3, 3)
        if self.maximum() > 0:
            ratio = self._display_val / self.maximum()
            fill_w = int(r.width() * ratio)
            if fill_w > 0:
                grad = QLinearGradient(0, 0, fill_w, 0)
                grad.setColorAt(0, QColor("#4a6fa5"))
                grad.setColorAt(1, QColor("#6b9ed4"))
                p.setBrush(grad)
                p.drawRoundedRect(QRect(0, 0, fill_w, r.height()), 3, 3)
        p.end()


class ProxyCheckerWorker(QObject):
    result_signal = pyqtSignal(int, bool, str)
    finished_signal = pyqtSignal()

    def __init__(self, proxies):
        super().__init__()
        self.proxies = proxies
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._check_all())
        self.finished_signal.emit()

    async def _check_all(self):
        for i, proxy in enumerate(self.proxies):
            if self._stop:
                return
            ok, info = await self._check_one(proxy)
            self.result_signal.emit(i, ok, info)

    async def _check_one(self, proxy):
        if not SOCKS_AVAILABLE:
            return False, "PySocks не установлен"
        try:
            ptype = proxy.get("type", "socks5").lower()
            pt = socks.SOCKS5
            if ptype == "socks4":
                pt = socks.SOCKS4
            elif ptype == "http":
                pt = socks.HTTP
            s = socks.socksocket()
            s.set_proxy(
                pt,
                proxy["host"],
                int(proxy["port"]),
                True,
                proxy.get("user") or None,
                proxy.get("password") or None,
            )
            s.settimeout(8)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: s.connect(("api.telegram.org", 443)))
            s.close()
            return True, "OK"
        except Exception as ex:
            return False, str(ex)[:60]


class AuthDialog(QDialog):
    _sig_status = pyqtSignal(str)
    _sig_need_password = pyqtSignal()
    _sig_show_code = pyqtSignal()
    _sig_done = pyqtSignal(str, str, str, str, str)

    def __init__(self, parent=None, proxy=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить аккаунт")
        self.setMinimumWidth(420)
        self.setStyleSheet(STYLE)
        self.result_account = None
        self._client = None
        self._phone = ""
        self._step = "phone"
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._sig_status.connect(self._set_status)
        self._sig_need_password.connect(self._show_password_step)
        self._sig_show_code.connect(self._show_code_step)
        self._sig_done.connect(self._on_done)
        self._proxy = proxy
        self._dot_timer = QTimer()
        self._dot_timer.timeout.connect(self._tick_status)
        self._dots = 0
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(14)

        title = QLabel("Подключение аккаунта")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #e8eef8;")
        lay.addWidget(title)

        link_lbl = QLabel('API ID и API Hash на <a href="https://my.telegram.org" style="color:#6b9ed4;">my.telegram.org</a>')
        link_lbl.setOpenExternalLinks(True)
        link_lbl.setStyleSheet("color: #4e5a78; font-size: 12px;")
        lay.addWidget(link_lbl)

        sep = QFrame()
        sep.setObjectName("separator")
        lay.addWidget(sep)

        for lbl_text, attr, ph in [
            ("API ID", "api_id", "12345678"),
            ("API HASH", "api_hash", "abcdef1234..."),
            ("НОМЕР ТЕЛЕФОНА", "phone_edit", "+79001234567"),
        ]:
            lbl = QLabel(lbl_text)
            lbl.setObjectName("section")
            lay.addWidget(lbl)
            edit = QLineEdit()
            edit.setPlaceholderText(ph)
            setattr(self, attr, edit)
            lay.addWidget(edit)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Код из Telegram")
        self.code_edit.setVisible(False)
        lay.addWidget(self.code_edit)

        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Пароль двухэтапной проверки")
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.pass_edit.setVisible(False)
        lay.addWidget(self.pass_edit)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #6b82c0; font-size: 12px;")
        self.status_lbl.setWordWrap(True)
        lay.addWidget(self.status_lbl)

        self.btn = AnimatedButton("Получить код")
        self.btn.setObjectName("primary")
        self.btn.clicked.connect(self._on_btn)
        lay.addWidget(self.btn)

    def _on_btn(self):
        if self._step == "phone":
            self._send_code()
        elif self._step == "code":
            self._confirm_code()
        elif self._step == "password":
            self._confirm_password()

    def _send_code(self):
        api_id_str = self.api_id.text().strip()
        api_hash = self.api_hash.text().strip()
        phone = self.phone_edit.text().strip()
        if not api_id_str or not api_hash or not phone:
            self._set_status("Заполните все поля")
            return
        try:
            api_id = int(api_id_str)
        except ValueError:
            self._set_status("API ID должен быть числом")
            return
        self._phone = phone
        self._api_id_val = api_id
        self._api_hash_val = api_hash
        fake_acc = {"phone": phone, "api_id": api_id, "api_hash": api_hash}
        self._client = build_client(fake_acc, self._proxy)
        self.btn.setEnabled(False)
        self._dots = 0
        self._dot_timer.start(600)

        async def _do():
            try:
                await self._client.connect()
                await self._client.send_code_request(phone)
                self._sig_show_code.emit()
            except Exception as ex:
                self._sig_status.emit(f"Ошибка: {ex}")
                self._sig_status.emit("btn_enable")

        asyncio.run_coroutine_threadsafe(_do(), self._loop)

    def _tick_status(self):
        self._dots = (self._dots + 1) % 4
        self.status_lbl.setText("Подключаемся к Telegram" + "." * self._dots)

    def _show_code_step(self):
        self._dot_timer.stop()
        self._step = "code"
        self.code_edit.setVisible(True)
        self.btn.setText("Войти")
        self.btn.setEnabled(True)
        self._set_status("Введите код из Telegram")

    def _confirm_code(self):
        code = self.code_edit.text().strip()
        if not code:
            self._set_status("Введите код")
            return
        self.btn.setEnabled(False)
        self._set_status("Проверяем...")

        async def _do():
            try:
                await self._client.sign_in(self._phone, code)
                me = await self._client.get_me()
                first = me.first_name or ""
                last = me.last_name or ""
                username = me.username or ""
                await self._client.disconnect()
                self._sig_done.emit(first, last, username, self._phone,
                                    str(self._api_id_val) + "|" + self._api_hash_val)
            except SessionPasswordNeededError:
                self._sig_need_password.emit()
            except Exception as ex:
                self._sig_status.emit(f"Ошибка: {ex}")
                self._sig_status.emit("btn_enable")

        asyncio.run_coroutine_threadsafe(_do(), self._loop)

    def _show_password_step(self):
        self._step = "password"
        self.pass_edit.setVisible(True)
        self.btn.setText("Войти")
        self.btn.setEnabled(True)
        self._set_status("Введите пароль двухэтапной проверки")

    def _confirm_password(self):
        password = self.pass_edit.text().strip()
        if not password:
            self._set_status("Введите пароль")
            return
        self.btn.setEnabled(False)
        self._set_status("Проверяем пароль...")

        async def _do():
            try:
                await self._client.sign_in(password=password)
                me = await self._client.get_me()
                first = me.first_name or ""
                last = me.last_name or ""
                username = me.username or ""
                await self._client.disconnect()
                self._sig_done.emit(first, last, username, self._phone,
                                    str(self._api_id_val) + "|" + self._api_hash_val)
            except Exception as ex:
                self._sig_status.emit(f"Ошибка: {ex}")
                self._sig_status.emit("btn_enable")

        asyncio.run_coroutine_threadsafe(_do(), self._loop)

    def _on_done(self, first, last, username, phone, api_str):
        api_id_str, api_hash = api_str.split("|", 1)
        name = f"{first} {last}".strip()
        self.result_account = {
            "phone": phone,
            "api_id": int(api_id_str),
            "api_hash": api_hash,
            "name": name,
            "username": username,
        }
        self._loop.call_soon_threadsafe(self._loop.stop)
        self.accept()

    def closeEvent(self, e):
        self._dot_timer.stop()
        self._loop.call_soon_threadsafe(self._loop.stop)
        super().closeEvent(e)

    def _set_status(self, text):
        if text == "btn_enable":
            self.btn.setEnabled(True)
            return
        self.status_lbl.setText(text)


class SenderWorker(QObject):
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal()
    failed_signal = pyqtSignal(str)
    failed_detail_signal = pyqtSignal(str, str)
    current_tag_signal = pyqtSignal(int, str)
    spamblock_signal = pyqtSignal(int, str, str, list)

    def __init__(self, account, recipients, pastes, interval_min, pastes_per_recipient,
                 proxy=None, tag_interval_min=0, worker_id=0):
        super().__init__()
        self.account = account
        self.recipients = recipients
        self.pastes = pastes
        self.interval_min = interval_min
        self.pastes_per_recipient = pastes_per_recipient
        self.proxy = proxy
        self.tag_interval_min = tag_interval_min
        self.worker_id = worker_id
        self._stop = False
        self._pause = False
        self._done = 0

    def stop(self):
        self._stop = True

    def pause(self):
        self._pause = True

    def resume(self):
        self._pause = False

    async def _interruptible_sleep(self, seconds):
        elapsed = 0
        while elapsed < seconds:
            if self._stop:
                return
            while self._pause:
                if self._stop:
                    return
                await asyncio.sleep(0.5)
            await asyncio.sleep(1)
            elapsed += 1

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._send_all())
        self.finished_signal.emit()

    async def _send_all(self):
        acc = self.account
        _set_session_wal(acc["phone"])
        client = build_client(acc, self.proxy)
        for attempt in range(3):
            try:
                await client.connect()
                break
            except Exception as ex:
                if "database is locked" in str(ex).lower() and attempt < 2:
                    self.log_signal.emit(f"[W{self.worker_id+1}] База заблокирована, повтор...", "warn")
                    await asyncio.sleep(3)
                else:
                    self.log_signal.emit(f"[W{self.worker_id+1}] Ошибка подключения: {ex}", "err")
                    return
        if not await client.is_user_authorized():
            self.log_signal.emit("Аккаунт не авторизован", "err")
            await client.disconnect()
            return

        pastes_to_use = self.pastes
        total = len(self.recipients) * len(pastes_to_use)
        self._done = 0
        first_rec = True

        for rec in self.recipients:
            tag = recipient_tag(rec)
            token = recipient_token(rec)

            if not first_rec:
                if self.tag_interval_min > 0:
                    self.log_signal.emit(
                        f"[W{self.worker_id+1}] Ждём {self.tag_interval_min} мин...",
                        "info"
                    )
                    await self._interruptible_sleep(self.tag_interval_min * 60)
                elif self.interval_min > 0:
                    await self._interruptible_sleep(self.interval_min * 60)
                if self._stop:
                    await client.disconnect()
                    return

            first_rec = False
            self.current_tag_signal.emit(self.worker_id, tag)

            for i, paste in enumerate(pastes_to_use):
                if self._stop:
                    self.log_signal.emit(f"[W{self.worker_id+1}] Остановлена", "warn")
                    await client.disconnect()
                    return
                while self._pause:
                    if self._stop:
                        await client.disconnect()
                        return
                    await asyncio.sleep(0.5)
                try:
                    text = apply_token(paste, token) if token else paste
                    await client.send_message(tag, text)
                    self.log_signal.emit(f"[W{self.worker_id+1}] ok  {tag}", "ok")
                except FloodWaitError as e:
                    self.log_signal.emit(f"[W{self.worker_id+1}] Flood {e.seconds}s  {tag}", "warn")
                    await self._interruptible_sleep(e.seconds)
                except (UserPrivacyRestrictedError, UsernameNotOccupiedError):
                    self.log_signal.emit(f"[W{self.worker_id+1}] Недоступен  {tag}", "warn")
                    self.failed_signal.emit(tag)
                    self.failed_detail_signal.emit(tag, "Приватность или пользователь не найден")
                    self._done += 1
                    self.progress_signal.emit(self._done, total)
                    break
                except PeerFloodError:
                    self.log_signal.emit(f"[W{self.worker_id+1}] PeerFlood на {tag} - пытаемся снять спамблок...", "err")
                    freed = False
                    last_reply = ""
                    buttons = []
                    for attempt in range(3):
                        try:
                            await client.send_message("Spam_info_bot", "/start")
                            await asyncio.sleep(3)
                            reply_text = ""
                            btn_labels = []
                            async for m in client.iter_messages("Spam_info_bot", limit=3):
                                if m.message and not reply_text:
                                    reply_text = m.message
                                if m.reply_markup:
                                    try:
                                        for row in m.reply_markup.rows:
                                            for btn in row.buttons:
                                                if hasattr(btn, "text"):
                                                    btn_labels.append(btn.text)
                                    except Exception:
                                        pass
                                break
                            last_reply = reply_text
                            buttons = btn_labels
                            self.log_signal.emit(f"[W{self.worker_id+1}] Spam info bot попытка {attempt+1}: {reply_text[:80]}", "warn")
                            low = reply_text.lower()
                            if any(w in low for w in ("free", "no limits", "свободен", "ограничений", "bird")):
                                freed = True
                                self.log_signal.emit(f"[W{self.worker_id+1}] Спамблок снят", "ok")
                                break
                        except Exception as sb_ex:
                            self.log_signal.emit(f"[W{self.worker_id+1}] Spam info bot ошибка: {sb_ex}", "err")
                        await asyncio.sleep(5)
                    self.spamblock_signal.emit(self.worker_id, tag, last_reply, buttons)
                    await client.disconnect()
                    return
                except Exception as ex:
                    err_str = str(ex).lower()
                    skip_errors = (
                        "database is locked",
                        "user not found",
                        "username invalid",
                        "nobody",
                        "you have been blocked",
                        "user is blocked",
                        "chat write forbidden",
                        "not in the chat",
                        "banned",
                        "deactivated",
                        "need to buy",
                        "paid",
                        "slowmode",
                    )
                    if "database is locked" in err_str:
                        self.log_signal.emit(f"[W{self.worker_id+1}] База заблокирована, ждём...", "warn")
                        await asyncio.sleep(5)
                    elif any(e in err_str for e in skip_errors):
                        self.log_signal.emit(f"[W{self.worker_id+1}] Скип {tag}: {ex}", "warn")
                        self.failed_signal.emit(tag)
                        self.failed_detail_signal.emit(tag, str(ex))
                        self._done += 1
                        self.progress_signal.emit(self._done, total)
                        break
                    else:
                        self.log_signal.emit(f"[W{self.worker_id+1}] err  {tag}: {ex}", "err")
                        self.failed_signal.emit(tag)
                        self.failed_detail_signal.emit(tag, str(ex))
                else:
                    self._done += 1
                    self.progress_signal.emit(self._done, total)
                    if i < len(pastes_to_use) - 1 and self.interval_min > 0:
                        await self._interruptible_sleep(self.interval_min * 60)
                    continue
                self._done += 1
                self.progress_signal.emit(self._done, total)
                if i < len(pastes_to_use) - 1 and self.interval_min > 0:
                    await self._interruptible_sleep(self.interval_min * 60)

        await client.disconnect()


class ChatLoader(QObject):
    messages_loaded = pyqtSignal(str, list)
    error_signal = pyqtSignal(str)

    def __init__(self, account, recipient, proxy=None):
        super().__init__()
        self.account = account
        self.recipient = recipient
        self.proxy = proxy

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._load())

    async def _load(self):
        _set_session_wal(self.account["phone"], chat_mode=True)
        for attempt in range(5):
            try:
                client = build_client(self.account, self.proxy, chat_mode=True)
                await client.connect()
                if not await client.is_user_authorized():
                    self.error_signal.emit("Аккаунт не авторизован")
                    await client.disconnect()
                    return
                msgs = []
                async for msg in client.iter_messages(self.recipient, limit=50):
                    if msg.message:
                        sender = "Я" if msg.out else self.recipient
                        ts = msg.date.strftime("%d.%m %H:%M")
                        msgs.append({"sender": sender, "text": msg.message, "ts": ts, "out": msg.out})
                msgs.reverse()
                await client.disconnect()
                self.messages_loaded.emit(self.recipient, msgs)
                return
            except Exception as ex:
                if "database is locked" in str(ex).lower() and attempt < 4:
                    await asyncio.sleep(3)
                else:
                    self.error_signal.emit(str(ex))
                    return


class StatCard(QFrame):
    def __init__(self, label, value="0", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(100)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)
        lbl = QLabel(label)
        lbl.setObjectName("section")
        lbl.setStyleSheet("background: transparent; font-size: 10px; font-weight: 700; color: #6b82c0; letter-spacing: 1.8px;")
        lay.addWidget(lbl)
        self._val = QLabel(value)
        self._val.setStyleSheet("background: transparent; font-size: 32px; font-weight: 700; color: #c8d8f0; letter-spacing: -1px;")
        lay.addWidget(self._val)
        lay.addStretch()

    def set_value(self, v):
        self._val.setText(str(v))
        self._val.setStyleSheet("background: transparent; font-size: 32px; font-weight: 700; color: #6b9ed4; letter-spacing: -1px;")
        QTimer.singleShot(300, lambda: self._val.setStyleSheet(
            "background: transparent; font-size: 32px; font-weight: 700; color: #c8d8f0; letter-spacing: -1px;"))


COMBO_VIEW_STYLE = """
    QAbstractItemView {
        background:
        color:
        border: 1px solid
        border-radius: 6px;
        outline: none;
        padding: 2px;
        selection-background-color:
        selection-color:
    }
    QAbstractItemView::item {
        padding: 7px 12px;
        min-height: 28px;
        background: transparent;
        color:
    }
    QAbstractItemView::item:hover {
        background:
        color:
    }
    QAbstractItemView::item:selected {
        background:
        color:
    }
"""


def styled_combo():
    cb = QComboBox()
    cb.view().setStyleSheet(COMBO_VIEW_STYLE)
    return cb


class ProxyStatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = QColor("#3a4a68")

    def set_status(self, status):
        colors = {"ok": "#6a9e80", "err": "#b06070", "checking": "#a08858"}
        self._color = QColor(colors.get(status, "#3a4a68"))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(self.rect())
        p.end()


class ProxyRowWidget(QWidget):
    def __init__(self, proxy_data, idx, parent=None):
        super().__init__(parent)
        self.proxy_data = proxy_data
        self.idx = idx
        self.setFixedHeight(36)
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(10)

        self._dot = ProxyStatusDot()
        lay.addWidget(self._dot)

        type_lbl = QLabel(proxy_data.get("type", "socks5").upper())
        type_lbl.setStyleSheet("color: #6b82c0; font-size: 11px; font-weight: 700; background: transparent; min-width: 50px;")
        lay.addWidget(type_lbl)

        host_lbl = QLabel(f"{proxy_data['host']}:{proxy_data['port']}")
        host_lbl.setStyleSheet("color: #a8b8d8; background: transparent;")
        lay.addWidget(host_lbl)

        if proxy_data.get("user"):
            user_lbl = QLabel(proxy_data["user"])
            user_lbl.setStyleSheet("color: #4e5a78; font-size: 11px; background: transparent;")
            lay.addWidget(user_lbl)

        lay.addStretch()

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("font-size: 11px; background: transparent; min-width: 40px;")
        lay.addWidget(self._status_lbl)

        self._active_lbl = QLabel("")
        self._active_lbl.setStyleSheet("color: #4a6fa5; font-size: 11px; font-weight: 700; background: transparent; min-width: 50px;")
        lay.addWidget(self._active_lbl)

    def set_status(self, status, info=""):
        self._dot.set_status(status)
        if status == "ok":
            self._status_lbl.setText("OK")
            self._status_lbl.setStyleSheet("color: #6a9e80; font-size: 11px; background: transparent; min-width: 40px;")
        elif status == "err":
            self._status_lbl.setText("ERR")
            self._status_lbl.setStyleSheet("color: #b06070; font-size: 11px; background: transparent; min-width: 40px;")
        elif status == "checking":
            self._status_lbl.setText("...")
            self._status_lbl.setStyleSheet("color: #a08858; font-size: 11px; background: transparent; min-width: 40px;")
        else:
            self._status_lbl.setText("")

    def set_active(self, active):
        self._active_lbl.setText("АКТИВНЫЕ" if active else "")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lagos Sender")
        self.setMinimumSize(1160, 720)
        self.setStyleSheet(STYLE)
        self.data = load_data()
        self._workers = {}
        self._worker_threads = {}
        self._shared_clients = {}
        self._worker_totals = {}
        self._worker_paused = {}
        self._ok_count = 0
        self._err_count = 0
        self._paused = False
        self._total_messages = 0
        self._done_messages = 0
        self._proxy_check_worker = None
        self._proxy_status = {}
        self._proxy_row_widgets = []
        self._failed_recipients = []
        self._failed_entries = []
        self._worker_cards = []
        self._build_ui()
        self._refresh_accounts()
        self._refresh_recipients()
        self._refresh_pastes()
        self._refresh_proxies()
        self._refresh_app_proxy_status()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet("background: #141720; border: none;")
        sb_lay = QVBoxLayout(sidebar)
        sb_lay.setContentsMargins(12, 24, 12, 20)
        sb_lay.setSpacing(3)

        logo_lbl = QLabel("Lagos Sender")
        logo_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #8898c8; letter-spacing: 0.5px; background: transparent; border: none;")
        logo_lbl.setAlignment(Qt.AlignCenter)
        sb_lay.addWidget(logo_lbl)
        sb_lay.addSpacing(20)

        self._tabs_btns = []
        tabs = [
            ("Аккаунты", 0),
            ("Теги", 1),
            ("Пасты", 2),
            ("Отписи", 3),
            ("Логи", 4),
            ("Прокси пул", 5),
            ("Системный прокси", 6),
            ("Чаты", 7),
            ("Спамблок", 8),
        ]
        for name, idx in tabs:
            btn = SidebarButton(name)
            btn.clicked.connect(lambda checked, i=idx: self._switch_tab(i))
            sb_lay.addWidget(btn)
            self._tabs_btns.append(btn)

        sb_lay.addStretch()
        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setStyleSheet("color: #2e3a52; font-size: 11px; background: transparent; border: none;")
        ver_lbl.setAlignment(Qt.AlignCenter)
        sb_lay.addWidget(ver_lbl)
        root.addWidget(sidebar)

        sidebar_sep = QFrame()
        sidebar_sep.setFixedWidth(1)
        sidebar_sep.setStyleSheet("QFrame { background: #1e2334; border: none; }")
        root.addWidget(sidebar_sep)

        right_wrap = QWidget()
        right_wrap.setStyleSheet("background: #1a1d26;")
        right_vlay = QVBoxLayout(right_wrap)
        right_vlay.setContentsMargins(0, 0, 0, 0)
        right_vlay.setSpacing(0)

        topbar = QWidget()
        topbar.setFixedHeight(52)
        topbar.setStyleSheet("background: #1a1d26; border-bottom: 1px solid #1e2334;")
        topbar_lay = QHBoxLayout(topbar)
        topbar_lay.setContentsMargins(24, 10, 24, 10)
        topbar_lay.addStretch()

        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setMinimumWidth(200)
        self.progress_bar.hide()
        topbar_lay.addWidget(self.progress_bar)
        topbar_lay.addSpacing(10)

        self._pause_btn = AnimatedButton("Пауза")
        self._pause_btn.setFixedHeight(32)
        self._pause_btn.setMinimumWidth(90)
        self._pause_btn.hide()
        self._pause_btn.clicked.connect(self._toggle_pause)
        topbar_lay.addWidget(self._pause_btn)
        topbar_lay.addSpacing(8)

        self._run_btn = AnimatedButton("Начать отписи")
        self._run_btn.setFixedHeight(32)
        self._run_btn.setMinimumWidth(160)
        self._run_btn.clicked.connect(self._toggle_send)
        topbar_lay.addWidget(self._run_btn)
        right_vlay.addWidget(topbar)

        self._stack = QStackedWidget()
        right_vlay.addWidget(self._stack)
        root.addWidget(right_wrap)

        self._pages = [
            self._build_accounts_page(),
            self._build_recipients_page(),
            self._build_pastes_page(),
            self._build_sender_page(),
            self._build_logs_page(),
            self._build_proxies_page(),
            self._build_system_proxy_page(),
            self._build_chats_page(),
            self._build_spamblock_page(),
        ]
        for p in self._pages:
            self._stack.addWidget(p)

        self._switch_tab(0)

    def _switch_tab(self, idx):
        for i, btn in enumerate(self._tabs_btns):
            btn.setChecked(i == idx)
        page = self._pages[idx]
        if hasattr(page, "fade_in"):
            page.fade_in()
        self._stack.setCurrentIndex(idx)
        if idx == 3:
            self._refresh_sender_page()
        if idx == 6:
            self._refresh_chats_accounts()
        if idx == 7:
            self._refresh_spamblock_page()

    def _mk_page(self):
        w = FadeWidget()
        w.setStyleSheet("background: #1a1d26;")
        return w

    def _build_accounts_page(self):
        w = self._mk_page()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 36, 36, 36)
        lay.setSpacing(14)

        hdr = QLabel("Аккаунты")
        hdr.setObjectName("header")
        lay.addWidget(hdr)

        sep = QFrame()
        sep.setObjectName("separator")
        lay.addWidget(sep)

        self.acc_list = QListWidget()
        lay.addWidget(self.acc_list)

        btn_row = QHBoxLayout()
        add_btn = AnimatedButton("Добавить аккаунт")
        add_btn.clicked.connect(self._add_account)
        del_btn = AnimatedButton("Удалить")
        del_btn.clicked.connect(self._del_account)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        return w

    def _refresh_accounts(self):
        self.acc_list.clear()
        for acc in self.data["accounts"]:
            name = acc.get("name", acc["phone"])
            un = f"@{acc['username']}" if acc.get("username") else ""
            self.acc_list.addItem(f"  {name}  {un}  {acc['phone']}")

    def _add_account(self):
        proxy = self._get_app_proxy()
        dlg = AuthDialog(self, proxy=proxy)
        if dlg.exec_() == QDialog.Accepted:
            self.data["accounts"].append(dlg.result_account)
            save_data(self.data)
            self._refresh_accounts()
            self._refresh_sender_page()

    def _del_account(self):
        row = self.acc_list.currentRow()
        if row < 0:
            return
        self.data["accounts"].pop(row)
        save_data(self.data)
        self._refresh_accounts()
        self._refresh_sender_page()

    def _build_recipients_page(self):
        w = self._mk_page()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 36, 36, 36)
        lay.setSpacing(14)

        hdr = QLabel("Теги")
        hdr.setObjectName("header")
        lay.addWidget(hdr)

        sub = QLabel("Создавайте отдельные базы для каждого потока отписок")
        sub.setObjectName("subheader")
        lay.addWidget(sub)

        sep = QFrame()
        sep.setObjectName("separator")
        lay.addWidget(sep)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)
        lbl_db = QLabel("БАЗА:")
        lbl_db.setObjectName("section")
        top_row.addWidget(lbl_db)
        self.db_combo = styled_combo()
        self.db_combo.setFixedHeight(34)
        self.db_combo.setMinimumWidth(200)
        self.db_combo.currentIndexChanged.connect(self._on_db_changed)
        top_row.addWidget(self.db_combo)
        self.db_name_edit = QLineEdit()
        self.db_name_edit.setPlaceholderText("Название новой базы...")
        self.db_name_edit.setFixedHeight(34)
        self.db_name_edit.setMinimumWidth(180)
        top_row.addWidget(self.db_name_edit)
        new_db_btn = AnimatedButton("+ Новая база")
        new_db_btn.setFixedHeight(34)
        new_db_btn.clicked.connect(self._create_db)
        top_row.addWidget(new_db_btn)
        del_db_btn = AnimatedButton("Удалить базу")
        del_db_btn.setFixedHeight(34)
        del_db_btn.clicked.connect(self._delete_db)
        top_row.addWidget(del_db_btn)
        top_row.addStretch()
        lay.addLayout(top_row)

        content = QHBoxLayout()
        content.setSpacing(28)

        left = QVBoxLayout()
        lbl_s = QLabel("СПИСОК")
        lbl_s.setObjectName("section")
        left.addWidget(lbl_s)
        self.rec_list = QListWidget()
        self.rec_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        left.addWidget(self.rec_list)
        self.rec_count = QLabel("0 тегов")
        self.rec_count.setStyleSheet("color: #4e5a78; font-size: 12px;")
        left.addWidget(self.rec_count)
        content.addLayout(left, 2)

        right = QVBoxLayout()
        right.setSpacing(10)

        lbl_a = QLabel("ДОБАВИТЬ")
        lbl_a.setObjectName("section")
        right.addWidget(lbl_a)
        self.rec_single = QLineEdit()
        self.rec_single.setPlaceholderText("@username - $TOKEN")
        right.addWidget(self.rec_single)
        add_one = AnimatedButton("+ Добавить")
        add_one.clicked.connect(self._add_recipient_single)
        right.addWidget(add_one)

        lbl_b = QLabel("СПИСКОМ")
        lbl_b.setObjectName("section")
        lbl_b.setContentsMargins(0, 14, 0, 0)
        right.addWidget(lbl_b)
        self.rec_bulk = QPlainTextEdit()
        self.rec_bulk.setPlaceholderText("@user1 - $TOKEN1\n@user2")
        self.rec_bulk.setMaximumHeight(130)
        right.addWidget(self.rec_bulk)
        add_bulk = AnimatedButton("Добавить всех")
        add_bulk.clicked.connect(self._add_recipients_bulk)
        right.addWidget(add_bulk)

        right.addSpacing(14)
        sep2 = QFrame()
        sep2.setObjectName("separator")
        right.addWidget(sep2)
        right.addSpacing(14)

        del_sel_btn = AnimatedButton("Удалить выбранные")
        del_sel_btn.clicked.connect(self._del_selected_recipients)
        right.addWidget(del_sel_btn)

        hint = QLabel("Ctrl+Click для выбора нескольких")
        hint.setStyleSheet("color: #3a4a68; font-size: 11px;")
        right.addWidget(hint)

        clear_btn = AnimatedButton("Очистить список")
        clear_btn.clicked.connect(self._clear_recipients)
        right.addWidget(clear_btn)

        export_btn = AnimatedButton("Копировать список")
        export_btn.clicked.connect(self._export_recipients)
        right.addWidget(export_btn)

        right.addStretch()
        content.addLayout(right, 1)
        lay.addLayout(content)
        self._refresh_db_combo()
        return w

    def _get_current_db_key(self):
        idx = self.db_combo.currentIndex()
        if idx <= 0:
            return None
        return self.db_combo.currentText()

    def _get_current_recipients(self):
        key = self._get_current_db_key()
        if key is None:
            return self.data["recipients"]
        return self.data["recipient_dbs"].get(key, [])

    def _set_current_recipients(self, lst):
        key = self._get_current_db_key()
        if key is None:
            self.data["recipients"] = lst
        else:
            if "recipient_dbs" not in self.data:
                self.data["recipient_dbs"] = {}
            self.data["recipient_dbs"][key] = lst

    def _refresh_db_combo(self):
        self.db_combo.blockSignals(True)
        cur = self.db_combo.currentText()
        self.db_combo.clear()
        self.db_combo.addItem("База")
        for name in self.data.get("recipient_dbs", {}):
            self.db_combo.addItem(name)
        idx = self.db_combo.findText(cur)
        self.db_combo.setCurrentIndex(max(0, idx))
        self.db_combo.blockSignals(False)
        self._refresh_recipients()
        self._refresh_all_worker_rec_combos()

    def _on_db_changed(self):
        self._refresh_recipients()

    def _create_db(self):
        name = self.db_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название базы")
            return
        if "recipient_dbs" not in self.data:
            self.data["recipient_dbs"] = {}
        if name in self.data["recipient_dbs"]:
            QMessageBox.warning(self, "Ошибка", "База с таким именем уже существует")
            return
        self.data["recipient_dbs"][name] = []
        save_data(self.data)
        self.db_name_edit.clear()
        self._refresh_db_combo()
        idx = self.db_combo.findText(name)
        if idx >= 0:
            self.db_combo.setCurrentIndex(idx)

    def _delete_db(self):
        key = self._get_current_db_key()
        if key is None:
            QMessageBox.warning(self, "Ошибка", "Общую базу удалить нельзя")
            return
        reply = QMessageBox.question(
            self, "Удалить базу",
            f"Удалить базу '{key}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        del self.data["recipient_dbs"][key]
        save_data(self.data)
        self._refresh_db_combo()

    def _refresh_recipients(self):
        self.rec_list.clear()
        recs = self._get_current_recipients()
        for r in recs:
            tag = recipient_tag(r)
            token = recipient_token(r)
            label = f"  {tag}  {token}" if token else f"  {tag}"
            self.rec_list.addItem(label)
        self.rec_count.setText(f"{len(recs)} тегов")

    def _add_recipient_single(self):
        raw = self.rec_single.text().strip()
        if not raw:
            return
        tag, token = _parse_recipient_line(raw)
        entry = {"tag": tag, "token": token}
        recs = self._get_current_recipients()
        if not any(recipient_tag(r) == tag for r in recs):
            recs.append(entry)
            self._set_current_recipients(recs)
            save_data(self.data)
            self._refresh_recipients()
        self.rec_single.clear()

    def _add_recipients_bulk(self):
        text = self.rec_bulk.toPlainText()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        added = 0
        recs = self._get_current_recipients()
        for line in lines:
            tag, token = _parse_recipient_line(line)
            entry = {"tag": tag, "token": token}
            if not any(recipient_tag(r) == tag for r in recs):
                recs.append(entry)
                added += 1
        self._set_current_recipients(recs)
        save_data(self.data)
        self._refresh_recipients()
        self.rec_bulk.clear()
        QMessageBox.information(self, "Готово", f"Добавлено {added} тегов")

    def _del_selected_recipients(self):
        rows = sorted(set(idx.row() for idx in self.rec_list.selectedIndexes()), reverse=True)
        if not rows:
            return
        recs = self._get_current_recipients()
        for row in rows:
            recs.pop(row)
        self._set_current_recipients(recs)
        save_data(self.data)
        self._refresh_recipients()

    def _clear_recipients(self):
        self._set_current_recipients([])
        save_data(self.data)
        self._refresh_recipients()

    def _export_recipients(self):
        recipients = self._get_current_recipients()
        if not recipients:
            QMessageBox.information(self, "Экспорт", "Список пуст")
            return
        lines = []
        for r in recipients:
            tag = recipient_tag(r)
            token = recipient_token(r)
            lines.append(f"{tag} - {token}" if token else tag)
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Экспорт", f"Скопировано {len(lines)} тегов")

    def _build_pastes_page(self):
        w = self._mk_page()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 36, 36, 36)
        lay.setSpacing(14)

        hdr = QLabel("Пасты")
        hdr.setObjectName("header")
        lay.addWidget(hdr)
        sub = QLabel("Тексты сообщений отправляются по очереди каждому мамонту")
        sub.setObjectName("subheader")
        lay.addWidget(sub)

        sep = QFrame()
        sep.setObjectName("separator")
        lay.addWidget(sep)

        content = QHBoxLayout()
        content.setSpacing(28)

        left = QVBoxLayout()
        lbl_l = QLabel("ПАСТЫ")
        lbl_l.setObjectName("section")
        left.addWidget(lbl_l)
        self.paste_list = QListWidget()
        self.paste_list.currentRowChanged.connect(self._load_paste)
        left.addWidget(self.paste_list)
        row = QHBoxLayout()
        add_p = AnimatedButton("+ Новая")
        add_p.clicked.connect(self._new_paste)
        del_p = AnimatedButton("Удалить")
        del_p.clicked.connect(self._del_paste)
        row.addWidget(add_p)
        row.addWidget(del_p)
        left.addLayout(row)
        content.addLayout(left, 1)

        right = QVBoxLayout()
        lbl_r = QLabel("ТЕКСТ СООБЩЕНИЯ")
        lbl_r.setObjectName("section")
        right.addWidget(lbl_r)
        self.paste_edit = QTextEdit()
        self.paste_edit.setPlaceholderText("Введите текст сообщения...")
        self.paste_edit.textChanged.connect(self._autosave_paste)
        right.addWidget(self.paste_edit)
        save_p = AnimatedButton("Сохранить")
        save_p.clicked.connect(self._save_paste)
        right.addWidget(save_p)
        content.addLayout(right, 2)
        lay.addLayout(content)

        self._paste_autosave_timer = QTimer()
        self._paste_autosave_timer.setSingleShot(True)
        self._paste_autosave_timer.timeout.connect(self._save_paste_silent)
        return w

    def _autosave_paste(self):
        self._paste_autosave_timer.start(800)

    def _save_paste_silent(self):
        row = self.paste_list.currentRow()
        if row < 0 or row >= len(self.data["pastes"]):
            return
        self.data["pastes"][row] = self.paste_edit.toPlainText()
        save_data(self.data)
        self._refresh_pastes_keep_row(row)

    def _refresh_pastes(self):
        self.paste_list.clear()
        for i, p in enumerate(self.data["pastes"]):
            preview = p[:48].replace("\n", " ")
            self.paste_list.addItem(f"  {i+1}.  {preview}")

    def _refresh_pastes_keep_row(self, row):
        self.paste_list.blockSignals(True)
        self.paste_list.clear()
        for i, p in enumerate(self.data["pastes"]):
            preview = p[:48].replace("\n", " ")
            self.paste_list.addItem(f"  {i+1}.  {preview}")
        self.paste_list.blockSignals(False)
        if row < self.paste_list.count():
            self.paste_list.setCurrentRow(row)

    def _load_paste(self, row):
        if 0 <= row < len(self.data["pastes"]):
            self.paste_edit.blockSignals(True)
            self.paste_edit.setPlainText(self.data["pastes"][row])
            self.paste_edit.blockSignals(False)

    def _new_paste(self):
        self.data["pastes"].append("")
        save_data(self.data)
        self._refresh_pastes()
        self.paste_list.setCurrentRow(len(self.data["pastes"]) - 1)
        self.paste_edit.setFocus()

    def _save_paste(self):
        row = self.paste_list.currentRow()
        if row < 0:
            return
        self.data["pastes"][row] = self.paste_edit.toPlainText()
        save_data(self.data)
        self._refresh_pastes_keep_row(row)

    def _del_paste(self):
        row = self.paste_list.currentRow()
        if row < 0:
            return
        self.data["pastes"].pop(row)
        save_data(self.data)
        self._refresh_pastes()

    def _build_proxies_page(self):
        w = self._mk_page()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 36, 36, 36)
        lay.setSpacing(14)

        hdr = QLabel("Прокси пул")
        hdr.setObjectName("header")
        lay.addWidget(hdr)
        sub = QLabel("Прокси для отписей")
        sub.setObjectName("subheader")
        lay.addWidget(sub)

        sep = QFrame()
        sep.setObjectName("separator")
        lay.addWidget(sep)

        content = QHBoxLayout()
        content.setSpacing(28)

        left = QVBoxLayout()
        lbl_list = QLabel("ПРОКСИ ПУЛ")
        lbl_list.setObjectName("section")
        left.addWidget(lbl_list)

        self.proxy_list = QListWidget()
        self.proxy_list.setSpacing(3)
        self.proxy_list.setStyleSheet("""
            QListWidget {
                background:
                border: 1px solid
                border-radius: 8px;
                outline: none;
                padding: 4px;
            }
            QListWidget::item {
                border-radius: 6px;
                padding: 0px;
                margin: 1px 2px;
                background: transparent;
            }
            QListWidget::item:selected {
                background:
                border-radius: 6px;
            }
            QListWidget::item:hover {
                background:
                border-radius: 6px;
            }
        """)
        left.addWidget(self.proxy_list)

        proxy_btn_row = QHBoxLayout()
        set_active_btn = AnimatedButton("Использовать")
        set_active_btn.clicked.connect(self._set_active_proxy)
        check_btn = AnimatedButton("Проверить все")
        check_btn.clicked.connect(self._check_all_proxies)
        del_proxy_btn = AnimatedButton("Удалить")
        del_proxy_btn.clicked.connect(self._del_proxy)
        proxy_btn_row.addWidget(set_active_btn)
        proxy_btn_row.addWidget(check_btn)
        proxy_btn_row.addWidget(del_proxy_btn)
        left.addLayout(proxy_btn_row)

        self.active_proxy_lbl = QLabel("Активные прокси: нет")
        self.active_proxy_lbl.setStyleSheet("color: #4e5a78; font-size: 12px;")
        left.addWidget(self.active_proxy_lbl)
        content.addLayout(left, 2)

        right = QVBoxLayout()
        right.setSpacing(10)

        lbl_add = QLabel("ДОБАВИТЬ ПРОКСИ")
        lbl_add.setObjectName("section")
        right.addWidget(lbl_add)

        lbl_type = QLabel("ТИП")
        lbl_type.setObjectName("section")
        right.addWidget(lbl_type)
        self.proxy_type = styled_combo()
        self.proxy_type.addItems(["socks5", "socks4", "http"])
        self.proxy_type.setFixedHeight(38)
        right.addWidget(self.proxy_type)

        for lbl_text, attr, ph in [
            ("ХОСТ", "proxy_host", "127.0.0.1"),
            ("ПОРТ", "proxy_port", "1080"),
            ("ЛОГИН (необязательно)", "proxy_user", "username"),
        ]:
            lbl = QLabel(lbl_text)
            lbl.setObjectName("section")
            right.addWidget(lbl)
            edit = QLineEdit()
            edit.setPlaceholderText(ph)
            setattr(self, attr, edit)
            right.addWidget(edit)

        lbl_pass = QLabel("ПАРОЛЬ (необязательно)")
        lbl_pass.setObjectName("section")
        right.addWidget(lbl_pass)
        self.proxy_pass = QLineEdit()
        self.proxy_pass.setPlaceholderText("пароль")
        self.proxy_pass.setEchoMode(QLineEdit.Password)
        right.addWidget(self.proxy_pass)

        add_proxy_btn = AnimatedButton("+ Добавить")
        add_proxy_btn.clicked.connect(self._add_proxy)
        right.addWidget(add_proxy_btn)

        right.addStretch()
        content.addLayout(right, 1)
        lay.addLayout(content)
        return w

    def _build_system_proxy_page(self):
        w = self._mk_page()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 36, 36, 36)
        lay.setSpacing(14)

        hdr = QLabel("Системный прокси")
        hdr.setObjectName("header")
        lay.addWidget(hdr)
        sub = QLabel("Используется для добавления аккаунтов, чатов и спамблока")
        sub.setObjectName("subheader")
        lay.addWidget(sub)

        sep = QFrame()
        sep.setObjectName("separator")
        lay.addWidget(sep)

        form = QVBoxLayout()
        form.setSpacing(10)

        lbl_type = QLabel("ТИП")
        lbl_type.setObjectName("section")
        form.addWidget(lbl_type)
        self.app_proxy_type = styled_combo()
        self.app_proxy_type.addItems(["socks5", "socks4", "http"])
        self.app_proxy_type.setFixedHeight(38)
        self.app_proxy_type.setMaximumWidth(320)
        form.addWidget(self.app_proxy_type)

        for lbl_text, attr, ph in [
            ("ХОСТ", "app_proxy_host", "127.0.0.1"),
            ("ПОРТ", "app_proxy_port", "1080"),
            ("ЛОГИН (необязательно)", "app_proxy_user", "username"),
        ]:
            lbl = QLabel(lbl_text)
            lbl.setObjectName("section")
            form.addWidget(lbl)
            edit = QLineEdit()
            edit.setPlaceholderText(ph)
            edit.setMaximumWidth(320)
            setattr(self, attr, edit)
            form.addWidget(edit)

        lbl_pass = QLabel("ПАРОЛЬ (необязательно)")
        lbl_pass.setObjectName("section")
        form.addWidget(lbl_pass)
        self.app_proxy_pass = QLineEdit()
        self.app_proxy_pass.setPlaceholderText("пароль")
        self.app_proxy_pass.setEchoMode(QLineEdit.Password)
        self.app_proxy_pass.setMaximumWidth(320)
        form.addWidget(self.app_proxy_pass)

        form.addSpacing(8)
        btns = QHBoxLayout()
        save_btn = AnimatedButton("Сохранить")
        save_btn.setObjectName("primary")
        save_btn.setFixedWidth(150)
        save_btn.clicked.connect(self._save_app_proxy)
        clear_btn = AnimatedButton("Отключить")
        clear_btn.setFixedWidth(150)
        clear_btn.clicked.connect(self._clear_app_proxy)
        btns.addWidget(save_btn)
        btns.addWidget(clear_btn)
        btns.addStretch()
        form.addLayout(btns)

        self.app_proxy_status_lbl = QLabel("Системный прокси: не задан")
        self.app_proxy_status_lbl.setStyleSheet("color: #4e5a78; font-size: 12px;")
        form.addWidget(self.app_proxy_status_lbl)

        form.addStretch()
        lay.addLayout(form)
        return w

    def _save_app_proxy(self):
        host = self.app_proxy_host.text().strip()
        port = self.app_proxy_port.text().strip()
        if not host or not port:
            QMessageBox.warning(self, "Ошибка", "Укажите хост и порт")
            return
        try:
            int(port)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом")
            return
        self.data["app_proxy"] = {
            "type": self.app_proxy_type.currentText(),
            "host": host,
            "port": int(port),
            "user": self.app_proxy_user.text().strip(),
            "password": self.app_proxy_pass.text().strip(),
        }
        save_data(self.data)
        self._refresh_app_proxy_status()

    def _clear_app_proxy(self):
        self.data["app_proxy"] = None
        save_data(self.data)
        self.app_proxy_host.clear()
        self.app_proxy_port.clear()
        self.app_proxy_user.clear()
        self.app_proxy_pass.clear()
        self._refresh_app_proxy_status()

    def _refresh_app_proxy_status(self):
        p = self.data.get("app_proxy")
        if p:
            self.app_proxy_status_lbl.setText(
                f"Системный прокси: {p['type'].upper()} {p['host']}:{p['port']}"
            )
            self.app_proxy_status_lbl.setStyleSheet("color: #6a9e80; font-size: 12px;")
            idx = self.app_proxy_type.findText(p["type"])
            if idx >= 0:
                self.app_proxy_type.setCurrentIndex(idx)
            self.app_proxy_host.setText(p["host"])
            self.app_proxy_port.setText(str(p["port"]))
            self.app_proxy_user.setText(p.get("user", ""))
            self.app_proxy_pass.setText(p.get("password", ""))
        else:
            self.app_proxy_status_lbl.setText("Системный прокси: не задан")
            self.app_proxy_status_lbl.setStyleSheet("color: #4e5a78; font-size: 12px;")

    def _refresh_proxies(self):
        self.proxy_list.clear()
        self._proxy_row_widgets = []
        active_idx = self.data.get("active_proxy_idx", -1)
        for i, p in enumerate(self.data.get("proxies", [])):
            row_widget = ProxyRowWidget(p, i)
            status = self._proxy_status.get(i, "")
            if status:
                row_widget.set_status(status)
            row_widget.set_active(i == active_idx)
            item = QListWidgetItem(self.proxy_list)
            item.setSizeHint(QSize(row_widget.sizeHint().width(), 42))
            self.proxy_list.addItem(item)
            self.proxy_list.setItemWidget(item, row_widget)
            self._proxy_row_widgets.append(row_widget)
        self._update_active_proxy_label()

    def _update_active_proxy_label(self):
        idx = self.data.get("active_proxy_idx", -1)
        proxies = self.data.get("proxies", [])
        if 0 <= idx < len(proxies):
            p = proxies[idx]
            self.active_proxy_lbl.setText(f"Активные: {p['type'].upper()} {p['host']}:{p['port']}")
        else:
            self.active_proxy_lbl.setText("Активные прокси: нет")

    def _add_proxy(self):
        host = self.proxy_host.text().strip()
        port = self.proxy_port.text().strip()
        if not host or not port:
            QMessageBox.warning(self, "Ошибка", "Укажите хост и порт")
            return
        try:
            int(port)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом")
            return
        proxy = {
            "type": self.proxy_type.currentText(),
            "host": host,
            "port": int(port),
            "user": self.proxy_user.text().strip(),
            "password": self.proxy_pass.text().strip(),
        }
        if "proxies" not in self.data:
            self.data["proxies"] = []
        self.data["proxies"].append(proxy)
        save_data(self.data)
        self._refresh_proxies()
        self.proxy_host.clear()
        self.proxy_port.clear()
        self.proxy_user.clear()
        self.proxy_pass.clear()



    def _del_proxy(self):
        row = self.proxy_list.currentRow()
        if row < 0:
            return
        self.data["proxies"].pop(row)
        active = self.data.get("active_proxy_idx", -1)
        if active == row:
            self.data["active_proxy_idx"] = -1
        elif active > row:
            self.data["active_proxy_idx"] = active - 1
        new_status = {}
        for k, v in self._proxy_status.items():
            if k < row:
                new_status[k] = v
            elif k > row:
                new_status[k - 1] = v
        self._proxy_status = new_status
        save_data(self.data)
        self._refresh_proxies()

    def _set_active_proxy(self):
        row = self.proxy_list.currentRow()
        if row < 0:
            return
        self.data["active_proxy_idx"] = row
        save_data(self.data)
        self._refresh_proxies()

    def _get_app_proxy(self):
        return self.data.get("app_proxy") or None

    def _get_active_proxy(self):
        idx = self.data.get("active_proxy_idx", -1)
        proxies = self.data.get("proxies", [])
        if 0 <= idx < len(proxies):
            return proxies[idx]
        return None

    def _check_all_proxies(self):
        proxies = self.data.get("proxies", [])
        if not proxies:
            QMessageBox.information(self, "Проверка", "Нет прокси для проверки")
            return
        for i in range(len(proxies)):
            self._proxy_status[i] = "checking"
            if i < len(self._proxy_row_widgets):
                self._proxy_row_widgets[i].set_status("checking")
        self._proxy_check_worker = ProxyCheckerWorker(proxies)
        self._proxy_check_worker.result_signal.connect(self._on_proxy_check_result)
        self._proxy_check_worker.finished_signal.connect(self._on_proxy_check_done)
        t = threading.Thread(target=self._proxy_check_worker.run, daemon=True)
        t.start()

    def _on_proxy_check_result(self, idx, ok, info):
        self._proxy_status[idx] = "ok" if ok else "err"
        if idx < len(self._proxy_row_widgets):
            self._proxy_row_widgets[idx].set_status("ok" if ok else "err", info)

    def _on_proxy_check_done(self):
        self._proxy_check_worker = None

    def _build_chats_page(self):
        w = self._mk_page()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 36, 36, 36)
        lay.setSpacing(14)

        hdr = QLabel("Чаты")
        hdr.setObjectName("header")
        lay.addWidget(hdr)
        sub = QLabel("Переписка с мамонтами")
        sub.setObjectName("subheader")
        lay.addWidget(sub)

        sep = QFrame()
        sep.setObjectName("separator")
        lay.addWidget(sep)

        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        lbl_acc = QLabel("АККАУНТ")
        lbl_acc.setObjectName("section")
        top_row.addWidget(lbl_acc)
        self.chat_acc_combo = styled_combo()
        self.chat_acc_combo.setMinimumWidth(260)
        self.chat_acc_combo.setFixedHeight(38)
        top_row.addWidget(self.chat_acc_combo)
        load_btn = AnimatedButton("Загрузить список")
        load_btn.clicked.connect(self._load_chat_contacts)
        top_row.addWidget(load_btn)
        top_row.addStretch()
        lay.addLayout(top_row)

        content = QHBoxLayout()
        content.setSpacing(16)

        contacts_col = QVBoxLayout()
        lbl_contacts = QLabel("ТЕГИ")
        lbl_contacts.setObjectName("section")
        contacts_col.addWidget(lbl_contacts)
        self.chat_contacts_list = QListWidget()
        self.chat_contacts_list.currentRowChanged.connect(self._open_chat)
        contacts_col.addWidget(self.chat_contacts_list)
        self.chat_status_lbl = QLabel("")
        self.chat_status_lbl.setStyleSheet("color: #4e5a78; font-size: 11px;")
        contacts_col.addWidget(self.chat_status_lbl)
        content.addLayout(contacts_col, 1)

        chat_col = QVBoxLayout()
        lbl_chat = QLabel("ПЕРЕПИСКА")
        lbl_chat.setObjectName("section")
        chat_col.addWidget(lbl_chat)
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setStyleSheet("""
            QTextEdit {
                background:
                border: 1px solid
                border-radius: 10px;
                padding: 12px 14px;
                font-size: 13px;
                color:
            }
        """)
        chat_col.addWidget(self.chat_view)
        content.addLayout(chat_col, 2)
        lay.addLayout(content)
        return w

    def _refresh_chats_accounts(self):
        self.chat_acc_combo.clear()
        for acc in self.data["accounts"]:
            name = acc.get("name", acc["phone"])
            self.chat_acc_combo.addItem(f"{name}  {acc['phone']}")

    def _load_chat_contacts(self):
        acc_idx = self.chat_acc_combo.currentIndex()
        if acc_idx < 0 or acc_idx >= len(self.data["accounts"]):
            QMessageBox.warning(self, "Ошибка", "Выберите аккаунт")
            return
        recipients = self.data.get("recipients", [])
        if not recipients:
            QMessageBox.warning(self, "Ошибка", "Нет тегов")
            return
        self.chat_contacts_list.clear()
        self.chat_view.clear()
        self.chat_status_lbl.setText("Загружено")
        chat_log = self.data.get("chat_log", {})
        for r in recipients:
            tag = recipient_tag(r)
            replied = chat_log.get(tag, {}).get("replied", False)
            suffix = "  [ответил]" if replied else ""
            self.chat_contacts_list.addItem(f"  {tag}{suffix}")

    def _open_chat(self, row):
        if row < 0:
            return
        acc_idx = self.chat_acc_combo.currentIndex()
        if acc_idx < 0 or acc_idx >= len(self.data["accounts"]):
            return
        acc = self.data["accounts"][acc_idx]
        recipients = self.data.get("recipients", [])
        if row >= len(recipients):
            return
        tag = recipient_tag(recipients[row])
        self.chat_view.setPlainText("Загружаем...")
        proxy = self._get_app_proxy()
        loader = ChatLoader(acc, tag, proxy=proxy)
        loader.messages_loaded.connect(self._on_chat_loaded)
        loader.error_signal.connect(self._on_chat_error)
        t = threading.Thread(target=loader.run, daemon=True)
        t.start()
        self._current_chat_loader = loader

    def _on_chat_loaded(self, tag, messages):
        self.chat_view.clear()
        if not messages:
            self.chat_view.setPlainText("Нет сообщений")
            return
        replied = any(not m["out"] for m in messages)
        chat_log = self.data.get("chat_log", {})
        if tag not in chat_log:
            chat_log[tag] = {}
        chat_log[tag]["replied"] = replied
        self.data["chat_log"] = chat_log
        save_data(self.data)
        html_parts = []
        for m in messages:
            if m["out"]:
                color = "#4a6fa5"
                align = "right"
                prefix = "Я"
            else:
                color = "#6a9e80"
                align = "left"
                prefix = tag
            text = m["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html_parts.append(
                f'<div style="text-align:{align}; margin:6px 0;">'
                f'<span style="color:#3a4a68; font-size:11px;">{prefix} {m["ts"]}</span><br>'
                f'<span style="color:{color};">{text}</span></div>'
            )
        self.chat_view.setHtml("".join(html_parts))
        self._refresh_chat_contacts_replied()

    def _on_chat_error(self, err):
        self.chat_view.setPlainText(f"Ошибка: {err}")

    def _refresh_chat_contacts_replied(self):
        chat_log = self.data.get("chat_log", {})
        recipients = self.data.get("recipients", [])
        self.chat_contacts_list.blockSignals(True)
        current = self.chat_contacts_list.currentRow()
        self.chat_contacts_list.clear()
        for r in recipients:
            tag = recipient_tag(r)
            replied = chat_log.get(tag, {}).get("replied", False)
            suffix = "  [ответил]" if replied else ""
            self.chat_contacts_list.addItem(f"  {tag}{suffix}")
        if 0 <= current < self.chat_contacts_list.count():
            self.chat_contacts_list.setCurrentRow(current)
        self.chat_contacts_list.blockSignals(False)

    def _build_sender_page(self):
        w = self._mk_page()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(36, 36, 36, 0)
        outer.setSpacing(0)

        hdr = QLabel("Отписи")
        hdr.setObjectName("header")
        outer.addWidget(hdr)
        outer.addSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(scroll_content)
        lay.setContentsMargins(0, 0, 12, 24)
        lay.setSpacing(16)

        self._worker_cards_widget = QWidget()
        self._worker_cards_widget.setStyleSheet("background: transparent;")
        self._worker_cards_layout = QVBoxLayout(self._worker_cards_widget)
        self._worker_cards_layout.setContentsMargins(0, 0, 0, 0)
        self._worker_cards_layout.setSpacing(12)
        lay.addWidget(self._worker_cards_widget)

        add_worker_btn = AnimatedButton("+ Добавить поток")
        add_worker_btn.setFixedWidth(200)
        add_worker_btn.clicked.connect(self._add_worker_card)
        lay.addWidget(add_worker_btn)
        lay.addSpacing(8)

        sep_s = QFrame()
        sep_s.setObjectName("separator")
        lay.addWidget(sep_s)
        lay.addSpacing(8)

        glob_card = QFrame()
        glob_card.setObjectName("card")
        glob_lay = QHBoxLayout(glob_card)
        glob_lay.setContentsMargins(20, 16, 20, 16)
        glob_lay.setSpacing(32)

        interval_col = QVBoxLayout()
        lbl_int = QLabel("ИНТЕРВАЛ СООБЩЕНИЙ (МИН)")
        lbl_int.setObjectName("section")
        interval_col.addWidget(lbl_int)
        interval_col.addSpacing(6)
        self.interval_spin = StyledSpinBox()
        self.interval_spin.setRange(0, 60)
        self.interval_spin.setValue(2)
        self.interval_spin.setSuffix(" мин")
        self.interval_spin.valueChanged.connect(self._update_eta)
        self.interval_spin.setFixedWidth(160)
        interval_col.addWidget(self.interval_spin)
        glob_lay.addLayout(interval_col)

        tag_interval_col = QVBoxLayout()
        lbl_tag_int = QLabel("ИНТЕРВАЛ МЕЖДУ ТЕГАМИ (МИН)")
        lbl_tag_int.setObjectName("section")
        tag_interval_col.addWidget(lbl_tag_int)
        tag_interval_col.addSpacing(6)
        self.tag_interval_spin = StyledSpinBox()
        self.tag_interval_spin.setRange(0, 1440)
        self.tag_interval_spin.setValue(self.data.get("tag_interval_min", 0))
        self.tag_interval_spin.setSuffix(" мин")
        self.tag_interval_spin.setFixedWidth(160)
        hint_tag = QLabel("0 = без интервала")
        hint_tag.setStyleSheet("color: #3a4a68; font-size: 11px; background: transparent;")
        tag_interval_col.addWidget(self.tag_interval_spin)
        tag_interval_col.addWidget(hint_tag)
        glob_lay.addLayout(tag_interval_col)

        time_col = QVBoxLayout()
        lbl_time = QLabel("ВРЕМЯ СТАРТА")
        lbl_time.setObjectName("section")
        time_col.addWidget(lbl_time)
        time_col.addSpacing(6)
        self.start_time_edit = StyledTimeEdit()
        self.start_time_edit.setTime(QTime.currentTime())
        self.start_time_edit.setFixedWidth(160)
        time_col.addWidget(self.start_time_edit)
        glob_lay.addLayout(time_col)

        eta_col = QVBoxLayout()
        self.eta_lbl = QLabel("")
        self.eta_lbl.setStyleSheet("color: #4a5878; font-size: 12px; background: transparent;")
        self.eta_lbl.setWordWrap(True)
        eta_col.addStretch()
        eta_col.addWidget(self.eta_lbl)
        glob_lay.addLayout(eta_col)
        glob_lay.addStretch()
        lay.addWidget(glob_card)

        stats_outer = QFrame()
        stats_outer.setObjectName("card")
        stats_grid = QGridLayout(stats_outer)
        stats_grid.setContentsMargins(16, 16, 16, 16)
        stats_grid.setSpacing(12)
        for i in range(4):
            stats_grid.setColumnStretch(i, 1)
        self.stat_total = StatCard("ВСЕГО")
        self.stat_ok = StatCard("ОТПРАВЛЕНО")
        self.stat_err = StatCard("ОШИБОК")
        self.stat_left = StatCard("ОСТАЛОСЬ")
        stats_grid.addWidget(self.stat_total, 0, 0)
        stats_grid.addWidget(self.stat_ok, 0, 1)
        stats_grid.addWidget(self.stat_err, 0, 2)
        stats_grid.addWidget(self.stat_left, 0, 3)
        lay.addWidget(stats_outer)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_card_lay = QVBoxLayout(log_card)
        log_card_lay.setContentsMargins(16, 14, 16, 14)
        log_card_lay.setSpacing(8)
        lbl_log = QLabel("СТАТУС")
        lbl_log.setObjectName("section")
        log_card_lay.addWidget(lbl_log)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(220)
        self.log_view.setStyleSheet("""
            QTextEdit {
                background:
                border: 1px solid
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 12px;
                color:
            }
        """)
        log_card_lay.addWidget(self.log_view)
        lay.addWidget(log_card)

        scroll.setWidget(scroll_content)
        outer.addWidget(scroll)
        return w

    def _add_worker_card(self):
        card_idx = len(self._worker_cards)
        self._build_worker_card(card_idx)
        self._update_eta()

    def _build_worker_card(self, idx):
        card = QFrame()
        card.setObjectName("card")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 16, 20, 16)
        card_lay.setSpacing(10)

        title_row = QHBoxLayout()
        title_lbl = QLabel(f"ПОТОК {idx + 1}")
        title_lbl.setStyleSheet("background: transparent; font-size: 10px; font-weight: 700; color: #6b82c0; letter-spacing: 1.8px;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        if idx > 0:
            rm_btn = AnimatedButton("Удалить")
            rm_btn.setFixedHeight(28)
            rm_btn.setFixedWidth(90)
            rm_btn.clicked.connect(lambda checked, i=idx: self._remove_worker_card(i))
            title_row.addWidget(rm_btn)
        card_lay.addLayout(title_row)

        row1 = QHBoxLayout()
        row1.setSpacing(16)

        acc_col = QVBoxLayout()
        acc_col.setSpacing(6)
        lbl_a = QLabel("АККАУНТ")
        lbl_a.setStyleSheet("background: transparent; font-size: 10px; font-weight: 700; color: #6b82c0; letter-spacing: 1.8px;")
        acc_col.addWidget(lbl_a)
        acc_combo = styled_combo()
        acc_combo.setFixedHeight(38)
        for acc in self.data["accounts"]:
            name = acc.get("name", acc["phone"])
            un = f"@{acc['username']}" if acc.get("username") else ""
            acc_combo.addItem(f"{name}  {un}  {acc['phone']}")
        acc_col.addWidget(acc_combo)
        row1.addLayout(acc_col, 2)

        proxy_col = QVBoxLayout()
        proxy_col.setSpacing(6)
        lbl_p = QLabel("ПРОКСИ")
        lbl_p.setStyleSheet("background: transparent; font-size: 10px; font-weight: 700; color: #6b82c0; letter-spacing: 1.8px;")
        proxy_col.addWidget(lbl_p)
        proxy_combo = styled_combo()
        proxy_combo.setFixedHeight(38)
        proxy_combo.addItem("Без прокси")
        for p in self.data.get("proxies", []):
            proxy_combo.addItem(f"{p['type'].upper()}  {p['host']}:{p['port']}")
        proxy_col.addWidget(proxy_combo)
        row1.addLayout(proxy_col, 2)

        rec_col = QVBoxLayout()
        rec_col.setSpacing(6)
        lbl_r = QLabel("ТЕГИ (БАЗА)")
        lbl_r.setStyleSheet("background: transparent; font-size: 10px; font-weight: 700; color: #6b82c0; letter-spacing: 1.8px;")
        rec_col.addWidget(lbl_r)
        rec_combo = styled_combo()
        rec_combo.setFixedHeight(38)
        rec_combo.addItem("База")
        for key in self.data.get("recipient_dbs", {}):
            rec_combo.addItem(key)
        rec_col.addWidget(rec_combo)
        row1.addLayout(rec_col, 2)

        card_lay.addLayout(row1)
        card_lay.addSpacing(12)

        pastes_col = QVBoxLayout()
        pastes_col.setSpacing(6)
        lbl_ps = QLabel("ПАСТЫ")
        lbl_ps.setStyleSheet("background: transparent; font-size: 10px; font-weight: 700; color: #6b82c0; letter-spacing: 1.8px;")
        pastes_col.addWidget(lbl_ps)
        paste_list_w = QListWidget()
        paste_list_w.setSelectionMode(QAbstractItemView.NoSelection)
        paste_list_w.setMinimumHeight(160)
        paste_list_w.setMaximumHeight(300)
        paste_list_w.setMinimumWidth(220)
        paste_list_w.setStyleSheet("""
            QListWidget {
                background:
                border: 1px solid
                border-radius: 8px;
                outline: none;
                padding: 4px;
                color:
            }
            QListWidget::item {
                border-radius: 6px;
                padding: 5px 10px;
                margin: 1px 2px;
                color:
                background: transparent;
            }
            QListWidget::item:hover { background:
            QListWidget::indicator {
                width: 13px;
                height: 13px;
                border: 1px solid
                border-radius: 3px;
                background:
            }
            QListWidget::indicator:checked {
                background:
                border-color:
            }
        """)
        for i, p in enumerate(self.data["pastes"]):
            if not p.strip():
                continue
            preview = p[:40].replace("\n", " ")
            item = QListWidgetItem(f"  {i+1}.  {preview}")
            item.setData(Qt.UserRole, i)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            paste_list_w.addItem(item)
        paste_list_w.itemClicked.connect(lambda it: it.setCheckState(
            Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked
        ))
        pastes_col.addWidget(paste_list_w)
        card_lay.addLayout(pastes_col)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        start_btn = AnimatedButton(f"Запустить поток {idx + 1}")
        start_btn.setMinimumHeight(36)
        start_btn.setFixedWidth(220)
        start_btn.clicked.connect(lambda checked, i=idx: self._toggle_worker(i))
        btn_row.addWidget(start_btn)

        pause_btn = AnimatedButton("Пауза")
        pause_btn.setMinimumHeight(36)
        pause_btn.setFixedWidth(110)
        pause_btn.setEnabled(False)
        pause_btn.clicked.connect(lambda checked, i=idx: self._toggle_worker_pause(i))
        btn_row.addWidget(pause_btn)

        current_tag_lbl = QLabel("")
        current_tag_lbl.setStyleSheet("color: #6b82c0; font-size: 12px; background: transparent;")
        btn_row.addWidget(current_tag_lbl)
        btn_row.addStretch()

        card_lay.addLayout(btn_row)

        self._worker_cards_layout.addWidget(card)
        self._worker_cards.append({
            "card": card,
            "acc_combo": acc_combo,
            "proxy_combo": proxy_combo,
            "paste_list": paste_list_w,
            "rec_combo": rec_combo,
            "start_btn": start_btn,
            "pause_btn": pause_btn,
            "current_tag_lbl": current_tag_lbl,
            "recipients": None,
        })

    def _refresh_all_worker_rec_combos(self):
        for card_data in self._worker_cards:
            combo = card_data["rec_combo"]
            cur = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("База")
            for key in self.data.get("recipient_dbs", {}):
                combo.addItem(key)
            idx2 = combo.findText(cur)
            combo.setCurrentIndex(max(0, idx2))
            combo.blockSignals(False)

    def _remove_worker_card(self, idx):
        if idx >= len(self._worker_cards):
            return
        if idx in self._workers and self._workers[idx] is not None:
            self._workers[idx].stop()
        card_data = self._worker_cards[idx]
        card_data["card"].setParent(None)
        card_data["card"].deleteLater()
        self._worker_cards.pop(idx)

    def _get_worker_selected_pastes(self, idx):
        if idx >= len(self._worker_cards):
            return []
        paste_list_w = self._worker_cards[idx]["paste_list"]
        selected = []
        for i in range(paste_list_w.count()):
            item = paste_list_w.item(i)
            if item.checkState() == Qt.Checked:
                data_idx = item.data(Qt.UserRole)
                if 0 <= data_idx < len(self.data["pastes"]):
                    selected.append(self.data["pastes"][data_idx])
        return selected

    def _toggle_worker(self, idx):
        if idx in self._workers and self._workers[idx] is not None:
            self._stop_worker(idx)
        else:
            self._start_worker(idx)

    def _start_worker(self, idx):
        if idx >= len(self._worker_cards):
            return
        card_data = self._worker_cards[idx]
        acc_idx = card_data["acc_combo"].currentIndex()
        if acc_idx < 0 or acc_idx >= len(self.data["accounts"]):
            QMessageBox.warning(self, "Ошибка", "Выберите аккаунт")
            return
        selected_pastes = self._get_worker_selected_pastes(idx)
        if not selected_pastes:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одну пасту")
            return
        rec_combo = card_data["rec_combo"]
        if rec_combo.currentIndex() == 0:
            recipients = self.data.get("recipients", [])
        else:
            key = rec_combo.currentText()
            recipients = self.data.get("recipient_dbs", {}).get(key, self.data.get("recipients", []))
        if not recipients:
            QMessageBox.warning(self, "Ошибка", "Нет тегов")
            return
        account = self.data["accounts"][acc_idx]
        proxy_idx = card_data["proxy_combo"].currentIndex()
        proxy = None
        if proxy_idx > 0:
            actual_idx = proxy_idx - 1
            proxies = self.data.get("proxies", [])
            if actual_idx < len(proxies):
                proxy = proxies[actual_idx]

        interval_min = self.interval_spin.value()
        tag_interval_min = self.tag_interval_spin.value()

        worker = SenderWorker(
            account, recipients, selected_pastes,
            interval_min, len(selected_pastes),
            proxy=proxy,
            tag_interval_min=tag_interval_min,
            worker_id=idx,
        )
        worker.log_signal.connect(self._on_log)
        worker.progress_signal.connect(lambda d, t, i=idx: self._on_worker_progress(i, d, t))
        worker.finished_signal.connect(lambda i=idx: self._on_worker_finished(i))
        worker.failed_signal.connect(self._on_failed)
        worker.failed_detail_signal.connect(self._on_failed_detail)
        worker.current_tag_signal.connect(self._on_worker_current_tag)
        worker.spamblock_signal.connect(self._on_spamblock)
        worker.current_tag_signal.connect(lambda wid, t: self._store_last_tag(wid, t))

        self._workers[idx] = worker
        self._total_messages = sum(
            len(self._worker_cards[i]["recipients"] or []) * len(self._get_worker_selected_pastes(i))
            for i in range(len(self._worker_cards))
            if i in self._workers and self._workers.get(i) is not None
        ) + len(recipients) * len(selected_pastes)
        self._worker_totals[idx] = len(recipients) * len(selected_pastes)
        self.stat_total.set_value(self._total_messages)
        self.stat_left.set_value(self._total_messages - self._done_messages)
        self.progress_bar.setMaximum(self._total_messages)
        self.progress_bar.show()
        self._pause_btn.show()

        t = threading.Thread(target=worker.run, daemon=True)
        self._worker_threads[idx] = t
        t.start()

        card_data["start_btn"].setText(f"Остановить поток {idx + 1}")
        card_data["pause_btn"].setEnabled(True)
        card_data["pause_btn"].setText("Пауза")
        card_data["current_tag_lbl"].setText("")
        self._worker_paused[idx] = False
        proxy_info = f"  прокси: {proxy['type'].upper()} {proxy['host']}:{proxy['port']}" if proxy else ""
        self._on_log(
            f"[W{idx+1}] Запущен  {len(recipients)} тегов  {len(selected_pastes)} past{proxy_info}",
            "info"
        )

    def _stop_worker(self, idx):
        if idx in self._workers and self._workers[idx]:
            self._workers[idx].stop()
            self._workers[idx] = None
        self._worker_paused[idx] = False
        if idx < len(self._worker_cards):
            self._worker_cards[idx]["start_btn"].setText(f"Запустить поток {idx + 1}")
            self._worker_cards[idx]["pause_btn"].setEnabled(False)
            self._worker_cards[idx]["pause_btn"].setText("Пауза")
            self._worker_cards[idx]["current_tag_lbl"].setText("")
        self._on_log(f"[W{idx+1}] Остановлен", "warn")

    def _toggle_worker_pause(self, idx):
        if idx not in self._workers or self._workers[idx] is None:
            return
        is_paused = self._worker_paused.get(idx, False)
        if is_paused:
            self._workers[idx].resume()
            self._worker_paused[idx] = False
            if idx < len(self._worker_cards):
                self._worker_cards[idx]["pause_btn"].setText("Пауза")
            self._on_log(f"[W{idx+1}] Возобновлён", "info")
        else:
            self._workers[idx].pause()
            self._worker_paused[idx] = True
            if idx < len(self._worker_cards):
                self._worker_cards[idx]["pause_btn"].setText("Продолжить")
            self._on_log(f"[W{idx+1}] На паузе", "warn")

    def _on_worker_current_tag(self, worker_id, tag):
        if worker_id < len(self._worker_cards):
            lbl = self._worker_cards[worker_id].get("current_tag_lbl")
            if lbl:
                lbl.setText(f"→ {tag}")

    def _on_worker_progress(self, worker_idx, done_delta, total_delta):
        self._done_messages = sum(
            getattr(w, '_done', 0) for w in self._workers.values() if w is not None
        )
        total = sum(self._worker_totals.values()) if self._worker_totals else self._total_messages
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(self._done_messages)
        self._on_progress(self._done_messages, total)

    def _on_worker_finished(self, idx):
        if idx in self._workers:
            self._workers[idx] = None
        self._worker_paused[idx] = False
        if idx < len(self._worker_cards):
            self._worker_cards[idx]["start_btn"].setText(f"Запустить поток {idx + 1}")
            self._worker_cards[idx]["pause_btn"].setEnabled(False)
            self._worker_cards[idx]["pause_btn"].setText("Пауза")
            self._worker_cards[idx]["current_tag_lbl"].setText("")
        self._on_log(f"[W{idx+1}] Завершён", "ok")
        any_running = any(w is not None for w in self._workers.values())
        if any_running:
            self._run_btn.setText("Остановить все")
        else:
            self._run_btn.setText("Начать отписи")
            self.progress_bar.hide()
            self._pause_btn.hide()
            self._on_finished_all()

    def _store_last_tag(self, worker_id, tag):
        if not hasattr(self, "_last_tags"):
            self._last_tags = {}
        self._last_tags[worker_id] = tag

    def _get_acc_for_worker(self, worker_id):
        if worker_id < len(self._worker_cards):
            idx = self._worker_cards[worker_id]["acc_combo"].currentIndex()
            if 0 <= idx < len(self.data["accounts"]):
                return self.data["accounts"][idx]
        return None

    def _on_spamblock(self, worker_id, stopped_at_tag, spambot_reply, spambot_buttons):
        acc = self._get_acc_for_worker(worker_id)
        acc_name = acc.get("name", acc["phone"]) if acc else f"Поток {worker_id+1}"

        entry = {
            "worker_id": worker_id,
            "acc_name": acc_name,
            "acc": acc,
            "stopped_at": stopped_at_tag,
            "reply": spambot_reply,
            "buttons": spambot_buttons,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
        if not hasattr(self, "_spamblock_log"):
            self._spamblock_log = []
        self._spamblock_log.append(entry)

        self._switch_tab(7)
        self._refresh_spamblock_page()

    def _refresh_spamblock_page(self):
        if not hasattr(self, "_spam_list_widget"):
            return
        self._spam_list_widget.clear()
        for e in getattr(self, "_spamblock_log", []):
            low = (e["reply"] or "").lower()
            freed = any(w in low for w in ("free", "no limits", "свободен", "ограничений", "bird"))
            status = "СНЯТ" if freed else "БЛОК"
            color = "#6a9e80" if freed else "#b06070"
            item = QListWidgetItem(f"  [{e['time']}]  {e['acc_name']}  -  {e['stopped_at']}  [{status}]")
            item.setForeground(QColor(color))
            item.setData(Qt.UserRole, e)
            self._spam_list_widget.addItem(item)

    def _build_spamblock_page(self):
        w = self._mk_page()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 36, 36, 36)
        lay.setSpacing(14)

        hdr = QLabel("Спамблок")
        hdr.setObjectName("header")
        lay.addWidget(hdr)
        sub = QLabel("Аккаунты словившие PeerFlood - статус и ручное управление Spam info bot")
        sub.setObjectName("subheader")
        lay.addWidget(sub)

        sep = QFrame()
        sep.setObjectName("separator")
        lay.addWidget(sep)

        content = QHBoxLayout()
        content.setSpacing(20)

        left = QVBoxLayout()
        lbl_l = QLabel("АККАУНТЫ")
        lbl_l.setObjectName("section")
        left.addWidget(lbl_l)

        self._spam_list_widget = QListWidget()
        self._spam_list_widget.currentRowChanged.connect(self._on_spamblock_selected)
        left.addWidget(self._spam_list_widget)

        clear_btn = AnimatedButton("Очистить")
        clear_btn.clicked.connect(self._clear_spamblock_log)
        left.addWidget(clear_btn)
        content.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(10)

        lbl_r = QLabel("ОТВЕТ SPAMBOT")
        lbl_r.setObjectName("section")
        right.addWidget(lbl_r)

        self._spam_reply_lbl = QTextEdit()
        self._spam_reply_lbl.setReadOnly(True)
        self._spam_reply_lbl.setMaximumHeight(120)
        self._spam_reply_lbl.setStyleSheet("""
            QTextEdit {
                background:
                border: 1px solid
                border-radius: 8px;
                padding: 10px;
                color:
                font-size: 13px;
            }
        """)
        right.addWidget(self._spam_reply_lbl)

        lbl_info = QLabel("ОСТАНОВЛЕН НА ТЕГЕ")
        lbl_info.setObjectName("section")
        right.addWidget(lbl_info)
        self._spam_tag_lbl = QLabel("")
        self._spam_tag_lbl.setStyleSheet("color: #a8b8d8; font-size: 13px;")
        right.addWidget(self._spam_tag_lbl)

        lbl_btns = QLabel("ВАРИАНТЫ ОТВЕТА SPAMBOT")
        lbl_btns.setObjectName("section")
        right.addWidget(lbl_btns)

        self._spam_btns_frame = QFrame()
        self._spam_btns_frame.setObjectName("card")
        self._spam_btns_frame.setMinimumHeight(80)
        spam_btns_lay = QVBoxLayout(self._spam_btns_frame)
        spam_btns_lay.setContentsMargins(16, 16, 16, 16)
        spam_btns_lay.setSpacing(10)
        self._spam_btns_layout = spam_btns_lay
        right.addWidget(self._spam_btns_frame)

        right.addSpacing(8)
        manual_row = QHBoxLayout()
        self._spam_manual_edit = QLineEdit()
        self._spam_manual_edit.setPlaceholderText("Ввести вручную и отправить...")
        manual_row.addWidget(self._spam_manual_edit)
        send_manual_btn = AnimatedButton("Отправить")
        send_manual_btn.setFixedWidth(110)
        send_manual_btn.clicked.connect(self._send_spambot_manual)
        manual_row.addWidget(send_manual_btn)
        right.addLayout(manual_row)

        right.addSpacing(8)
        start_btn = AnimatedButton("Отправить /start")
        start_btn.clicked.connect(self._send_spambot_start)
        right.addWidget(start_btn)

        right.addStretch()
        content.addLayout(right, 2)
        lay.addLayout(content)
        return w

    def _on_spamblock_selected(self, row):
        entries = getattr(self, "_spamblock_log", [])
        if row < 0 or row >= len(entries):
            return
        e = entries[row]
        self._spam_reply_lbl.setPlainText(e.get("reply", ""))
        self._spam_tag_lbl.setText(e.get("stopped_at", ""))
        for i in reversed(range(self._spam_btns_layout.count())):
            w = self._spam_btns_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        for btn_text in e.get("buttons", []):
            b = AnimatedButton(btn_text)
            b.setMinimumHeight(44)
            b.setStyleSheet(b.styleSheet() + "font-size: 14px; font-weight: 600;")
            b.clicked.connect(lambda _, t=btn_text, en=e: self._send_spambot_reply(t, en))
            self._spam_btns_layout.addWidget(b)
        if not e.get("buttons"):
            no_btn = QLabel("Нет кнопок от Spam info bot")
            no_btn.setStyleSheet("color: #4e5a78; font-size: 12px;")
            self._spam_btns_layout.addWidget(no_btn)

    def _send_spambot_reply(self, text, entry):
        acc = entry.get("acc")
        if not acc:
            return
        proxy = self._get_app_proxy()
        self._do_spambot_send(acc, text, proxy)

    def _send_spambot_manual(self):
        text = self._spam_manual_edit.text().strip()
        if not text:
            return
        row = self._spam_list_widget.currentRow()
        entries = getattr(self, "_spamblock_log", [])
        if row < 0 or row >= len(entries):
            return
        acc = entries[row].get("acc")
        if not acc:
            return
        proxy = self._get_app_proxy()
        self._do_spambot_send(acc, text, proxy)
        self._spam_manual_edit.clear()

    def _send_spambot_start(self):
        row = self._spam_list_widget.currentRow()
        entries = getattr(self, "_spamblock_log", [])
        if row < 0 or row >= len(entries):
            return
        acc = entries[row].get("acc")
        if not acc:
            return
        proxy = self._get_app_proxy()
        self._do_spambot_send(acc, "/start", proxy)

    def _do_spambot_send(self, acc, text, proxy):
        def _run():
            loop = asyncio.new_event_loop()
            async def _inner():
                try:
                    client = build_client(acc, proxy)
                    await client.connect()
                    await client.send_message("Spam_info_bot", text)
                    await asyncio.sleep(3)
                    reply = ""
                    btns = []
                    async for m in client.iter_messages("Spam_info_bot", limit=3):
                        if m.message and not reply:
                            reply = m.message
                        if m.reply_markup:
                            try:
                                for row2 in m.reply_markup.rows:
                                    for b in row2.buttons:
                                        if hasattr(b, "text"):
                                            btns.append(b.text)
                            except Exception:
                                pass
                        break
                    await client.disconnect()
                    name = acc.get("name", acc["phone"])
                    self._on_log(f"Spam info bot [{name}] -> {text}: {reply[:120]}", "info")
                    row = self._spam_list_widget.currentRow()
                    entries = getattr(self, "_spamblock_log", [])
                    if 0 <= row < len(entries):
                        entries[row]["reply"] = reply
                        entries[row]["buttons"] = btns
                        QTimer.singleShot(0, lambda: self._on_spamblock_selected(row))
                        QTimer.singleShot(0, self._refresh_spamblock_page)
                except Exception as ex:
                    self._on_log(f"Spam info bot ошибка: {ex}", "err")
            loop.run_until_complete(_inner())
        threading.Thread(target=_run, daemon=True).start()

    def _clear_spamblock_log(self):
        self._spamblock_log = []
        self._refresh_spamblock_page()
        self._spam_reply_lbl.setPlainText("")
        self._spam_tag_lbl.setText("")

    def _on_finished_all(self):
        if self._failed_recipients:
            out = (APP_DIR / "failed_recipients.txt").resolve()
            out.write_text("\n".join(self._failed_recipients), encoding="utf-8")
            self._on_log(f"Неудачных: {len(self._failed_recipients)}, сохранено в {out}", "warn")
        self._on_log("Все потоки завершены", "ok")
        self._total_messages = 0
        self._done_messages = 0

    def _refresh_sender_page(self):
        if not self._worker_cards:
            self._build_worker_card(0)
        else:
            for card_data in self._worker_cards:
                old_acc = card_data["acc_combo"].currentIndex()
                card_data["acc_combo"].clear()
                for acc in self.data["accounts"]:
                    name = acc.get("name", acc["phone"])
                    un = f"@{acc['username']}" if acc.get("username") else ""
                    card_data["acc_combo"].addItem(f"{name}  {un}  {acc['phone']}")
                if old_acc < card_data["acc_combo"].count():
                    card_data["acc_combo"].setCurrentIndex(old_acc)
                old_proxy = card_data["proxy_combo"].currentIndex()
                card_data["proxy_combo"].clear()
                card_data["proxy_combo"].addItem("Без прокси")
                for p in self.data.get("proxies", []):
                    card_data["proxy_combo"].addItem(f"{p['type'].upper()}  {p['host']}:{p['port']}")
                if old_proxy < card_data["proxy_combo"].count():
                    card_data["proxy_combo"].setCurrentIndex(old_proxy)
                pw = card_data["paste_list"]
                checked_idxs = set()
                for i in range(pw.count()):
                    it = pw.item(i)
                    if it.checkState() == Qt.Checked:
                        checked_idxs.add(it.data(Qt.UserRole))
                pw.clear()
                for i, p in enumerate(self.data["pastes"]):
                    if not p.strip():
                        continue
                    preview = p[:40].replace("\n", " ")
                    item = QListWidgetItem(f"  {i+1}.  {preview}")
                    item.setData(Qt.UserRole, i)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked if (i in checked_idxs or not checked_idxs) else Qt.Unchecked)
                    pw.addItem(item)
        self._update_eta()

    def _update_eta(self):
        if not self._worker_cards:
            self.eta_lbl.setText("")
            return
        total = 0
        for idx, card_data in enumerate(self._worker_cards):
            pastes = self._get_worker_selected_pastes(idx)
            rec_combo = card_data["rec_combo"]
            if rec_combo.currentIndex() == 0:
                recs = self.data.get("recipients", [])
            else:
                key = rec_combo.currentText()
                recs = self.data.get("recipient_dbs", {}).get(key, self.data.get("recipients", []))
            total += len(recs) * len(pastes)
        if total == 0:
            self.eta_lbl.setText("")
            return
        interval_min = self.interval_spin.value()
        done = getattr(self, "_done_messages", 0)
        remaining = max(0, total - done)
        remaining_min = remaining * interval_min
        end_dt = datetime.now() + timedelta(minutes=remaining_min)
        self.eta_lbl.setText(f"Конец ~{end_dt.strftime('%H:%M')}  {total} сообщений")

    def _toggle_send(self):
        any_running = any(w is not None for w in self._workers.values())
        if any_running:
            for idx in list(self._workers.keys()):
                self._stop_worker(idx)
            self._run_btn.setText("Начать отписи")
        else:
            for idx in range(len(self._worker_cards)):
                self._start_worker(idx)
            if any(w is not None for w in self._workers.values()):
                self._run_btn.setText("Остановить все")

    def _toggle_pause(self):
        if self._paused:
            for w in self._workers.values():
                if w:
                    w.resume()
            self._paused = False
            self._pause_btn.setText("Пауза")
            self._on_log("Возобновлена", "info")
        else:
            for w in self._workers.values():
                if w:
                    w.pause()
            self._paused = True
            self._pause_btn.setText("Продолжить")
            self._on_log("На паузе", "warn")

    def _on_failed(self, recipient):
        if recipient not in self._failed_recipients:
            self._failed_recipients.append(recipient)

    def _on_log(self, message, level):
        colors = {"ok": "#6a9e80", "err": "#b06070", "warn": "#a08858", "info": "#5878a8"}
        color = colors.get(level, "#5a6a88")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(
            f'<span style="color:#2e3a52">[{ts}]</span> '
            f'<span style="color:{color}">{message}</span>'
        )
        if level == "ok":
            self._ok_count += 1
            self.stat_ok.set_value(self._ok_count)
        elif level == "err":
            self._err_count += 1
            self.stat_err.set_value(self._err_count)

    def _on_progress(self, current, total):
        if total > 0:
            self._done_messages = current
            self.progress_bar.setValue(current)
            self.stat_left.set_value(max(0, total - current))
            self._update_eta()

    def _build_logs_page(self):
        w = self._mk_page()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 36, 36, 36)
        lay.setSpacing(14)

        hdr = QLabel("Логи")
        hdr.setObjectName("header")
        lay.addWidget(hdr)

        sep = QFrame()
        sep.setObjectName("separator")
        lay.addWidget(sep)

        content = QHBoxLayout()
        content.setSpacing(24)

        left = QVBoxLayout()
        lbl_tags = QLabel("ТЕГИ БЕЗ ОТВЕТА")
        lbl_tags.setObjectName("section")
        left.addWidget(lbl_tags)
        self._failed_tags_view = QTextEdit()
        self._failed_tags_view.setReadOnly(True)
        self._failed_tags_view.setStyleSheet("""
            QTextEdit {
                background:
                border: 1px solid
                border-radius: 10px;
                padding: 12px 14px;
                font-size: 13px;
                color:
            }
        """)
        left.addWidget(self._failed_tags_view)
        content.addLayout(left, 1)

        right = QVBoxLayout()
        lbl_reasons = QLabel("ПРИЧИНЫ")
        lbl_reasons.setObjectName("section")
        right.addWidget(lbl_reasons)
        self._failed_reasons_view = QTextEdit()
        self._failed_reasons_view.setReadOnly(True)
        self._failed_reasons_view.setStyleSheet("""
            QTextEdit {
                background:
                border: 1px solid
                border-radius: 10px;
                padding: 12px 14px;
                font-size: 13px;
                color:
            }
        """)
        right.addWidget(self._failed_reasons_view)
        content.addLayout(right, 1)
        lay.addLayout(content)

        clear_btn = AnimatedButton("Очистить")
        clear_btn.clicked.connect(self._clear_logs)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(clear_btn)
        lay.addLayout(btn_row)
        return w

    def _clear_logs(self):
        self._failed_entries = []
        self._failed_tags_view.clear()
        self._failed_reasons_view.clear()

    def _on_failed_detail(self, recipient, reason):
        if recipient not in [e[0] for e in self._failed_entries]:
            self._failed_entries.append((recipient, reason))
        self._refresh_logs()

    def _refresh_logs(self):
        entries = getattr(self, "_failed_entries", [])
        tags_text = "\n".join(f"{i+1}  {rec}" for i, (rec, _) in enumerate(entries))
        reasons_text = "\n".join(f"{i+1}  {rec}  {reason}" for i, (rec, reason) in enumerate(entries))
        self._failed_tags_view.setPlainText(tags_text)
        self._failed_reasons_view.setPlainText(reasons_text)


_pending_update_version = None


def check_for_update(parent_widget=None):
    global _pending_update_version
    try:
        with urllib.request.urlopen(GITHUB_VERSION_URL, timeout=8) as r:
            latest = r.read().decode().strip()
        if latest.strip() == APP_VERSION.strip():
            return
        _pending_update_version = latest
    except Exception:
        pass


def _show_update_dialog(parent_widget=None):
    latest = _pending_update_version
    if not latest:
        return
    msg = QMessageBox(parent_widget)
    msg.setWindowTitle("Доступно обновление")
    msg.setText(f"Новая версия: {latest}\nТекущая: {APP_VERSION}\n\nОбновить сейчас?")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setStyleSheet(STYLE)
    if msg.exec_() == QMessageBox.Yes:
        _do_update(parent_widget)


def _do_update(parent_widget=None):
    try:
        with urllib.request.urlopen(GITHUB_RAW_URL, timeout=30) as r:
            new_code = r.read()

        is_frozen = getattr(sys, "frozen", False)

        if is_frozen:
            current_exe = Path(sys.executable).resolve()
            current_dir = current_exe.parent

            lagos_py = current_dir / "Lagos.py"
            lagos_py.write_bytes(new_code)

            try:
                current_exe.unlink()
            except Exception:
                pass

            QMessageBox.information(
                parent_widget,
                "Обновление загружено",
                "Lagos.py обновлён!\n\n"
                "Запусти install.bat чтобы пересобрать приложение."
            )
            sys.exit(0)

        else:
            current = Path(sys.argv[0]).resolve()
            backup = current.with_suffix(".bak")
            backup.write_bytes(current.read_bytes())
            current.write_bytes(new_code)
            subprocess.Popen([sys.executable, str(current)])
            sys.exit(0)

    except Exception as e:
        QMessageBox.critical(parent_widget, "Ошибка обновления", str(e))


def resource_path(name):
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return str(Path(base) / name)


if __name__ == "__main__":
    import traceback

    def _excepthook(exc_type, exc_value, exc_tb):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(msg, file=sys.stderr)
        try:
            (APP_DIR / "crash.log").write_text(msg, encoding="utf-8")
        except Exception:
            pass
        try:
            QMessageBox.critical(None, "Ошибка", msg)
        except Exception:
            pass

    sys.excepthook = _excepthook

    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        icon_file = resource_path("icon.ico")
        if Path(icon_file).exists():
            app.setWindowIcon(QIcon(icon_file))
        win = MainWindow()
        if Path(icon_file).exists():
            win.setWindowIcon(QIcon(icon_file))
        win.show()
        def _poll_update():
            if _pending_update_version:
                _show_update_dialog(win)
            else:
                QTimer.singleShot(2000, _poll_update)

        threading.Thread(target=check_for_update, daemon=True).start()
        QTimer.singleShot(3000, _poll_update)
        sys.exit(app.exec_())
    except Exception:
        traceback.print_exc()
        try:
            (APP_DIR / "crash.log").write_text(traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
