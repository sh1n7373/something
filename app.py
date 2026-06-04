import sys
import threading
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

if getattr(sys, "frozen", False):
    _internal = Path(sys.executable).parent / "_internal"
    if _internal.exists() and str(_internal) not in sys.path:
        sys.path.insert(0, str(_internal))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QPlainTextEdit,
    QListWidget, QListWidgetItem, QScrollArea, QFrame, QStackedWidget,
    QAbstractItemView, QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt, QTimer, QTime, pyqtSignal, QObject, QSize
from PyQt5.QtGui import QIcon, QPainter, QColor

from theme import STYLE, PASTE_LIST_STYLE, PROXY_LIST_STYLE, MONOSPACE_VIEW_STYLE, LOG_VIEW_STYLE
from storage import (
    load_data, save_data, APP_DIR,
    recipient_tag, recipient_token, parse_recipient_line, parse_recipients_bulk
)
from tg_client import build_client, SenderWorker, ChatLoader, SpamBotLoader, ProxyChecker, FingerprintChecker, SESSION_DIR
from device_profiles import random_fingerprint
from widgets import (
    FadeWidget, SidebarButton, AnimatedButton, AnimatedProgressBar,
    StatCard, StyledSpinBox, StyledTimeEdit, ProxyRowWidget,
    styled_combo, make_sep, section_label
)
from updater import APP_VERSION, check_for_update, show_update_dialog, pending_version


def resource_path(name):
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return str(Path(base) / name)


