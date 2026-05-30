from PyQt5.QtWidgets import QFrame, QLabel

ANIM_FAST   = 280
ANIM_NORMAL = 380
ANIM_SLOW   = 580

SIDEBAR_OFFSET = -48.0
SPINBOX_HEIGHT = 36
ARROW_BTN_W    = 28
ARROW_BTN_H    = 24

C_BG         = "#1a1d26"
C_SURFACE    = "#1e2230"
C_SURFACE2   = "#252c42"
C_SURFACE3   = "#2d3650"
C_BORDER     = "#323a52"
C_BORDER2    = "#2c3348"
C_ACCENT     = "#4a6fa5"
C_ACCENT2    = "#6b9ed4"
C_TEXT       = "#dde3f0"
C_TEXT_DIM   = "#a8b8d8"
C_TEXT_MUTED = "#4e5a78"
C_SECTION    = "#6b82c0"
C_OK         = "#6a9e80"
C_ERR        = "#b06070"
C_WARN       = "#a08858"
C_INFO       = "#5878a8"

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
QComboBox:focus { border-color: #4a6fa5; }
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
QPushButton:hover { background: #253050; color: #a0b8e0; }
QPushButton:pressed { background: #3d5080; }
"""

COMBO_VIEW_STYLE = """
    QAbstractItemView {
        background: #141720;
        color: #dde3f0;
        border: 1px solid #2a3a5a;
        border-radius: 6px;
        outline: none;
        padding: 2px;
        selection-background-color: #2a3a5a;
        selection-color: #e8eef8;
    }
    QAbstractItemView::item {
        padding: 7px 12px;
        min-height: 28px;
        background: transparent;
        color: #a8b8d8;
    }
    QAbstractItemView::item:hover { background: #1e2538; color: #dde3f0; }
    QAbstractItemView::item:selected { background: #2a3a5a; color: #e8eef8; }
"""

PASTE_LIST_STYLE = """
    QListWidget {
        background: #141720;
        border: 1px solid #2c3348;
        border-radius: 8px;
        outline: none;
        padding: 4px;
        color: #a8b8d8;
    }
    QListWidget::item {
        border-radius: 6px;
        padding: 5px 10px;
        margin: 1px 2px;
        color: #a8b8d8;
        background: transparent;
    }
    QListWidget::item:hover { background: #202535; }
    QListWidget::indicator {
        width: 13px;
        height: 13px;
        border: 1px solid #4a6fa5;
        border-radius: 3px;
        background: #1a1d26;
    }
    QListWidget::indicator:checked {
        background: #4a6fa5;
        border-color: #4a6fa5;
    }
"""

PROXY_LIST_STYLE = """
    QListWidget {
        background: #141720;
        border: 1px solid #2c3348;
        border-radius: 8px;
        outline: none;
        padding: 4px;
    }
    QListWidget::item {
        border-radius: 6px;
        padding: 2px 4px;
        margin: 1px 2px;
        color: #a8b8d8;
    }
    QListWidget::item:selected { background: #2a3a5a; color: #e8eef8; }
    QListWidget::item:hover { background: #202535; }
"""

MONOSPACE_VIEW_STYLE = """
    QTextEdit {
        background: #13161f;
        border: 1px solid #232840;
        border-radius: 10px;
        padding: 12px 14px;
        font-size: 13px;
        color: #dde3f0;
    }
"""

LOG_VIEW_STYLE = """
    QTextEdit {
        background: #13161f;
        border: 1px solid #232840;
        border-radius: 8px;
        padding: 10px 12px;
        font-size: 12px;
        color: #dde3f0;
    }
"""


def make_sep():
    f = QFrame()
    f.setObjectName("separator")
    return f


def section_label(text):
    lbl = QLabel(text)
    lbl.setObjectName("section")
    return lbl
