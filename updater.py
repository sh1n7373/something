import sys
import subprocess
import urllib.request
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox

APP_VERSION = "5.1"
GITHUB_BASE_URL    = "https://raw.githubusercontent.com/sh1n7373/something/main/"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/sh1n7373/something/main/version.txt"
GITHUB_FILES = [
    "app.py",
    "storage.py",
    "tg_client.py",
    "theme.py",
    "updater.py",
    "widgets.py",
    "device_profiles.py",
]

_pending_version = None


def check_for_update():
    global _pending_version
    try:
        with urllib.request.urlopen(GITHUB_VERSION_URL, timeout=8) as r:
            latest = r.read().decode().strip()
        if latest != APP_VERSION:
            _pending_version = latest
    except (OSError, ValueError):
        pass


def pending_version():
    return _pending_version


def show_update_dialog(parent, style):
    if not _pending_version:
        return
    msg = QMessageBox(parent)
    msg.setWindowTitle("Доступно обновление")
    msg.setText(f"Новая версия: {_pending_version}\nТекущая: {APP_VERSION}\n\nОбновить сейчас?")
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setStyleSheet(style)
    if msg.exec_() == QMessageBox.Yes:
        _do_update(parent)


def _do_update(parent):
    try:
        base = Path(sys.argv[0]).resolve().parent
        for filename in GITHUB_FILES:
            url = GITHUB_BASE_URL + filename
            with urllib.request.urlopen(url, timeout=30) as r:
                data = r.read()
            (base / filename).write_bytes(data)
        QMessageBox.information(
            parent, "Обновление загружено",
            "Для обновления запусти install.bat"
        )
        sys.exit(0)
    except Exception as e:
        QMessageBox.critical(parent, "Ошибка обновления", str(e))