class AuthDialog(QDialog):
    _sig_status  = pyqtSignal(str)
    _sig_code    = pyqtSignal()
    _sig_pass    = pyqtSignal()
    _sig_done    = pyqtSignal(str, str, str, str, str)

    def __init__(self, parent=None, proxy=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить аккаунт")
        self.setMinimumWidth(420)
        self.setStyleSheet(STYLE)
        self.result_account = None
        self._client = None
        self._phone  = ""
        self._step   = "phone"
        self._proxy  = proxy
        self._loop   = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._dot_timer = QTimer()
        self._dot_timer.timeout.connect(self._tick)
        self._dots = 0
        for sig, slot in [
            (self._sig_status, self._set_status),
            (self._sig_code,   self._show_code_step),
            (self._sig_pass,   self._show_pass_step),
            (self._sig_done,   self._on_done),
        ]:
            sig.connect(slot)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(14)

        title = QLabel("Подключение аккаунта")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #e8eef8;")
        lay.addWidget(title)

        link = QLabel('API ID и API Hash на <a href="https://my.telegram.org" style="color:#6b9ed4;">my.telegram.org</a>')
        link.setOpenExternalLinks(True)
        link.setStyleSheet("color: #4e5a78; font-size: 12px;")
        lay.addWidget(link)
        lay.addWidget(make_sep())

        for lbl_text, attr, ph in [
            ("API ID",          "api_id",     "12345678"),
            ("API HASH",        "api_hash",   "abcdef1234..."),
            ("НОМЕР ТЕЛЕФОНА",  "phone_edit", "+79001234567"),
        ]:
            lay.addWidget(section_label(lbl_text))
            e = QLineEdit()
            e.setPlaceholderText(ph)
            setattr(self, attr, e)
            lay.addWidget(e)

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
        self.btn.clicked.connect(self._on_btn)
        lay.addWidget(self.btn)

    def _on_btn(self):
        {"phone": self._send_code, "code": self._confirm_code, "password": self._confirm_pass}[self._step]()

    def _send_code(self):
        try:
            api_id = int(self.api_id.text().strip())
        except ValueError:
            self._set_status("API ID должен быть числом"); return
        phone = self.phone_edit.text().strip()
        api_hash = self.api_hash.text().strip()
        if not phone or not api_hash:
            self._set_status("Заполните все поля"); return
        self._phone = phone
        self._api_id_val = api_id
        self._api_hash_val = api_hash
        self._client = build_client({"phone": phone, "api_id": api_id, "api_hash": api_hash}, self._proxy)
        self.btn.setEnabled(False)
        self._dots = 0
        self._dot_timer.start(600)

        async def _go():
            try:
                await self._client.connect()
                await self._client.send_code_request(phone)
                self._sig_code.emit()
            except Exception as ex:
                self._sig_status.emit(f"Ошибка: {ex}")
                self._sig_status.emit("btn_enable")

        asyncio.run_coroutine_threadsafe(_go(), self._loop)

    def _tick(self):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._dots = (self._dots + 1) % len(frames)
        self.status_lbl.setText(f"{frames[self._dots]}  Подключаемся к Telegram...")

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
            self._set_status("Введите код"); return
        self.btn.setEnabled(False)
        self._set_status("Проверяем...")

        async def _go():
            try:
                from telethon.errors import SessionPasswordNeededError
                await self._client.sign_in(self._phone, code)
                me = await self._client.get_me()
                await self._client.disconnect()
                self._sig_done.emit(
                    me.first_name or "", me.last_name or "",
                    me.username or "", self._phone,
                    f"{self._api_id_val}|{self._api_hash_val}"
                )
            except Exception as ex:
                from telethon.errors import SessionPasswordNeededError
                if isinstance(ex, SessionPasswordNeededError):
                    self._sig_pass.emit()
                else:
                    self._sig_status.emit(f"Ошибка: {ex}")
                    self._sig_status.emit("btn_enable")

        asyncio.run_coroutine_threadsafe(_go(), self._loop)

    def _show_pass_step(self):
        self._step = "password"
        self.pass_edit.setVisible(True)
        self.btn.setText("Войти")
        self.btn.setEnabled(True)
        self._set_status("Введите пароль двухэтапной проверки")

    def _confirm_pass(self):
        pw = self.pass_edit.text().strip()
        if not pw:
            self._set_status("Введите пароль"); return
        self.btn.setEnabled(False)
        self._set_status("Проверяем пароль...")

        async def _go():
            try:
                await self._client.sign_in(password=pw)
                me = await self._client.get_me()
                await self._client.disconnect()
                self._sig_done.emit(
                    me.first_name or "", me.last_name or "",
                    me.username or "", self._phone,
                    f"{self._api_id_val}|{self._api_hash_val}"
                )
            except Exception as ex:
                self._sig_status.emit(f"Ошибка: {ex}")
                self._sig_status.emit("btn_enable")

        asyncio.run_coroutine_threadsafe(_go(), self._loop)

    def _on_done(self, first, last, username, phone, api_str):
        api_id_str, api_hash = api_str.split("|", 1)
        self.result_account = {
            "phone": phone,
            "api_id": int(api_id_str),
            "api_hash": api_hash,
            "name": f"{first} {last}".strip(),
            "username": username,
        }
        self._loop.call_soon_threadsafe(self._loop.stop)
        self.accept()

    def _set_status(self, text):
        if text == "btn_enable":
            self.btn.setEnabled(True)
        else:
            self.status_lbl.setText(text)

    def closeEvent(self, e):
        self._dot_timer.stop()
        self._loop.call_soon_threadsafe(self._loop.stop)
        super().closeEvent(e)


def _acc_label(acc):
    un = f"@{acc['username']}" if acc.get("username") else ""
    return f"{acc.get('name', acc['phone'])}  {un}  {acc['phone']}"


def _proxy_label(p):
    return f"{p['type'].upper()}  {p['host']}:{p['port']}"


class SpamWorker(QObject):
    result_signal = pyqtSignal(str, list)
    error_signal  = pyqtSignal(str)

    def __init__(self, acc, text, proxy):
        super().__init__()
        self.acc   = acc
        self.text  = text
        self.proxy = proxy

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._inner())

    async def _inner(self):
        try:
            from tg_client import build_client
            client = build_client(self.acc, self.proxy, chat_mode=True)
            await client.connect()
            if not await client.is_user_authorized():
                self.error_signal.emit("Аккаунт не авторизован")
                await client.disconnect()
                return
            await client.send_message("@SpamBot", self.text)
            reply, btns = "", []
            for _ in range(10):
                await asyncio.sleep(2)
                async for m in client.iter_messages("@SpamBot", limit=5):
                    if not m.out and m.message:
                        reply = m.message
                        if m.reply_markup and hasattr(m.reply_markup, "rows"):
                            for row in m.reply_markup.rows:
                                for b in row.buttons:
                                    if hasattr(b, "text"):
                                        btns.append(b.text)
                        break
                if reply:
                    break
            await client.disconnect()
            self.result_signal.emit(reply, btns)
        except Exception as ex:
            self.error_signal.emit(str(ex))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lagos Sender")
        self.setMinimumSize(1160, 720)
        self.setStyleSheet(STYLE)
        self.data = load_data()

        self._workers       = {}
        self._worker_threads = {}
        self._worker_totals = {}
        self._worker_paused = {}
        self._worker_timers = {}
        self._worker_cards  = []
        self._proxy_status  = {}
        self._proxy_rows    = []
        self._app_proxy_rows = []
        self._ok_count      = 0
        self._err_count     = 0
        self._total_msgs    = 0
        self._done_msgs     = 0
        self._failed_tags   = []
        self._failed_entries = []
        self._spamblock_log = []

        self._build_ui()
        self._refresh_accounts()
        self._refresh_recipients()
        self._refresh_pastes()
        self._refresh_proxies()
        self._refresh_app_proxies()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet("background: #141720; border: none;")
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(12, 24, 12, 20)
        sb.setSpacing(3)

        logo = QLabel("Lagos Sender")
        logo.setStyleSheet("font-size: 15px; font-weight: 700; color: #8898c8; letter-spacing: 0.5px; background: transparent; border: none;")
        logo.setAlignment(Qt.AlignCenter)
        sb.addWidget(logo)
        sb.addSpacing(20)

        self._tab_btns = []
        for name, idx in [
            ("Аккаунты", 0), ("Теги", 1), ("Пасты", 2), ("Отписи", 3),
            ("Логи", 4), ("Прокси пул", 5), ("Системное прокси", 6),
            ("Чаты", 7), ("Спамблок", 8),
        ]:
            btn = SidebarButton(name)
            btn.clicked.connect(lambda _checked, i=idx: self._switch_tab(i))
            sb.addWidget(btn)
            self._tab_btns.append(btn)

        sb.addStretch()
        ver = QLabel(f"v{APP_VERSION}")
        ver.setStyleSheet("color: #2e3a52; font-size: 11px; background: transparent; border: none;")
        ver.setAlignment(Qt.AlignCenter)
        sb.addWidget(ver)
        root.addWidget(sidebar)

        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("QFrame { background: #1e2334; border: none; }")
        root.addWidget(sep)

        right = QWidget()
        right.setStyleSheet("background: #1a1d26;")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        topbar = QWidget()
        topbar.setFixedHeight(52)
        topbar.setStyleSheet("background: #1a1d26; border-bottom: 1px solid #1e2334;")
        tl = QHBoxLayout(topbar)
        tl.setContentsMargins(24, 10, 24, 10)
        tl.addStretch()

        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setMinimumWidth(200)
        self.progress_bar.hide()
        tl.addWidget(self.progress_bar)
        tl.addSpacing(10)

        self._pause_btn = AnimatedButton("Пауза")
        self._pause_btn.setFixedHeight(32)
        self._pause_btn.setMinimumWidth(90)
        self._pause_btn.hide()
        self._pause_btn.clicked.connect(self._toggle_pause)
        tl.addWidget(self._pause_btn)
        tl.addSpacing(8)

        self._run_btn = AnimatedButton("Начать отписи")
        self._run_btn.setFixedHeight(32)
        self._run_btn.setMinimumWidth(160)
        self._run_btn.clicked.connect(self._toggle_send)
        tl.addWidget(self._run_btn)
        rv.addWidget(topbar)

        self._stack = QStackedWidget()
        rv.addWidget(self._stack)
        root.addWidget(right)

        pages = [
            self._build_accounts_page(),
            self._build_tags_page(),
            self._build_pastes_page(),
            self._build_sender_page(),
            self._build_logs_page(),
            self._build_proxies_page(),
            self._build_sys_proxy_page(),
            self._build_chats_page(),
            self._build_spamblock_page(),
        ]
        for p in pages:
            self._stack.addWidget(p)
        self._pages = pages
        self._switch_tab(0)

    def _mk_page(self, title=None, subtitle=None):
        w = FadeWidget()
        w.setStyleSheet("background: #1a1d26;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 36, 36, 36)
        lay.setSpacing(14)
        if title:
            h = QLabel(title)
            h.setObjectName("header")
            lay.addWidget(h)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("subheader")
            lay.addWidget(s)
        if title:
            lay.addWidget(make_sep())
        return w, lay

    def _switch_tab(self, idx):
        for i, btn in enumerate(self._tab_btns):
            btn.setChecked(i == idx)
        page = self._pages[idx]
        if hasattr(page, "fade_in"):
            page.fade_in()
        self._stack.setCurrentIndex(idx)
        refresh = {3: self._refresh_sender_page, 7: self._refresh_chats_accounts, 8: self._on_switch_spamblock}
        if idx in refresh:
            refresh[idx]()

    def _build_accounts_page(self):
        w, lay = self._mk_page("Аккаунты")

        content = QHBoxLayout()
        content.setSpacing(28)

        left = QVBoxLayout()
        self.acc_list = QListWidget()
        self.acc_list.currentRowChanged.connect(self._on_acc_selected)
        left.addWidget(self.acc_list)
        btn_row = QHBoxLayout()
        add = AnimatedButton("Добавить аккаунт")
        add.clicked.connect(self._add_account)
        rm = AnimatedButton("Удалить")
        rm.clicked.connect(self._del_account)
        btn_row.addWidget(add); btn_row.addWidget(rm); btn_row.addStretch()
        left.addLayout(btn_row)
        content.addLayout(left, 2)

        right = QVBoxLayout()
        right.setSpacing(10)
        fp_lbl = QLabel("ФИНГЕРПРИНТ УСТРОЙСТВА")
        fp_lbl.setObjectName("section")
        right.addWidget(fp_lbl)

        self._fp_info = QLabel("Выберите аккаунт")
        self._fp_info.setStyleSheet("color: #6b82c0; font-size: 12px; background: transparent;")
        self._fp_info.setWordWrap(True)
        right.addWidget(self._fp_info)

        right.addSpacing(8)
        type_lbl = QLabel("ТИП УСТРОЙСТВА")
        type_lbl.setObjectName("section")
        right.addWidget(type_lbl)
        self._fp_type_combo = styled_combo()
        self._fp_type_combo.addItems(["Случайный", "Android", "iOS", "Desktop (Win/Mac/Linux)"])
        self._fp_type_combo.setFixedHeight(36)
        right.addWidget(self._fp_type_combo)

        rand_btn = AnimatedButton("Рандомизировать")
        rand_btn.clicked.connect(self._randomize_fingerprint)
        right.addWidget(rand_btn)

        rand_all_btn = AnimatedButton("Рандомизировать все")
        rand_all_btn.clicked.connect(self._randomize_all_fingerprints)
        right.addWidget(rand_all_btn)

        check_fp_btn = AnimatedButton("Проверить фингерпринт")
        check_fp_btn.clicked.connect(self._check_fingerprint)
        right.addWidget(check_fp_btn)

        self._fp_check_lbl = QLabel("")
        self._fp_check_lbl.setStyleSheet("color: #6b82c0; font-size: 11px; background: transparent;")
        self._fp_check_lbl.setWordWrap(True)
        right.addWidget(self._fp_check_lbl)

        right.addStretch()
        content.addLayout(right, 1)
        lay.addLayout(content)
        return w

    def _on_acc_selected(self, row):
        if row < 0 or row >= len(self.data["accounts"]):
            self._fp_info.setText("Выберите аккаунт")
            return
        acc = self.data["accounts"][row]
        fp = acc.get("fingerprint")
        if fp:
            label = fp.get("_profile_label", "неизвестно")
            lang = fp.get("lang_code", "?")
            app_ver = fp.get("app_version", "?")
            self._fp_info.setText(f"{label}\nПриложение: {app_ver}  Язык: {lang}")
        else:
            self._fp_info.setText("Фингерпринт не задан")

    def _get_fp_type(self):
        idx = self._fp_type_combo.currentIndex()
        return ["random", "android", "ios", "desktop"][idx]

    def _check_fingerprint(self):
        row = self.acc_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Ошибка", "Выберите аккаунт"); return
        acc = self.data["accounts"][row]
        self._fp_check_lbl.setText("Подключаемся к Telegram...")
        proxy = self._get_app_proxy()
        chk = FingerprintChecker(acc, proxy)
        chk.result_signal.connect(self._on_fp_check_result)
        chk.error_signal.connect(lambda e: self._fp_check_lbl.setText(f"Ошибка: {e}"))
        threading.Thread(target=chk.run, daemon=True).start()

    def _on_fp_check_result(self, info):
        lines = [
            f"Устройство: {info.get('device', '?')}",
            f"Платформа: {info.get('platform', '?')}",
            f"ОС: {info.get('system', '?')}",
            f"Приложение: {info.get('app', '?')}",
            f"Страна: {info.get('country', '?')}",
            f"IP: {info.get('ip', '?')}",
            f"Официальный: {'да' if info.get('official') else 'нет'}",
        ]
        self._fp_check_lbl.setText("\n".join(lines))

    def _randomize_fingerprint(self):
        row = self.acc_list.currentRow()
        if row < 0:
            return
        fp = random_fingerprint(self._get_fp_type())
        self.data["accounts"][row]["fingerprint"] = fp
        save_data(self.data)
        self._on_acc_selected(row)

    def _randomize_all_fingerprints(self):
        fp_type = self._get_fp_type()
        for acc in self.data["accounts"]:
            acc["fingerprint"] = random_fingerprint(fp_type)
        save_data(self.data)
        row = self.acc_list.currentRow()
        self._on_acc_selected(row)

    def _refresh_accounts(self):
        self.acc_list.clear()
        for acc in self.data["accounts"]:
            self.acc_list.addItem(f"  {_acc_label(acc)}")

    def _add_account(self):
        dlg = AuthDialog(self, proxy=self._get_app_proxy())
        if dlg.exec_() == QDialog.Accepted:
            self.data["accounts"].append(dlg.result_account)
            save_data(self.data)
            self._refresh_accounts()
            self._refresh_sender_page()

    def _del_account(self):
        row = self.acc_list.currentRow()
        if row < 0: return
        self.data["accounts"].pop(row)
        save_data(self.data)
        self._refresh_accounts()
        self._refresh_sender_page()

    def _build_tags_page(self):
        w, lay = self._mk_page("Теги", "Создавайте отдельные базы для каждого потока отписок")

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(section_label("БАЗА:"))
        self.db_combo = styled_combo()
        self.db_combo.setFixedHeight(34)
        self.db_combo.setMinimumWidth(200)
        self.db_combo.currentIndexChanged.connect(self._refresh_recipients)
        top.addWidget(self.db_combo)
        self.db_name_edit = QLineEdit()
        self.db_name_edit.setPlaceholderText("Название новой базы...")
        self.db_name_edit.setFixedHeight(34)
        self.db_name_edit.setMinimumWidth(180)
        top.addWidget(self.db_name_edit)
        for label, slot in [("+ Новая база", self._create_db), ("Удалить базу", self._delete_db)]:
            b = AnimatedButton(label)
            b.setFixedHeight(34)
            b.clicked.connect(slot)
            top.addWidget(b)
        top.addStretch()
        lay.addLayout(top)

        content = QHBoxLayout()
        content.setSpacing(28)

        left = QVBoxLayout()
        left.addWidget(section_label("СПИСОК"))
        self.rec_list = QListWidget()
        self.rec_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        left.addWidget(self.rec_list)
        self.rec_count = QLabel("0 тегов")
        self.rec_count.setStyleSheet("color: #4e5a78; font-size: 12px;")
        left.addWidget(self.rec_count)
        content.addLayout(left, 2)

        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(section_label("ДОБАВИТЬ"))
        self.rec_single = QLineEdit()
        self.rec_single.setPlaceholderText("@username - $TOKEN")
        right.addWidget(self.rec_single)
        add1 = AnimatedButton("+ Добавить")
        add1.clicked.connect(self._add_tag_single)
        right.addWidget(add1)

        right.addWidget(section_label("СПИСКОМ"))
        self.rec_bulk = QPlainTextEdit()
        self.rec_bulk.setPlaceholderText("@user1 - $TOKEN1\n@user2 - [job title]")
        self.rec_bulk.setMaximumHeight(130)
        right.addWidget(self.rec_bulk)
        addm = AnimatedButton("Добавить всех")
        addm.clicked.connect(self._add_tags_bulk)
        right.addWidget(addm)

        right.addSpacing(14)
        right.addWidget(make_sep())
        right.addSpacing(14)

        for label, slot in [
            ("Удалить выбранные", self._del_selected_tags),
            ("Очистить список",   self._clear_tags),
            ("Копировать список", self._export_tags),
        ]:
            b = AnimatedButton(label)
            b.clicked.connect(slot)
            right.addWidget(b)

        hint = QLabel("Ctrl+Click для выбора нескольких")
        hint.setStyleSheet("color: #3a4a68; font-size: 11px;")
        right.addWidget(hint)
        right.addStretch()
        content.addLayout(right, 1)
        lay.addLayout(content)
        self._refresh_db_combo()
        return w

    def _current_db_key(self):
        idx = self.db_combo.currentIndex()
        return self.db_combo.currentText() if idx > 0 else None

    def _get_recs(self):
        key = self._current_db_key()
        return self.data["recipient_dbs"].get(key, []) if key else self.data["recipients"]

    def _set_recs(self, lst):
        key = self._current_db_key()
        if key:
            self.data.setdefault("recipient_dbs", {})[key] = lst
        else:
            self.data["recipients"] = lst

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
        self._sync_worker_rec_combos()

    def _create_db(self):
        name = self.db_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название базы"); return
        if name in self.data.get("recipient_dbs", {}):
            QMessageBox.warning(self, "Ошибка", "База с таким именем уже существует"); return
        self.data.setdefault("recipient_dbs", {})[name] = []
        save_data(self.data)
        self.db_name_edit.clear()
        self._refresh_db_combo()
        idx = self.db_combo.findText(name)
        if idx >= 0:
            self.db_combo.setCurrentIndex(idx)

    def _delete_db(self):
        key = self._current_db_key()
        if not key:
            QMessageBox.warning(self, "Ошибка", "Общую базу удалить нельзя"); return
        if QMessageBox.question(self, "Удалить базу", f"Удалить базу '{key}'?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        del self.data["recipient_dbs"][key]
        save_data(self.data)
        self._refresh_db_combo()

    def _refresh_recipients(self):
        self.rec_list.clear()
        for r in self._get_recs():
            tag, token = recipient_tag(r), recipient_token(r)
            self.rec_list.addItem(f"  {tag}  {token}" if token else f"  {tag}")
        self.rec_count.setText(f"{len(self._get_recs())} тегов")

    def _add_tag_single(self):
        raw = self.rec_single.text().strip()
        if not raw: return
        tag, token = parse_recipient_line(raw)
        recs = self._get_recs()
        if not any(recipient_tag(r) == tag for r in recs):
            recs.append({"tag": tag, "token": token})
            self._set_recs(recs)
            save_data(self.data)
            self._refresh_recipients()
        self.rec_single.clear()

    def _add_tags_bulk(self):
        parsed = parse_recipients_bulk(self.rec_bulk.toPlainText())
        recs = self._get_recs()
        existing = {recipient_tag(r) for r in recs}
        added = [p for p in parsed if p["tag"] not in existing]
        recs.extend(added)
        self._set_recs(recs)
        save_data(self.data)
        self._refresh_recipients()
        self.rec_bulk.clear()
        QMessageBox.information(self, "Готово", f"Добавлено {len(added)} тегов")

    def _del_selected_tags(self):
        rows = sorted({i.row() for i in self.rec_list.selectedIndexes()}, reverse=True)
        if not rows: return
        recs = self._get_recs()
        for r in rows:
            recs.pop(r)
        self._set_recs(recs)
        save_data(self.data)
        self._refresh_recipients()

    def _clear_tags(self):
        self._set_recs([])
        save_data(self.data)
        self._refresh_recipients()

    def _export_tags(self):
        recs = self._get_recs()
        if not recs:
            QMessageBox.information(self, "Экспорт", "Список пуст"); return
        lines = []
        for r in recs:
            tag, token = recipient_tag(r), recipient_token(r)
            lines.append(f"{tag} - {token}" if token else tag)
        from PyQt5.QtWidgets import QApplication
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Экспорт", f"Скопировано {len(lines)} тегов")

    def _build_pastes_page(self):
        w, lay = self._mk_page("Пасты", "Тексты сообщений отправляются по очереди каждому мамонту")

        content = QHBoxLayout()
        content.setSpacing(28)

        left = QVBoxLayout()
        left.addWidget(section_label("ПАСТЫ"))
        self.paste_list = QListWidget()
        self.paste_list.currentRowChanged.connect(self._load_paste)
        left.addWidget(self.paste_list)
        row = QHBoxLayout()
        for label, slot in [("+ Новая", self._new_paste), ("Удалить", self._del_paste)]:
            b = AnimatedButton(label)
            b.clicked.connect(slot)
            row.addWidget(b)
        left.addLayout(row)
        content.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(section_label("ТЕКСТ СООБЩЕНИЯ"))
        hint_p = QLabel("Замены в тексте:  $token - токен     [job] - должность(хайринг)")
        hint_p.setStyleSheet("color: #4e5a78; font-size: 11px;")
        right.addWidget(hint_p)
        self.paste_edit = QTextEdit()
        self.paste_edit.setPlaceholderText("Введите текст сообщения...")
        self.paste_edit.textChanged.connect(lambda: self._paste_save_timer.start(800))
        right.addWidget(self.paste_edit)
        save_btn = AnimatedButton("Сохранить")
        save_btn.clicked.connect(self._save_paste)
        right.addWidget(save_btn)
        content.addLayout(right, 2)
        lay.addLayout(content)

        self._paste_save_timer = QTimer()
        self._paste_save_timer.setSingleShot(True)
        self._paste_save_timer.timeout.connect(self._save_paste_silent)
        return w

    def _refresh_pastes(self):
        self.paste_list.clear()
        for i, p in enumerate(self.data["pastes"]):
            self.paste_list.addItem(f"  {i+1}.  {p[:48].replace(chr(10), ' ')}")

    def _refresh_pastes_keep(self, row):
        cur = self.paste_edit.textCursor()
        pos = cur.position()
        self.paste_list.blockSignals(True)
        self.paste_edit.blockSignals(True)
        self._refresh_pastes()
        self.paste_list.blockSignals(False)
        if row < self.paste_list.count():
            self.paste_list.setCurrentRow(row)
        self.paste_edit.blockSignals(False)
        cur.setPosition(min(pos, len(self.paste_edit.toPlainText())))
        self.paste_edit.setTextCursor(cur)

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
        if row < 0: return
        self.data["pastes"][row] = self.paste_edit.toPlainText()
        save_data(self.data)
        self._refresh_pastes_keep(row)

    def _save_paste_silent(self):
        row = self.paste_list.currentRow()
        if 0 <= row < len(self.data["pastes"]):
            self.data["pastes"][row] = self.paste_edit.toPlainText()
            save_data(self.data)
            self._refresh_pastes_keep(row)

    def _del_paste(self):
        row = self.paste_list.currentRow()
        if row < 0: return
        self.data["pastes"].pop(row)
        save_data(self.data)
        self._refresh_pastes()

    def _build_proxies_page(self):
        w, lay = self._mk_page("Прокси пул", "Прокси для отписей")

        content = QHBoxLayout()
        content.setSpacing(28)

        left = QVBoxLayout()
        left.addWidget(section_label("ПРОКСИ ПУЛ"))
        self.proxy_list = QListWidget()
        self.proxy_list.setSpacing(3)
        self.proxy_list.setStyleSheet(PROXY_LIST_STYLE)
        left.addWidget(self.proxy_list)

        row = QHBoxLayout()
        for label, slot in [
            ("Проверить все", self._check_proxies),
            ("Удалить", self._del_proxy),
        ]:
            b = AnimatedButton(label)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch()
        left.addLayout(row)
        self.active_proxy_lbl = QLabel("Активный прокси: нет")
        self.active_proxy_lbl.setStyleSheet("color: #4e5a78; font-size: 12px;")
        left.addWidget(self.active_proxy_lbl)
        content.addLayout(left, 2)

        right = self._proxy_form("proxy")
        content.addLayout(right, 1)
        lay.addLayout(content)
        return w

    def _build_sys_proxy_page(self):
        w, lay = self._mk_page("Системное прокси", "Используется для добавления аккаунтов, чатов и спамблока")

        content = QHBoxLayout()
        content.setSpacing(28)
        content.addLayout(self._proxy_form("app_proxy"), 1)

        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(section_label("СПИСОК ПРОКСИ"))
        self.app_proxy_list = QListWidget()
        self.app_proxy_list.setSpacing(3)
        self.app_proxy_list.setStyleSheet(PROXY_LIST_STYLE)
        right.addWidget(self.app_proxy_list)
        row = QHBoxLayout()
        for label, slot in [("Использовать", self._set_active_app_proxy), ("Проверить все", self._check_app_proxies), ("Удалить", self._del_app_proxy)]:
            b = AnimatedButton(label)
            b.clicked.connect(slot)
            row.addWidget(b)
        right.addLayout(row)
        self.app_proxy_status_lbl = QLabel("Системное прокси: не задано")
        self.app_proxy_status_lbl.setStyleSheet("color: #4e5a78; font-size: 12px;")
        right.addWidget(self.app_proxy_status_lbl)
        content.addLayout(right, 2)
        lay.addLayout(content)
        return w

    def _proxy_form(self, prefix):
        lay = QVBoxLayout()
        lay.setSpacing(10)
        lay.addWidget(section_label("ДОБАВИТЬ ПРОКСИ"))
        lay.addWidget(section_label("ТИП"))
        cb = styled_combo()
        cb.addItems(["socks5", "socks4", "http"])
        cb.setFixedHeight(38)
        setattr(self, f"{prefix}_type", cb)
        lay.addWidget(cb)
        for lbl_text, attr, ph in [
            ("ХОСТ",                  f"{prefix}_host", "127.0.0.1"),
            ("ПОРТ",                  f"{prefix}_port", "1080"),
            ("ЛОГИН (необязательно)", f"{prefix}_user", "username"),
        ]:
            lay.addWidget(section_label(lbl_text))
            e = QLineEdit()
            e.setPlaceholderText(ph)
            setattr(self, attr, e)
            lay.addWidget(e)
        lay.addWidget(section_label("ПАРОЛЬ (необязательно)"))
        pw = QLineEdit()
        pw.setPlaceholderText("пароль")
        pw.setEchoMode(QLineEdit.Password)
        setattr(self, f"{prefix}_pass", pw)
        lay.addWidget(pw)
        btn = AnimatedButton("+ Добавить")
        slot = self._add_proxy if prefix == "proxy" else self._add_app_proxy
        btn.clicked.connect(slot)
        lay.addWidget(btn)
        lay.addStretch()
        return lay

    def _parse_proxy_form(self, prefix):
        host = getattr(self, f"{prefix}_host").text().strip()
        port = getattr(self, f"{prefix}_port").text().strip()
        if not host or not port:
            QMessageBox.warning(self, "Ошибка", "Укажите хост и порт"); return None
        try:
            port = int(port)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Порт должен быть числом"); return None
        return {
            "type":     getattr(self, f"{prefix}_type").currentText(),
            "host":     host,
            "port":     port,
            "user":     getattr(self, f"{prefix}_user").text().strip(),
            "password": getattr(self, f"{prefix}_pass").text().strip(),
        }

    def _clear_proxy_form(self, prefix):
        for attr in (f"{prefix}_host", f"{prefix}_port", f"{prefix}_user", f"{prefix}_pass"):
            getattr(self, attr).clear()

    def _add_proxy(self):
        p = self._parse_proxy_form("proxy")
        if not p: return
        self.data.setdefault("proxies", []).append(p)
        save_data(self.data)
        self._clear_proxy_form("proxy")
        self._refresh_proxies()

    def _del_proxy(self):
        row = self.proxy_list.currentRow()
        if row < 0: return
        self.data["proxies"].pop(row)
        active = self.data.get("active_proxy_idx", -1)
        if active == row:
            self.data["active_proxy_idx"] = -1
        elif active > row:
            self.data["active_proxy_idx"] = active - 1
        new_st = {k-(k>row): v for k, v in self._proxy_status.items() if k != row}
        self._proxy_status = new_st
        save_data(self.data)
        self._refresh_proxies()

    def _set_active_proxy(self):
        row = self.proxy_list.currentRow()
        if row < 0: return
        self.data["active_proxy_idx"] = row
        save_data(self.data)
        self._refresh_proxies()

    def _refresh_proxies(self):
        self.proxy_list.clear()
        self._proxy_rows = []
        active = self.data.get("active_proxy_idx", -1)
        for i, p in enumerate(self.data.get("proxies", [])):
            rw = ProxyRowWidget(p, i)
            if i in self._proxy_status:
                rw.set_status(self._proxy_status[i])
            rw.set_active(i == active)
            item = QListWidgetItem(self.proxy_list)
            item.setSizeHint(QSize(rw.sizeHint().width(), 42))
            self.proxy_list.addItem(item)
            self.proxy_list.setItemWidget(item, rw)
            self._proxy_rows.append(rw)
        idx = self.data.get("active_proxy_idx", -1)
        proxies = self.data.get("proxies", [])
        if 0 <= idx < len(proxies):
            p = proxies[idx]
            self.active_proxy_lbl.setText(f"Активный: {_proxy_label(p)}")
        else:
            self.active_proxy_lbl.setText("Активный прокси: нет")

    def _check_proxies(self):
        proxies = self.data.get("proxies", [])
        if not proxies:
            QMessageBox.information(self, "Проверка", "Нет прокси для проверки"); return
        for i, rw in enumerate(self._proxy_rows):
            self._proxy_status[i] = "checking"
            rw.set_status("checking")
        chk = ProxyChecker(proxies)
        chk.result_signal.connect(self._on_proxy_result)
        chk.finished_signal.connect(lambda: None)
        threading.Thread(target=chk.run, daemon=True).start()

    def _on_proxy_result(self, idx, ok, info):
        status = "ok" if ok else "err"
        self._proxy_status[idx] = status
        if idx < len(self._proxy_rows):
            self._proxy_rows[idx].set_status(status, info)

    def _check_app_proxies(self):
        proxies = self.data.get("app_proxies", [])
        if not proxies:
            QMessageBox.information(self, "Проверка", "Нет прокси для проверки"); return
        for i, rw in enumerate(self._app_proxy_rows):
            rw.set_status("checking")
        chk = ProxyChecker(proxies)
        chk.result_signal.connect(self._on_app_proxy_result)
        chk.finished_signal.connect(lambda: None)
        threading.Thread(target=chk.run, daemon=True).start()

    def _on_app_proxy_result(self, idx, ok, info):
        status = "ok" if ok else "err"
        if idx < len(self._app_proxy_rows):
            self._app_proxy_rows[idx].set_status(status, info)

    def _add_app_proxy(self):
        p = self._parse_proxy_form("app_proxy")
        if not p: return
        self.data.setdefault("app_proxies", []).append(p)
        save_data(self.data)
        self._clear_proxy_form("app_proxy")
        self._refresh_app_proxies()

    def _del_app_proxy(self):
        row = self.app_proxy_list.currentRow()
        if row < 0: return
        self.data.setdefault("app_proxies", []).pop(row)
        active = self.data.get("active_app_proxy_idx", -1)
        if active == row:
            self.data["active_app_proxy_idx"] = -1
            self.data["app_proxy"] = None
        elif active > row:
            self.data["active_app_proxy_idx"] = active - 1
        save_data(self.data)
        self._refresh_app_proxies()

    def _set_active_app_proxy(self):
        row = self.app_proxy_list.currentRow()
        if row < 0: return
        self.data["active_app_proxy_idx"] = row
        self.data["app_proxy"] = self.data["app_proxies"][row]
        save_data(self.data)
        self._refresh_app_proxies()

    def _refresh_app_proxies(self):
        self.app_proxy_list.clear()
        self._app_proxy_rows = []
        active = self.data.get("active_app_proxy_idx", -1)
        for i, p in enumerate(self.data.get("app_proxies", [])):
            rw = ProxyRowWidget(p, i)
            rw.set_active(i == active)
            item = QListWidgetItem(self.app_proxy_list)
            item.setSizeHint(QSize(rw.sizeHint().width(), 42))
            self.app_proxy_list.addItem(item)
            self.app_proxy_list.setItemWidget(item, rw)
            self._app_proxy_rows.append(rw)
        p = self.data.get("app_proxy")
        if p:
            self.app_proxy_status_lbl.setText(f"Активное: {_proxy_label(p)}")
            self.app_proxy_status_lbl.setStyleSheet("color: #6a9e80; font-size: 12px;")
        else:
            self.app_proxy_status_lbl.setText("Системное прокси: не задано")
            self.app_proxy_status_lbl.setStyleSheet("color: #4e5a78; font-size: 12px;")

    def _get_app_proxy(self):
        return self.data.get("app_proxy") or None

    def _get_active_proxy(self):
        idx = self.data.get("active_proxy_idx", -1)
        proxies = self.data.get("proxies", [])
        return proxies[idx] if 0 <= idx < len(proxies) else None

    def _build_sender_page(self):
        w = FadeWidget()
        w.setStyleSheet("background: #1a1d26;")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(36, 36, 36, 0)
        outer.setSpacing(0)

        h = QLabel("Отписи")
        h.setObjectName("header")
        outer.addWidget(h)
        outer.addSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        sc = QWidget()
        sc.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(sc)
        lay.setContentsMargins(0, 0, 12, 24)
        lay.setSpacing(16)

        self._wc_widget = QWidget()
        self._wc_widget.setStyleSheet("background: transparent;")
        self._wc_layout = QVBoxLayout(self._wc_widget)
        self._wc_layout.setContentsMargins(0, 0, 0, 0)
        self._wc_layout.setSpacing(12)
        lay.addWidget(self._wc_widget)

        add_btn = AnimatedButton("+ Добавить поток")
        add_btn.setFixedWidth(200)
        add_btn.clicked.connect(self._add_worker_card)
        lay.addWidget(add_btn)
        lay.addSpacing(8)
        lay.addWidget(make_sep())
        lay.addSpacing(8)

        glob = QFrame()
        glob.setObjectName("card")
        gl = QHBoxLayout(glob)
        gl.setContentsMargins(20, 16, 20, 16)
        gl.setSpacing(32)

        for attr, lbl_text, mn, mx, default, suffix, hint_text in [
            ("interval_spin",     "ИНТЕРВАЛ СООБЩЕНИЙ (МИН)",    0, 60,   2, " мин", None),
            ("tag_interval_spin", "ИНТЕРВАЛ МЕЖДУ ТЕГАМИ (МИН)", 0, 1440, 0, " мин", "0 = без интервала"),
        ]:
            col = QVBoxLayout()
            col.addWidget(section_label(lbl_text))
            col.addSpacing(6)
            spin = StyledSpinBox()
            spin.setRange(mn, mx)
            spin.setValue(self.data.get("tag_interval_min", 0) if attr == "tag_interval_spin" else default)
            spin.setSuffix(suffix)
            spin.setFixedWidth(160)
            spin.valueChanged.connect(self._update_eta)
            setattr(self, attr, spin)
            col.addWidget(spin)
            h2 = QLabel(hint_text if hint_text else "")
            h2.setStyleSheet("color: #3a4a68; font-size: 11px; background: transparent;")
            h2.setFixedHeight(16)
            col.addWidget(h2)
            col.addStretch()
            gl.addLayout(col)

        time_col = QVBoxLayout()
        time_col.addWidget(section_label("ВРЕМЯ СТАРТА"))
        time_col.addSpacing(6)
        self.start_time_edit = StyledTimeEdit()
        self.start_time_edit.setTime(QTime.currentTime())
        self.start_time_edit.setFixedWidth(160)
        self.start_time_edit.timeChanged.connect(self._update_eta)
        time_col.addWidget(self.start_time_edit)
        h3 = QLabel("")
        h3.setFixedHeight(16)
        time_col.addWidget(h3)
        time_col.addStretch()
        gl.addLayout(time_col)

        eta_col = QVBoxLayout()
        self.eta_lbl = QLabel("")
        self.eta_lbl.setStyleSheet("color: #4a5878; font-size: 12px; background: transparent;")
        self.eta_lbl.setWordWrap(True)
        eta_col.addStretch()
        eta_col.addWidget(self.eta_lbl)
        gl.addLayout(eta_col)
        gl.addStretch()
        lay.addWidget(glob)

        stats = QFrame()
        stats.setObjectName("card")
        sg = QGridLayout(stats)
        sg.setContentsMargins(16, 16, 16, 16)
        sg.setSpacing(12)
        for i in range(4):
            sg.setColumnStretch(i, 1)
        self.stat_total = StatCard("ВСЕГО")
        self.stat_ok    = StatCard("ОТПРАВЛЕНО")
        self.stat_err   = StatCard("ОШИБОК")
        self.stat_left  = StatCard("ОСТАЛОСЬ")
        for i, card in enumerate([self.stat_total, self.stat_ok, self.stat_err, self.stat_left]):
            sg.addWidget(card, 0, i)
        lay.addWidget(stats)

        log_frame = QFrame()
        log_frame.setObjectName("card")
        ll = QVBoxLayout(log_frame)
        ll.setContentsMargins(16, 14, 16, 14)
        ll.setSpacing(8)
        ll.addWidget(section_label("СТАТУС"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(220)
        self.log_view.setStyleSheet(LOG_VIEW_STYLE)
        ll.addWidget(self.log_view)
        lay.addWidget(log_frame)

        scroll.setWidget(sc)
        outer.addWidget(scroll)
        return w

    def _add_worker_card(self):
        self._build_worker_card(len(self._worker_cards))
        self._update_eta()

    def _build_worker_card(self, idx):
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(10)

        title_row = QHBoxLayout()
        lbl = QLabel(f"ПОТОК {idx + 1}")
        lbl.setStyleSheet("background: transparent; font-size: 10px; font-weight: 700; color: #6b82c0; letter-spacing: 1.8px;")
        title_row.addWidget(lbl)
        title_row.addStretch()
        if idx > 0:
            rm = AnimatedButton("Удалить")
            rm.setFixedHeight(28); rm.setFixedWidth(90)
            rm.clicked.connect(lambda _c, i=idx: self._remove_worker_card(i))
            title_row.addWidget(rm)
        cl.addLayout(title_row)

        row1 = QHBoxLayout()
        row1.setSpacing(16)

        acc_combo = styled_combo()
        acc_combo.setFixedHeight(38)
        for acc in self.data["accounts"]:
            acc_combo.addItem(_acc_label(acc))

        proxy_combo = styled_combo()
        proxy_combo.setFixedHeight(38)
        proxy_combo.addItem("Без прокси")
        for p in self.data.get("proxies", []):
            proxy_combo.addItem(_proxy_label(p))

        rec_combo = styled_combo()
        rec_combo.setFixedHeight(38)
        rec_combo.addItem("База")
        for key in self.data.get("recipient_dbs", {}):
            rec_combo.addItem(key)
        rec_combo.currentIndexChanged.connect(self._update_eta)

        for lbl_text, widget in [("АККАУНТ", acc_combo), ("ПРОКСИ", proxy_combo), ("ТЕГИ (БАЗА)", rec_combo)]:
            col = QVBoxLayout()
            col.setSpacing(6)
            l2 = QLabel(lbl_text)
            l2.setStyleSheet("background: transparent; font-size: 10px; font-weight: 700; color: #6b82c0; letter-spacing: 1.8px;")
            col.addWidget(l2)
            col.addWidget(widget)
            row1.addLayout(col, 2)
        cl.addLayout(row1)
        cl.addSpacing(12)

        pastes_col = QVBoxLayout()
        pastes_col.setSpacing(6)
        pl = QLabel("ПАСТЫ")
        pl.setStyleSheet("background: transparent; font-size: 10px; font-weight: 700; color: #6b82c0; letter-spacing: 1.8px;")
        pastes_col.addWidget(pl)
        paste_lw = QListWidget()
        paste_lw.setSelectionMode(QAbstractItemView.NoSelection)
        paste_lw.setMinimumHeight(160)
        paste_lw.setMaximumHeight(300)
        paste_lw.setStyleSheet(PASTE_LIST_STYLE)
        for i, p in enumerate(self.data["pastes"]):
            if not p.strip(): continue
            item = QListWidgetItem(f"  {i+1}.  {p[:40].replace(chr(10), ' ')}")
            item.setData(Qt.UserRole, i)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            paste_lw.addItem(item)
        paste_lw.itemClicked.connect(lambda it: it.setCheckState(
            Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked
        ))
        pastes_col.addWidget(paste_lw)
        cl.addLayout(pastes_col)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        start_btn = AnimatedButton(f"Запустить поток {idx + 1}")
        start_btn.setMinimumHeight(36)
        start_btn.setFixedWidth(220)
        start_btn.clicked.connect(lambda _c, i=idx: self._toggle_worker(i))
        btn_row.addWidget(start_btn)

        pause_btn = AnimatedButton("Пауза")
        pause_btn.setMinimumHeight(36)
        pause_btn.setFixedWidth(110)
        pause_btn.setEnabled(False)
        pause_btn.clicked.connect(lambda _c, i=idx: self._toggle_worker_pause(i))
        btn_row.addWidget(pause_btn)

        cur_tag_lbl = QLabel("")
        cur_tag_lbl.setStyleSheet("color: #6b82c0; font-size: 12px; background: transparent;")
        btn_row.addWidget(cur_tag_lbl)
        btn_row.addStretch()
        cl.addLayout(btn_row)

        self._wc_layout.addWidget(card)
        self._worker_cards.append({
            "card": card, "acc_combo": acc_combo, "proxy_combo": proxy_combo,
            "paste_list": paste_lw, "rec_combo": rec_combo,
            "start_btn": start_btn, "pause_btn": pause_btn,
            "cur_tag_lbl": cur_tag_lbl,
        })

    def _sync_worker_rec_combos(self):
        for cd in self._worker_cards:
            combo = cd["rec_combo"]
            cur = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("База")
            for key in self.data.get("recipient_dbs", {}):
                combo.addItem(key)
            idx = combo.findText(cur)
            combo.setCurrentIndex(max(0, idx))
            combo.blockSignals(False)

    def _remove_worker_card(self, idx):
        if idx >= len(self._worker_cards): return
        if idx in self._workers and self._workers[idx]:
            self._workers[idx].stop()
        cd = self._worker_cards[idx]
        cd["card"].setParent(None)
        cd["card"].deleteLater()
        self._worker_cards.pop(idx)

    def _get_worker_pastes(self, idx):
        if idx >= len(self._worker_cards): return []
        lw = self._worker_cards[idx]["paste_list"]
        result = [self.data["pastes"][lw.item(i).data(Qt.UserRole)]
                  for i in range(lw.count())
                  if lw.item(i).checkState() == Qt.Checked
                  and 0 <= lw.item(i).data(Qt.UserRole) < len(self.data["pastes"])]
        if not result and lw.count() == 0:
            result = [p for p in self.data.get("pastes", []) if p.strip()]
        return result

    def _toggle_worker(self, idx):
        if idx in self._workers and self._workers[idx]:
            self._stop_worker(idx)
        else:
            self._start_worker(idx)

    def _start_worker(self, idx):
        if idx >= len(self._worker_cards): return
        cd = self._worker_cards[idx]
        acc_idx = cd["acc_combo"].currentIndex()
        if acc_idx < 0 or acc_idx >= len(self.data["accounts"]):
            QMessageBox.warning(self, "Ошибка", "Выберите аккаунт"); return
        pastes = self._get_worker_pastes(idx)
        if not pastes:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одну пасту"); return
        key = cd["rec_combo"].currentText() if cd["rec_combo"].currentIndex() > 0 else None
        recs = self.data.get("recipient_dbs", {}).get(key, self.data.get("recipients", [])) if key else self.data.get("recipients", [])
        if not recs:
            QMessageBox.warning(self, "Ошибка", "Нет тегов"); return
        acc = self.data["accounts"][acc_idx]
        pi = cd["proxy_combo"].currentIndex()
        proxy = self.data.get("proxies", [])[pi - 1] if pi > 0 and pi - 1 < len(self.data.get("proxies", [])) else None

        worker = SenderWorker(
            acc, recs, pastes,
            self.interval_spin.value(), len(pastes),
            proxy=proxy,
            tag_interval_min=self.tag_interval_spin.value(),
            worker_id=idx,
            resume_from=self.data.get("worker_last_tag", {}).get(str(idx)),
        )
        worker.log_signal.connect(self._on_log)
        worker.progress_signal.connect(lambda d, t, i=idx: self._on_worker_progress(i, d, t))
        worker.finished_signal.connect(lambda i=idx: self._on_worker_finished(i))
        worker.failed_signal.connect(self._on_failed)
        worker.failed_detail_signal.connect(self._on_failed_detail)
        worker.current_tag_signal.connect(self._on_worker_tag)
        worker.spamblock_signal.connect(self._on_spamblock)
        worker.tag_sent_signal.connect(self._on_tag_sent)

        self._workers[idx] = worker
        self._worker_totals[idx] = len(recs) * len(pastes)
        total = sum(self._worker_totals.values())
        self._total_msgs = total
        self.stat_total.set_value(total)
        self.stat_left.set_value(total - self._done_msgs)
        self.progress_bar.setMaximum(total)
        self.progress_bar.show()
        self._pause_btn.show()

        t = threading.Thread(target=worker.run, daemon=True)
        self._worker_threads[idx] = t

        now = QTime.currentTime()
        target = self.start_time_edit.time()
        now_dt = datetime.now()
        target_dt = now_dt.replace(hour=target.hour(), minute=target.minute(), second=0, microsecond=0)
        if target_dt <= now_dt:
            target_dt = target_dt.replace(day=target_dt.day + 1)
        secs = int((target_dt - now_dt).total_seconds())
        if secs > 10:
            mins, rem = divmod(secs, 60)
            time_str = f"{mins} мин {rem} сек" if mins > 0 else f"{rem} сек"
            self._on_log(f"[W{idx+1}] Старт в {target.toString('HH:mm')} (через {time_str})", "info")
            def _delayed_start(thread=t):
                thread.start()
            timer = threading.Timer(secs, _delayed_start)
            timer.daemon = True
            self._worker_timers[idx] = timer
            timer.start()
        else:
            self._worker_timers.pop(idx, None)
            t.start()

        cd["start_btn"].setText(f"Остановить поток {idx + 1}")
        cd["pause_btn"].setEnabled(True)
        cd["pause_btn"].setText("Пауза")
        cd["cur_tag_lbl"].setText("")
        self._worker_paused[idx] = False
        proxy_info = f"  прокси: {_proxy_label(proxy)}" if proxy else ""
        self._on_log(f"[W{idx+1}] Запущен  {len(recs)} тегов  {len(pastes)} паст{proxy_info}", "info")
        self._run_btn.setText("Остановить все")

    def _stop_worker(self, idx):
        timer = self._worker_timers.pop(idx, None)
        if timer:
            timer.cancel()
        if self._workers.get(idx):
            self._workers[idx].stop()
            self._workers[idx] = None
        self._worker_paused[idx] = False
        if idx < len(self._worker_cards):
            cd = self._worker_cards[idx]
            cd["start_btn"].setText(f"Запустить поток {idx + 1}")
            cd["pause_btn"].setEnabled(False)
            cd["pause_btn"].setText("Пауза")
            cd["cur_tag_lbl"].setText("")
        self._on_log(f"[W{idx+1}] Остановлен", "warn")
        if not any(w for w in self._workers.values()):
            self._run_btn.setText("Начать отписи")
            self.progress_bar.hide()
            self._pause_btn.hide()

    def _toggle_worker_pause(self, idx):
        if not self._workers.get(idx): return
        if self._worker_paused.get(idx):
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

    def _toggle_send(self):
        if any(w for w in self._workers.values()):
            for idx in list(self._workers.keys()):
                self._stop_worker(idx)
            self._run_btn.setText("Начать отписи")
        else:
            for idx in range(len(self._worker_cards)):
                self._start_worker(idx)
            if any(w for w in self._workers.values()):
                self._run_btn.setText("Остановить все")

    def _toggle_pause(self):
        if self._paused:
            for w in self._workers.values():
                if w: w.resume()
            self._paused = False
            self._pause_btn.setText("Пауза")
            self._on_log("Возобновлена", "info")
        else:
            for w in self._workers.values():
                if w: w.pause()
            self._paused = True
            self._pause_btn.setText("Продолжить")
            self._on_log("На паузе", "warn")

    def _on_worker_tag(self, wid, tag):
        if wid < len(self._worker_cards):
            self._worker_cards[wid]["cur_tag_lbl"].setText(f"-> {tag}")
        if "worker_last_tag" not in self.data:
            self.data["worker_last_tag"] = {}
        self.data["worker_last_tag"][str(wid)] = tag
        save_data(self.data)

    def _on_tag_sent(self, wid, tag):
        cd = self._worker_cards[wid] if wid < len(self._worker_cards) else None
        key = cd["rec_combo"].currentText() if cd and cd["rec_combo"].currentIndex() > 0 else None
        if key:
            recs = self.data.get("recipient_dbs", {}).get(key, [])
            self.data["recipient_dbs"][key] = [r for r in recs if (r.get("tag") if isinstance(r, dict) else r) != tag]
        else:
            self.data["recipients"] = [r for r in self.data.get("recipients", []) if (r.get("tag") if isinstance(r, dict) else r) != tag]
        if "worker_last_tag" not in self.data:
            self.data["worker_last_tag"] = {}
        self.data["worker_last_tag"].pop(str(wid), None)
        save_data(self.data)
        self._refresh_recipients()

    def _on_worker_progress(self, wid, done_delta, total_delta):
        self._done_msgs = sum(getattr(w, "_done", 0) for w in self._workers.values() if w)
        total = sum(self._worker_totals.values()) or self._total_msgs
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(self._done_msgs)
        self.stat_left.set_value(max(0, total - self._done_msgs))
        self._update_eta()

    def _on_worker_finished(self, idx):
        self._workers[idx] = None
        self._worker_paused[idx] = False
        if idx < len(self._worker_cards):
            cd = self._worker_cards[idx]
            cd["start_btn"].setText(f"Запустить поток {idx + 1}")
            cd["pause_btn"].setEnabled(False)
            cd["pause_btn"].setText("Пауза")
            cd["cur_tag_lbl"].setText("")
        self.data.setdefault("worker_last_tag", {}).pop(str(idx), None)
        save_data(self.data)
        self._on_log(f"[W{idx+1}] Завершён", "ok")
        if any(w for w in self._workers.values()):
            self._run_btn.setText("Остановить все")
        else:
            self._run_btn.setText("Начать отписи")
            self.progress_bar.hide()
            self._pause_btn.hide()
            self._on_finished_all()

    def _on_finished_all(self):
        if self._failed_tags:
            out = (APP_DIR / "failed_recipients.txt").resolve()
            out.write_text("\n".join(self._failed_tags), encoding="utf-8")
            self._on_log(f"Неудачных: {len(self._failed_tags)}, сохранено в {out}", "warn")
        self._on_log("Все потоки завершены", "ok")
        self._total_msgs = 0
        self._done_msgs  = 0

    def _refresh_sender_page(self):
        if not self._worker_cards:
            self._build_worker_card(0)
        else:
            for cd in self._worker_cards:
                old_acc = cd["acc_combo"].currentIndex()
                cd["acc_combo"].clear()
                for acc in self.data["accounts"]:
                    cd["acc_combo"].addItem(_acc_label(acc))
                if old_acc < cd["acc_combo"].count():
                    cd["acc_combo"].setCurrentIndex(old_acc)

                old_proxy = cd["proxy_combo"].currentIndex()
                cd["proxy_combo"].clear()
                cd["proxy_combo"].addItem("Без прокси")
                for p in self.data.get("proxies", []):
                    cd["proxy_combo"].addItem(_proxy_label(p))
                if old_proxy < cd["proxy_combo"].count():
                    cd["proxy_combo"].setCurrentIndex(old_proxy)

                lw = cd["paste_list"]
                checked = {lw.item(i).data(Qt.UserRole) for i in range(lw.count()) if lw.item(i).checkState() == Qt.Checked}
                lw.clear()
                for i, p in enumerate(self.data["pastes"]):
                    if not p.strip(): continue
                    item = QListWidgetItem(f"  {i+1}.  {p[:40].replace(chr(10), ' ')}")
                    item.setData(Qt.UserRole, i)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked if (i in checked or not checked) else Qt.Unchecked)
                    lw.addItem(item)
        self._update_eta()

    def _update_eta(self):
        if not self._worker_cards:
            self.eta_lbl.setText(""); return
        total_tags = 0
        total_msgs = 0
        for idx, cd in enumerate(self._worker_cards):
            pastes = self._get_worker_pastes(idx)
            key = cd["rec_combo"].currentText() if cd["rec_combo"].currentIndex() > 0 else None
            recs = self.data.get("recipient_dbs", {}).get(key, self.data.get("recipients", [])) if key else self.data.get("recipients", [])
            total_tags += len(recs)
            total_msgs += len(recs) * len(pastes)
        if not total_msgs:
            self.eta_lbl.setText(""); return
        interval = self.interval_spin.value()
        tag_interval = self.tag_interval_spin.value()
        done = self._done_msgs
        remaining_msgs = max(0, total_msgs - done)
        remaining_tags = max(0, total_tags - (done // max(1, total_msgs // max(1, total_tags))))
        mins = remaining_msgs * interval + remaining_tags * tag_interval
        now = datetime.now()
        target = self.start_time_edit.time()
        start_dt = now.replace(hour=target.hour(), minute=target.minute(), second=0, microsecond=0)
        if start_dt < now:
            start_dt = start_dt.replace(day=start_dt.day + 1)
        base_dt = max(now, start_dt)
        end_dt = base_dt + timedelta(minutes=mins)
        self.eta_lbl.setText(f"Конец ~{end_dt.strftime('%H:%M')}  {total_msgs} сообщений")

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

    def _on_failed(self, tag):
        if tag not in self._failed_tags:
            self._failed_tags.append(tag)

    def _on_failed_detail(self, tag, reason):
        if tag not in [e[0] for e in self._failed_entries]:
            self._failed_entries.append((tag, reason))
        self._refresh_logs()

    def _build_chats_page(self):
        w, lay = self._mk_page("Чаты", "Переписка с мамонтами")

        top = QHBoxLayout()
        top.setSpacing(16)
        top.addWidget(section_label("АККАУНТ"))
        self.chat_acc_combo = styled_combo()
        self.chat_acc_combo.setMinimumWidth(260)
        self.chat_acc_combo.setFixedHeight(38)
        top.addWidget(self.chat_acc_combo)
        load = AnimatedButton("Загрузить список")
        load.clicked.connect(self._load_chat_contacts)
        top.addWidget(load)
        top.addStretch()
        lay.addLayout(top)

        content = QHBoxLayout()
        content.setSpacing(16)

        left = QVBoxLayout()
        left.addWidget(section_label("ТЕГИ"))
        self.chat_contacts = QListWidget()
        self.chat_contacts.currentRowChanged.connect(self._open_chat)
        left.addWidget(self.chat_contacts)
        self.chat_status_lbl = QLabel("")
        self.chat_status_lbl.setStyleSheet("color: #4e5a78; font-size: 11px;")
        left.addWidget(self.chat_status_lbl)
        content.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(section_label("ПЕРЕПИСКА"))
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setStyleSheet(MONOSPACE_VIEW_STYLE)
        right.addWidget(self.chat_view)
        content.addLayout(right, 2)
        lay.addLayout(content)
        return w

    def _refresh_chats_accounts(self):
        self.chat_acc_combo.clear()
        for acc in self.data["accounts"]:
            self.chat_acc_combo.addItem(f"{acc.get('name', acc['phone'])}  {acc['phone']}")

    def _load_chat_contacts(self):
        acc_idx = self.chat_acc_combo.currentIndex()
        if acc_idx < 0 or acc_idx >= len(self.data["accounts"]):
            QMessageBox.warning(self, "Ошибка", "Выберите аккаунт"); return
        all_recs = list(self.data.get("recipients", []))
        for db_recs in self.data.get("recipient_dbs", {}).values():
            for r in db_recs:
                if r not in all_recs:
                    all_recs.append(r)
        if not all_recs:
            QMessageBox.warning(self, "Ошибка", "Нет тегов ни в одной базе"); return
        self._chat_recs = all_recs
        self.chat_contacts.clear()
        self.chat_view.clear()
        chat_log = self.data.get("chat_log", {})
        for r in all_recs:
            tag = recipient_tag(r)
            suffix = "  [ответил]" if chat_log.get(tag, {}).get("replied") else ""
            self.chat_contacts.addItem(f"  {tag}{suffix}")
        self.chat_status_lbl.setText("Загружено")

    def _open_chat(self, row):
        if row < 0: return
        acc_idx = self.chat_acc_combo.currentIndex()
        if acc_idx < 0 or acc_idx >= len(self.data["accounts"]): return
        recs = getattr(self, "_chat_recs", self.data.get("recipients", []))
        if row >= len(recs): return
        tag = recipient_tag(recs[row])
        self._chat_dots = 0
        if not hasattr(self, "_chat_timer"):
            self._chat_timer = QTimer()
            self._chat_timer.timeout.connect(self._tick_chat)
        self._chat_timer.start(80)
        self.chat_view.setPlainText("⠋  Загружаем переписку...")
        loader = ChatLoader(self.data["accounts"][acc_idx], tag, proxy=self._get_app_proxy())
        loader.messages_loaded.connect(self._on_chat_loaded)
        loader.error_signal.connect(self._on_chat_error)
        threading.Thread(target=loader.run, daemon=True).start()

    def _tick_chat(self):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._chat_dots = (self._chat_dots + 1) % len(frames)
        self.chat_view.setPlainText(f"{frames[self._chat_dots]}  Загружаем переписку...")

    def _on_chat_error(self, e):
        if hasattr(self, "_chat_timer"):
            self._chat_timer.stop()
        self.chat_view.setPlainText(f"Ошибка: {e}")

    def _on_chat_loaded(self, tag, messages):
        if hasattr(self, "_chat_timer"):
            self._chat_timer.stop()
        self.chat_view.clear()
        if not messages:
            self.chat_view.setPlainText("Нет сообщений"); return
        replied = any(not m["out"] for m in messages)
        log = self.data.setdefault("chat_log", {})
        log.setdefault(tag, {})["replied"] = replied
        save_data(self.data)
        html = []
        for m in messages:
            color  = "#4a6fa5" if m["out"] else "#6a9e80"
            align  = "right"   if m["out"] else "left"
            prefix = "Я"       if m["out"] else tag
            text = m["text"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html.append(
                f'<div style="text-align:{align}; margin:6px 0;">'
                f'<span style="color:#3a4a68; font-size:11px;">{prefix} {m["ts"]}</span><br>'
                f'<span style="color:{color};">{text}</span></div>'
            )
        self.chat_view.setHtml("".join(html))

    def _build_logs_page(self):
        w, lay = self._mk_page("Логи")

        content = QHBoxLayout()
        content.setSpacing(24)

        for attr, title in [("_failed_tags_view", "ТЕГИ БЕЗ ОТВЕТА"), ("_failed_reasons_view", "ПРИЧИНЫ")]:
            col = QVBoxLayout()
            col.addWidget(section_label(title))
            tv = QTextEdit()
            tv.setReadOnly(True)
            tv.setStyleSheet(MONOSPACE_VIEW_STYLE)
            setattr(self, attr, tv)
            col.addWidget(tv)
            content.addLayout(col, 1)
        lay.addLayout(content)

        row = QHBoxLayout()
        row.addStretch()
        clear = AnimatedButton("Очистить")
        clear.clicked.connect(self._clear_logs)
        row.addWidget(clear)
        lay.addLayout(row)
        return w

    def _clear_logs(self):
        self._failed_entries = []
        self._failed_tags_view.clear()
        self._failed_reasons_view.clear()

    def _refresh_logs(self):
        entries = self._failed_entries
        self._failed_tags_view.setPlainText("\n".join(f"{i+1}  {r}" for i, (r, _) in enumerate(entries)))
        self._failed_reasons_view.setPlainText("\n".join(f"{i+1}  {r}  {reason}" for i, (r, reason) in enumerate(entries)))

    def _build_spamblock_page(self):
        w, lay = self._mk_page("Спамблок", "Аккаунты словившие PeerFlood - статус и ручное управление Spam info bot")

        acc_row = QHBoxLayout()
        acc_row.addWidget(section_label("АККАУНТ"))
        self._spam_acc_combo = styled_combo()
        self._spam_acc_combo.setFixedHeight(38)
        self._spam_acc_combo.setMinimumWidth(280)
        acc_row.addWidget(self._spam_acc_combo)
        acc_row.addStretch()
        lay.addLayout(acc_row)

        right = QVBoxLayout()
        right.setSpacing(10)

        right.addWidget(section_label("ОТВЕТ SPAMBOT"))
        self._spam_reply = QTextEdit()
        self._spam_reply.setReadOnly(True)
        self._spam_reply.setMaximumHeight(120)
        self._spam_reply.setStyleSheet(
            "QTextEdit { background: #13161f; border: 1px solid #232840; border-radius: 8px; padding: 10px; color: #dde3f0; font-size: 13px; }"
        )
        right.addWidget(self._spam_reply)

        right.addWidget(section_label("ОСТАНОВЛЕН НА ТЕГЕ"))
        self._spam_tag_lbl = QLabel("")
        self._spam_tag_lbl.setStyleSheet("color: #a8b8d8; font-size: 13px;")
        right.addWidget(self._spam_tag_lbl)

        right.addWidget(section_label("ВАРИАНТЫ ОТВЕТА SPAMBOT"))
        self._spam_btns_frame = QFrame()
        self._spam_btns_frame.setObjectName("card")
        self._spam_btns_frame.setMinimumHeight(80)
        self._spam_btns_lay = QVBoxLayout(self._spam_btns_frame)
        self._spam_btns_lay.setContentsMargins(16, 16, 16, 16)
        self._spam_btns_lay.setSpacing(10)
        right.addWidget(self._spam_btns_frame)

        right.addSpacing(8)
        manual_row = QHBoxLayout()
        self._spam_manual = QLineEdit()
        self._spam_manual.setPlaceholderText("Ввести вручную и отправить...")
        manual_row.addWidget(self._spam_manual)
        send_m = AnimatedButton("Отправить")
        send_m.setFixedWidth(110)
        send_m.clicked.connect(self._send_spam_manual)
        manual_row.addWidget(send_m)
        right.addLayout(manual_row)

        right.addSpacing(8)
        start_btn = AnimatedButton("Отправить /start")
        start_btn.clicked.connect(self._send_spam_start)
        right.addWidget(start_btn)
        right.addStretch()

        content = QHBoxLayout()
        content.setSpacing(20)
        content.addLayout(right, 1)
        lay.addLayout(content)
        return w

    def _refresh_spamblock_page(self):
        if not hasattr(self, "_spam_acc_combo"): return
        cur = self._spam_acc_combo.currentIndex()
        self._spam_acc_combo.clear()
        for acc in self.data.get("accounts", []):
            un = f"@{acc['username']}" if acc.get("username") else ""
            self._spam_acc_combo.addItem(f"{acc.get('name', acc['phone'])}  {un}  {acc['phone']}")
        if cur >= 0:
            self._spam_acc_combo.setCurrentIndex(min(cur, self._spam_acc_combo.count() - 1))

    def _on_switch_spamblock(self):
        self._refresh_spamblock_page()
        if self._spamblock_log:
            self._apply_spamblock_ui(self._spamblock_log[-1])

    def _on_spamblock(self, wid, stopped_tag, reply, buttons):
        acc = None
        if wid < len(self._worker_cards):
            idx = self._worker_cards[wid]["acc_combo"].currentIndex()
            if 0 <= idx < len(self.data["accounts"]):
                acc = self.data["accounts"][idx]
        entry = {
            "worker_id": wid, "acc": acc,
            "acc_name": acc.get("name", acc["phone"]) if acc else f"Поток {wid+1}",
            "stopped_at": stopped_tag, "reply": reply, "buttons": buttons,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
        self._spamblock_log.append(entry)
        self._refresh_spamblock_page()
        self._apply_spamblock_ui(entry)

    def _apply_spamblock_ui(self, entry):
        if not hasattr(self, "_spam_reply"): return
        self._spam_reply.setPlainText(entry.get("reply", ""))
        self._spam_tag_lbl.setText(entry.get("stopped_at", ""))
        self._clear_spam_btns()
        for btn_text in entry.get("buttons", []):
            b = AnimatedButton(btn_text)
            b.setMinimumHeight(44)
            b.clicked.connect(lambda _, t=btn_text, en=entry: self._send_spam_reply(t, en))
            self._spam_btns_lay.addWidget(b)
        if not entry.get("buttons"):
            no = QLabel("Нет кнопок от Spam info bot")
            no.setStyleSheet("color: #4e5a78; font-size: 12px;")
            self._spam_btns_lay.addWidget(no)

    def _clear_spam_btns(self):
        for i in reversed(range(self._spam_btns_lay.count())):
            w = self._spam_btns_lay.itemAt(i).widget()
            if w: w.deleteLater()

    def _send_spam_reply(self, text, entry):
        acc = entry.get("acc")
        if acc:
            self._do_spam_send(acc, text)

    def _send_spam_manual(self):
        text = self._spam_manual.text().strip()
        if not text: return
        acc_idx = self._spam_acc_combo.currentIndex()
        accounts = self.data.get("accounts", [])
        if acc_idx < 0 or acc_idx >= len(accounts):
            QMessageBox.warning(self, "Ошибка", "Выберите аккаунт"); return
        self._do_spam_send(accounts[acc_idx], text)
        self._spam_manual.clear()

    def _send_spam_start(self):
        acc_idx = self._spam_acc_combo.currentIndex()
        accounts = self.data.get("accounts", [])
        if acc_idx < 0 or acc_idx >= len(accounts):
            QMessageBox.warning(self, "Ошибка", "Выберите аккаунт"); return
        self._do_spam_send(accounts[acc_idx], "/start")

    def _do_spam_send(self, acc, text):
        proxy = self._get_app_proxy()
        self._spam_loader = SpamBotLoader(acc, text, proxy)
        self._spam_loader.result_signal.connect(self._on_spambot_result)
        self._spam_loader.error_signal.connect(self._on_spambot_error)
        self._spam_loader.sent_signal.connect(self._on_spambot_sent)
        self._spam_status_dots = 0
        self._spam_status_phase = 0
        if not hasattr(self, "_spam_status_timer"):
            self._spam_status_timer = QTimer()
            self._spam_status_timer.timeout.connect(self._tick_spam_status)
        self._spam_status_timer.start(500)
        self._spam_reply.setPlainText("⠋  Отправляю сообщение...")
        threading.Thread(target=self._spam_loader.run, daemon=True).start()

    def _tick_spam_status(self):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._spam_status_dots = (self._spam_status_dots + 1) % len(frames)
        spin = frames[self._spam_status_dots]
        if self._spam_status_phase == 0:
            self._spam_reply.setPlainText(f"{spin}  Отправляю сообщение...")
        else:
            self._spam_reply.setPlainText(f"{spin}  Жду ответа от SpamBot...")

    def _on_spambot_sent(self):
        self._spam_status_phase = 1

    def _on_spambot_result(self, reply, btns):
        if hasattr(self, "_spam_status_timer"):
            self._spam_status_timer.stop()
        if not hasattr(self, "_spam_reply"): return
        self._spam_reply.setPlainText(reply if reply else "Нет ответа")
        self._spam_tag_lbl.setText("")
        self._clear_spam_btns()
        if btns:
            for btn_text in btns:
                b = AnimatedButton(btn_text)
                b.setMinimumHeight(44)
                b.clicked.connect(lambda _, t=btn_text: self._do_spam_send(
                    self.data["accounts"][self._spam_acc_combo.currentIndex()], t
                ))
                self._spam_btns_lay.addWidget(b)
        else:
            no = QLabel("Нет кнопок от Spam info bot")
            no.setStyleSheet("color: #4e5a78; font-size: 12px;")
            self._spam_btns_lay.addWidget(no)

    def _on_spambot_error(self, err):
        if hasattr(self, "_spam_status_timer"):
            self._spam_status_timer.stop()
        if not hasattr(self, "_spam_reply"): return
        self._spam_reply.setPlainText(f"Ошибка: {err}")

    def _apply_spam_reply(self, acc, reply, btns):
        self._on_spambot_result(reply, btns)

    def _paused(self):
        return getattr(self, "__paused", False)


if __name__ == "__main__":
    import traceback

    def _excepthook(exc_type, exc_value, exc_tb):
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(msg, file=sys.stderr)
        try:
            (APP_DIR / "crash.log").write_text(msg, encoding="utf-8")
        except OSError:
            pass
        try:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Ошибка", msg)
        except RuntimeError:
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

        def _poll():
            if pending_version():
                show_update_dialog(win, STYLE)
            else:
                QTimer.singleShot(2000, _poll)

        threading.Thread(target=check_for_update, daemon=True).start()
        QTimer.singleShot(3000, _poll)
        sys.exit(app.exec_())
    except Exception:
        traceback.print_exc()
        try:
            (APP_DIR / "crash.log").write_text(traceback.format_exc(), encoding="utf-8")
        except OSError:
            pass
