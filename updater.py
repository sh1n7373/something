import sys
import subprocess
import urllib.request
from pathlib import Path

from PyQt5.QtWidgets import QMessageBox

APP_VERSION = "4.0"
GITHUB_RAW_URL     = "https://raw.githubusercontent.com/sh1n7373/something/main/Lagos.py"
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/sh1n7373/something/main/version.txt"

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
        with urllib.request.urlopen(GITHUB_RAW_URL, timeout=30) as r:
            new_code = r.read()

        if getattr(sys, "frozen", False):
            current_dir = Path(sys.executable).parent
            (current_dir / "Lagos.py").write_bytes(new_code)
            try:
                Path(sys.executable).unlink()
            except OSError:
                pass
            QMessageBox.information(
                parent, "Обновление загружено",
                "Lagos.py обновлён!\n\nЗапусти install.bat чтобы пересобрать приложение."
            )
            sys.exit(0)
        else:
            current = Path(sys.argv[0]).resolve()
            current.with_suffix(".bak").write_bytes(current.read_bytes())
            current.write_bytes(new_code)
            subprocess.Popen([sys.executable, str(current)])
            sys.exit(0)

    except Exception as e:
        QMessageBox.critical(parent, "Ошибка обновления", str(e))
