from PyQt5.QtWidgets import (
    QWidget, QFrame, QPushButton, QListWidget, QListWidgetItem,
    QProgressBar, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QComboBox, QSize
)
from PyQt5.QtCore import (
    Qt, QTimer, QTime, QPropertyAnimation, QParallelAnimationGroup,
    QEasingCurve, pyqtSignal, pyqtProperty, QRect, QPointF, QObject
)
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QPen, QFont, QIcon
)

from theme import (
    ANIM_FAST, ANIM_NORMAL, ANIM_SLOW, SIDEBAR_OFFSET,
    SPINBOX_HEIGHT, ARROW_BTN_W, ARROW_BTN_H,
    ARROW_BTN_STYLE, COMBO_VIEW_STYLE,
    C_BORDER, C_ACCENT,
)


def styled_combo():
    cb = QComboBox()
    cb.view().setStyleSheet(COMBO_VIEW_STYLE)
    return cb


def make_sep():
    f = QFrame()
    f.setObjectName("separator")
    return f


def section_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("section")
    return lbl


class ArrowInput(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._edit = QLineEdit()
        self._edit.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._edit.editingFinished.connect(self._on_edit)
        lay.addWidget(self._edit)

        btn_col = QVBoxLayout()
        btn_col.setContentsMargins(0, 0, 0, 0)
        btn_col.setSpacing(0)

        self._up = QPushButton("^")
        self._up.setFixedSize(ARROW_BTN_W, ARROW_BTN_H)
        self._up.setStyleSheet(ARROW_BTN_STYLE + "QPushButton { border-top-right-radius: 8px; border-bottom: 1px solid #2c3348; }")
        self._up.clicked.connect(self._inc)

        self._dn = QPushButton("v")
        self._dn.setFixedSize(ARROW_BTN_W, ARROW_BTN_H)
        self._dn.setStyleSheet(ARROW_BTN_STYLE + "QPushButton { border-bottom-right-radius: 8px; }")
        self._dn.clicked.connect(self._dec)

        btn_col.addWidget(self._up)
        btn_col.addWidget(self._dn)
        lay.addLayout(btn_col)

        self.setFixedHeight(SPINBOX_HEIGHT)
        self._edit.setFixedHeight(SPINBOX_HEIGHT)
        self.setStyleSheet(
            "QWidget { background: transparent; }"
            "QLineEdit {"
            "    background: #141720; border: 1px solid #2c3348;"
            "    border-top-right-radius: 0px; border-bottom-right-radius: 0px;"
            "    border-top-left-radius: 8px; border-bottom-left-radius: 8px;"
            "    padding: 8px 12px; color: #dde3f0;"
            "}"
            "QLineEdit:focus { border-color: #4a6fa5; }"
        )

    def _inc(self):     raise NotImplementedError
    def _dec(self):     raise NotImplementedError
    def _on_edit(self): raise NotImplementedError


class StyledSpinBox(ArrowInput):
    valueChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._min    = 0
        self._max    = 99
        self._val    = 0
        self._suffix = ""

    def setRange(self, mn, mx):
        self._min, self._max = mn, mx

    def setSuffix(self, s):
        self._suffix = s
        self.setValue(self._val)

    def value(self):
        return self._val

    def setValue(self, v):
        self._val = max(self._min, min(self._max, v))
        self._edit.setText(f"{self._val}{self._suffix}")

    def _inc(self):
        self.setValue(self._val + 1)
        self.valueChanged.emit(self._val)

    def _dec(self):
        self.setValue(self._val - 1)
        self.valueChanged.emit(self._val)

    def _on_edit(self):
        try:
            self.setValue(int(self._edit.text().replace(self._suffix, "").strip()))
        except ValueError:
            self.setValue(self._val)
        self._edit.setText(f"{self._val}{self._suffix}")
        self.valueChanged.emit(self._val)


class StyledTimeEdit(ArrowInput):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._h = self._m = 0

    def setTime(self, t):
        self._h, self._m = t.hour(), t.minute()
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
        parts = self._edit.text().strip().split(":")
        try:
            self._h = int(parts[0]) % 24
            self._m = int(parts[1]) % 60 if len(parts) > 1 else 0
        except (ValueError, IndexError):
            self._h = self._m = 0
        self._refresh()


from PyQt5.QtWidgets import QGraphicsEffect
from PyQt5.QtCore import QPointF

class SlideEffect(QGraphicsEffect):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dx      = 0.0
        self._opacity = 1.0

    def _get_dx(self):    return self._dx
    def _set_dx(self, v): self._dx = v; self.update()
    dx = pyqtProperty(float, _get_dx, _set_dx)

    def _get_op(self):    return self._opacity
    def _set_op(self, v): self._opacity = v; self.update()
    opacity = pyqtProperty(float, _get_op, _set_op)

    def boundingRectFor(self, r): return r

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
        self._dx_anim.setDuration(ANIM_SLOW - 160)
        self._dx_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._op_anim = QPropertyAnimation(self._eff, b"opacity")
        self._op_anim.setDuration(ANIM_NORMAL)
        self._op_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._grp = QParallelAnimationGroup()
        self._grp.addAnimation(self._dx_anim)
        self._grp.addAnimation(self._op_anim)

    def fade_in(self):
        self._grp.stop()
        self._dx_anim.setStartValue(float(SIDEBAR_OFFSET))
        self._dx_anim.setEndValue(0.0)
        self._op_anim.setStartValue(0.0)
        self._op_anim.setEndValue(1.0)
        self._grp.start()


class SidebarButton(QPushButton):
    def __init__(self, text, icon_char="", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setText(f"   {icon_char}  {text}" if icon_char else f"   {text}")
        self.setFixedHeight(38)
        self.setCursor(Qt.PointingHandCursor)

        self._bg  = QColor("#141720")
        self._fg  = QColor("#4e5a78")
        self._ind = 0.0

        def _anim(prop, dur):
            a = QPropertyAnimation(self, prop)
            a.setDuration(dur)
            a.setEasingCurve(QEasingCurve.OutCubic)
            return a

        self._bg_anim  = _anim(b"_bg_prop",  ANIM_FAST)
        self._fg_anim  = _anim(b"_fg_prop",  ANIM_FAST)
        self._ind_anim = _anim(b"_ind_prop", ANIM_FAST + 70)

    def _get_bg(self):    return self._bg
    def _set_bg(self, c): self._bg = c; self.update()
    _bg_prop = pyqtProperty(QColor, _get_bg, _set_bg)

    def _get_fg(self):    return self._fg
    def _set_fg(self, c): self._fg = c; self.update()
    _fg_prop = pyqtProperty(QColor, _get_fg, _set_fg)

    def _get_ind(self):    return self._ind
    def _set_ind(self, v): self._ind = v; self.update()
    _ind_prop = pyqtProperty(float, _get_ind, _set_ind)

    def _animate(self, bg, fg, ind):
        for a in (self._bg_anim, self._fg_anim, self._ind_anim):
            a.stop()
        self._bg_anim.setStartValue(self._bg);   self._bg_anim.setEndValue(bg)
        self._fg_anim.setStartValue(self._fg);   self._fg_anim.setEndValue(fg)
        self._ind_anim.setStartValue(self._ind); self._ind_anim.setEndValue(ind)
        for a in (self._bg_anim, self._fg_anim, self._ind_anim):
            a.start()

    def enterEvent(self, e):
        if not self.isChecked():
            self._animate(QColor("#1e2334"), QColor("#8898c8"), 0.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self.isChecked():
            self._animate(QColor("#141720"), QColor("#4e5a78"), 0.0)
        super().leaveEvent(e)

    def setChecked(self, v):
        super().setChecked(v)
        if v:
            self._animate(QColor("#1e2a48"), QColor("#6b9ed4"), 1.0)
        else:
            self._animate(QColor("#141720"), QColor("#4e5a78"), 0.0)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg)
        p.drawRoundedRect(r, 8, 8)
        if self._ind > 0:
            bh = int(r.height() * 0.5 * self._ind)
            by = (r.height() - bh) // 2
            p.setBrush(QColor("#4a6fa5"))
            p.drawRoundedRect(QRect(0, by, 3, bh), 1, 1)
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
        self._bc   = QColor(C_BORDER)

        self._glow_anim = QPropertyAnimation(self, b"_glow_val")
        self._glow_anim.setDuration(ANIM_FAST)
        self._glow_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._bc_anim = QPropertyAnimation(self, b"_bc_val")
        self._bc_anim.setDuration(ANIM_FAST)
        self._bc_anim.setEasingCurve(QEasingCurve.OutCubic)

    def _get_glow(self):    return self._glow
    def _set_glow(self, v): self._glow = v; self.update()
    _glow_val = pyqtProperty(float, _get_glow, _set_glow)

    def _get_bc(self):    return self._bc
    def _set_bc(self, c): self._bc = c; self.update()
    _bc_val = pyqtProperty(QColor, _get_bc, _set_bc)

    def _run(self, glow_to, bc_to):
        self._glow_anim.stop(); self._bc_anim.stop()
        self._glow_anim.setStartValue(self._glow);  self._glow_anim.setEndValue(glow_to)
        self._bc_anim.setStartValue(self._bc);       self._bc_anim.setEndValue(bc_to)
        self._glow_anim.start(); self._bc_anim.start()

    def enterEvent(self, e):
        self._run(1.0, QColor(C_ACCENT))
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._run(0.0, QColor(C_BORDER))
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        base, hover = QColor("#1e2230"), QColor("#252c42")
        bg = QColor(
            int(base.red()   + (hover.red()   - base.red())   * self._glow),
            int(base.green() + (hover.green() - base.green()) * self._glow),
            int(base.blue()  + (hover.blue()  - base.blue())  * self._glow),
        )
        p.setPen(QPen(self._bc, 1))
        p.setBrush(bg)
        p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 10, 10)
        if self._glow > 0:
            p.setPen(QPen(QColor(74, 111, 165, int(80 * self._glow)), 1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(r.adjusted(0, 0, -1, -1), 10, 10)
        p.setPen(QColor("#dde3f0"))
        font = self.font()
        font.setPointSize(10)
        p.setFont(font)
        p.drawText(r, Qt.AlignCenter, self.text())
        p.end()


class AnimatedProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dv = 0.0
        self._anim = QPropertyAnimation(self, b"_dv_prop")
        self._anim.setDuration(ANIM_SLOW)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setTextVisible(False)
        self.setFixedHeight(5)

    def _get_dv(self):    return self._dv
    def _set_dv(self, v): self._dv = v; self.update()
    _dv_prop = pyqtProperty(float, _get_dv, _set_dv)

    def setValue(self, v):
        super().setValue(v)
        self._anim.stop()
        self._anim.setStartValue(self._dv)
        self._anim.setEndValue(float(v))
        self._anim.start()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1e2230"))
        p.drawRoundedRect(r, 3, 3)
        if self.maximum() > 0:
            fill_w = int(r.width() * self._dv / self.maximum())
            if fill_w > 0:
                grad = QLinearGradient(0, 0, fill_w, 0)
                grad.setColorAt(0, QColor("#4a6fa5"))
                grad.setColorAt(1, QColor("#6b9ed4"))
                p.setBrush(grad)
                p.drawRoundedRect(QRect(0, 0, fill_w, r.height()), 3, 3)
        p.end()


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


class ProxyStatusDot(QWidget):
    _colors = {"ok": "#6a9e80", "err": "#b06070", "checking": "#a08858"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = QColor("#3a4a68")

    def set_status(self, status):
        self._color = QColor(self._colors.get(status, "#3a4a68"))
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(self.rect())
        p.end()


class ProxyRowWidget(QWidget):
    _status_styles = {
        "ok":       ("OK",  "color: #6a9e80; font-size: 11px; background: transparent; min-width: 40px;"),
        "err":      ("ERR", "color: #b06070; font-size: 11px; background: transparent; min-width: 40px;"),
        "checking": ("...", "color: #a08858; font-size: 11px; background: transparent; min-width: 40px;"),
    }

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
            u = QLabel(proxy_data["user"])
            u.setStyleSheet("color: #4e5a78; font-size: 11px; background: transparent;")
            lay.addWidget(u)

        lay.addStretch()

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("font-size: 11px; background: transparent; min-width: 40px;")
        lay.addWidget(self._status_lbl)

        self._active_lbl = QLabel("")
        self._active_lbl.setStyleSheet("color: #4a6fa5; font-size: 11px; font-weight: 700; background: transparent; min-width: 50px;")
        lay.addWidget(self._active_lbl)

    def set_status(self, status, info=""):
        self._dot.set_status(status)
        text, style = self._status_styles.get(status, ("", "font-size: 11px; background: transparent; min-width: 40px;"))
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(style)

    def set_active(self, active):
        self._active_lbl.setText("АКТИВНЫЙ" if active else "")
