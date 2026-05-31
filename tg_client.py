import asyncio
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal

from storage import APP_DIR, recipient_tag, recipient_token, apply_token

SESSION_DIR = APP_DIR / "sessions"
SESSION_DIR.mkdir(exist_ok=True)

try:
    from telethon import TelegramClient
    from telethon.errors import (
        FloodWaitError, UserPrivacyRestrictedError,
        UsernameNotOccupiedError, PeerFloodError,
        SessionPasswordNeededError,
    )
except ImportError:
    raise

try:
    import socks
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False

_SKIP_ERRORS = (
    "database is locked", "user not found", "username invalid",
    "nobody", "you have been blocked", "user is blocked",
    "chat write forbidden", "not in the chat", "banned",
    "deactivated", "need to buy", "paid", "slowmode",
    "allow_payment_required", "no user has", "as username",
)


def _session_wal(phone, chat_mode=False):
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
        except sqlite3.OperationalError:
            pass


def build_client(acc, proxy=None, chat_mode=False):
    base = acc["phone"].replace("+", "")
    sess = str(SESSION_DIR / (base + ("_chat" if chat_mode else "")))
    kwargs = {"connection_retries": 5, "retry_delay": 2}
    if proxy and SOCKS_AVAILABLE:
        ptype = proxy.get("type", "socks5").lower()
        pt = {"socks5": socks.SOCKS5, "socks4": socks.SOCKS4}.get(ptype, socks.HTTP)
        kwargs["proxy"] = (
            pt, proxy["host"], int(proxy["port"]), True,
            proxy.get("user") or None, proxy.get("password") or None,
        )
    return TelegramClient(sess, acc["api_id"], acc["api_hash"], **kwargs)


_COUNTRY_FLAGS = {
    "AD": "🇦🇩", "AE": "🇦🇪", "AF": "🇦🇫", "AG": "🇦🇬", "AI": "🇦🇮",
    "AL": "🇦🇱", "AM": "🇦🇲", "AO": "🇦🇴", "AR": "🇦🇷", "AS": "🇦🇸",
    "AT": "🇦🇹", "AU": "🇦🇺", "AW": "🇦🇼", "AX": "🇦🇽", "AZ": "🇦🇿",
    "BA": "🇧🇦", "BB": "🇧🇧", "BD": "🇧🇩", "BE": "🇧🇪", "BF": "🇧🇫",
    "BG": "🇧🇬", "BH": "🇧🇭", "BI": "🇧🇮", "BJ": "🇧🇯", "BL": "🇧🇱",
    "BM": "🇧🇲", "BN": "🇧🇳", "BO": "🇧🇴", "BQ": "🇧🇶", "BR": "🇧🇷",
    "BS": "🇧🇸", "BT": "🇧🇹", "BW": "🇧🇼", "BY": "🇧🇾", "BZ": "🇧🇿",
    "CA": "🇨🇦", "CC": "🇨🇨", "CD": "🇨🇩", "CF": "🇨🇫", "CG": "🇨🇬",
    "CH": "🇨🇭", "CI": "🇨🇮", "CK": "🇨🇰", "CL": "🇨🇱", "CM": "🇨🇲",
    "CN": "🇨🇳", "CO": "🇨🇴", "CR": "🇨🇷", "CU": "🇨🇺", "CV": "🇨🇻",
    "CW": "🇨🇼", "CX": "🇨🇽", "CY": "🇨🇾", "CZ": "🇨🇿", "DE": "🇩🇪",
    "DJ": "🇩🇯", "DK": "🇩🇰", "DM": "🇩🇲", "DO": "🇩🇴", "DZ": "🇩🇿",
    "EC": "🇪🇨", "EE": "🇪🇪", "EG": "🇪🇬", "EH": "🇪🇭", "ER": "🇪🇷",
    "ES": "🇪🇸", "ET": "🇪🇹", "FI": "🇫🇮", "FJ": "🇫🇯", "FK": "🇫🇰",
    "FM": "🇫🇲", "FO": "🇫🇴", "FR": "🇫🇷", "GA": "🇬🇦", "GB": "🇬🇧",
    "GD": "🇬🇩", "GE": "🇬🇪", "GF": "🇬🇫", "GG": "🇬🇬", "GH": "🇬🇭",
    "GI": "🇬🇮", "GL": "🇬🇱", "GM": "🇬🇲", "GN": "🇬🇳", "GP": "🇬🇵",
    "GQ": "🇬🇶", "GR": "🇬🇷", "GT": "🇬🇹", "GU": "🇬🇺", "GW": "🇬🇼",
    "GY": "🇬🇾", "HK": "🇭🇰", "HN": "🇭🇳", "HR": "🇭🇷", "HT": "🇭🇹",
    "HU": "🇭🇺", "ID": "🇮🇩", "IE": "🇮🇪", "IL": "🇮🇱", "IM": "🇮🇲",
    "IN": "🇮🇳", "IO": "🇮🇴", "IQ": "🇮🇶", "IR": "🇮🇷", "IS": "🇮🇸",
    "IT": "🇮🇹", "JE": "🇯🇪", "JM": "🇯🇲", "JO": "🇯🇴", "JP": "🇯🇵",
    "KE": "🇰🇪", "KG": "🇰🇬", "KH": "🇰🇭", "KI": "🇰🇮", "KM": "🇰🇲",
    "KN": "🇰🇳", "KP": "🇰🇵", "KR": "🇰🇷", "KW": "🇰🇼", "KY": "🇰🇾",
    "KZ": "🇰🇿", "LA": "🇱🇦", "LB": "🇱🇧", "LC": "🇱🇨", "LI": "🇱🇮",
    "LK": "🇱🇰", "LR": "🇱🇷", "LS": "🇱🇸", "LT": "🇱🇹", "LU": "🇱🇺",
    "LV": "🇱🇻", "LY": "🇱🇾", "MA": "🇲🇦", "MC": "🇲🇨", "MD": "🇲🇩",
    "ME": "🇲🇪", "MF": "🇲🇫", "MG": "🇲🇬", "MH": "🇲🇭", "MK": "🇲🇰",
    "ML": "🇲🇱", "MM": "🇲🇲", "MN": "🇲🇳", "MO": "🇲🇴", "MP": "🇲🇵",
    "MQ": "🇲🇶", "MR": "🇲🇷", "MS": "🇲🇸", "MT": "🇲🇹", "MU": "🇲🇺",
    "MV": "🇲🇻", "MW": "🇲🇼", "MX": "🇲🇽", "MY": "🇲🇾", "MZ": "🇲🇿",
    "NA": "🇳🇦", "NC": "🇳🇨", "NE": "🇳🇪", "NF": "🇳🇫", "NG": "🇳🇬",
    "NI": "🇳🇮", "NL": "🇳🇱", "NO": "🇳🇴", "NP": "🇳🇵", "NR": "🇳🇷",
    "NU": "🇳🇺", "NZ": "🇳🇿", "OM": "🇴🇲", "PA": "🇵🇦", "PE": "🇵🇪",
    "PF": "🇵🇫", "PG": "🇵🇬", "PH": "🇵🇭", "PK": "🇵🇰", "PL": "🇵🇱",
    "PM": "🇵🇲", "PR": "🇵🇷", "PS": "🇵🇸", "PT": "🇵🇹", "PW": "🇵🇼",
    "PY": "🇵🇾", "QA": "🇶🇦", "RE": "🇷🇪", "RO": "🇷🇴", "RS": "🇷🇸",
    "RU": "🇷🇺", "RW": "🇷🇼", "SA": "🇸🇦", "SB": "🇸🇧", "SC": "🇸🇨",
    "SD": "🇸🇩", "SE": "🇸🇪", "SG": "🇸🇬", "SH": "🇸🇭", "SI": "🇸🇮",
    "SJ": "🇸🇯", "SK": "🇸🇰", "SL": "🇸🇱", "SM": "🇸🇲", "SN": "🇸🇳",
    "SO": "🇸🇴", "SR": "🇸🇷", "SS": "🇸🇸", "ST": "🇸🇹", "SV": "🇸🇻",
    "SX": "🇸🇽", "SY": "🇸🇾", "SZ": "🇸🇿", "TC": "🇹🇨", "TD": "🇹🇩",
    "TF": "🇹🇫", "TG": "🇹🇬", "TH": "🇹🇭", "TJ": "🇹🇯", "TK": "🇹🇰",
    "TL": "🇹🇱", "TM": "🇹🇲", "TN": "🇹🇳", "TO": "🇹🇴", "TR": "🇹🇷",
    "TT": "🇹🇹", "TV": "🇹🇻", "TW": "🇹🇼", "TZ": "🇹🇿", "UA": "🇺🇦",
    "UG": "🇺🇬", "US": "🇺🇸", "UY": "🇺🇾", "UZ": "🇺🇿", "VA": "🇻🇦",
    "VC": "🇻🇨", "VE": "🇻🇪", "VG": "🇻🇬", "VI": "🇻🇮", "VN": "🇻🇳",
    "VU": "🇻🇺", "WF": "🇼🇫", "WS": "🇼🇸", "YE": "🇾🇪", "YT": "🇾🇹",
    "ZA": "🇿🇦", "ZM": "🇿🇲", "ZW": "🇿🇼",
}


class ProxyChecker(QObject):
    result_signal   = pyqtSignal(int, bool, str)
    finished_signal = pyqtSignal()

    def __init__(self, proxies):
        super().__init__()
        self.proxies = proxies
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        asyncio.new_event_loop().run_until_complete(self._run())
        self.finished_signal.emit()

    async def _run(self):
        for i, p in enumerate(self.proxies):
            if self._stop:
                return
            ok, info = await self._check(p)
            self.result_signal.emit(i, ok, info)

    async def _check(self, proxy):
        if not SOCKS_AVAILABLE:
            return False, "PySocks не установлен"
        try:
            ptype = proxy.get("type", "socks5").lower()
            pt = {"socks5": socks.SOCKS5, "socks4": socks.SOCKS4}.get(ptype, socks.HTTP)
            s = socks.socksocket()
            s.set_proxy(pt, proxy["host"], int(proxy["port"]), True,
                        proxy.get("user") or None, proxy.get("password") or None)
            s.settimeout(8)
            loop = asyncio.get_event_loop()
            targets = [
                ("api.telegram.org", 443),
                ("google.com", 443),
                ("1.1.1.1", 443),
                ("8.8.8.8", 53),
            ]
            connected = False
            for host, port in targets:
                try:
                    s2 = socks.socksocket()
                    s2.set_proxy(pt, proxy["host"], int(proxy["port"]), True,
                                proxy.get("user") or None, proxy.get("password") or None)
                    s2.settimeout(6)
                    await loop.run_in_executor(None, lambda h=host, p=port, sock=s2: sock.connect((h, p)))
                    s2.close()
                    connected = True
                    break
                except Exception:
                    try: s2.close()
                    except Exception: pass
            s.close()
            if not connected:
                return False, "Нет соединения"
            flag = await self._get_flag(proxy["host"])
            return True, f"OK|{flag}"
        except Exception as ex:
            return False, str(ex)[:60]

    async def _get_flag(self, host):
        try:
            import urllib.request, json
            loop = asyncio.get_event_loop()
            def _fetch():
                with urllib.request.urlopen(f"http://ip-api.com/json/{host}?fields=countryCode", timeout=4) as r:
                    return json.loads(r.read().decode()).get("countryCode", "")
            code = await loop.run_in_executor(None, _fetch)
            return code.upper()
        except Exception:
            return ""


class SenderWorker(QObject):
    log_signal          = pyqtSignal(str, str)
    progress_signal     = pyqtSignal(int, int)
    finished_signal     = pyqtSignal()
    failed_signal       = pyqtSignal(str)
    failed_detail_signal = pyqtSignal(str, str)
    current_tag_signal  = pyqtSignal(int, str)
    spamblock_signal    = pyqtSignal(int, str, str, list)

    def __init__(self, account, recipients, pastes, interval_min,
                 pastes_per_recipient, proxy=None, tag_interval_min=0, worker_id=0):
        super().__init__()
        self.account             = account
        self.recipients          = recipients
        self.pastes              = pastes
        self.interval_min        = interval_min
        self.pastes_per_recipient = pastes_per_recipient
        self.proxy               = proxy
        self.tag_interval_min    = tag_interval_min
        self.worker_id           = worker_id
        self._stop  = False
        self._pause = False
        self._done  = 0

    def stop(self):   self._stop  = True
    def pause(self):  self._pause = True
    def resume(self): self._pause = False

    async def _sleep(self, seconds):
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
        asyncio.new_event_loop().run_until_complete(self._send_all())
        self.finished_signal.emit()

    def _log(self, msg, lvl):
        self.log_signal.emit(f"[W{self.worker_id+1}] {msg}", lvl)

    async def _send_all(self):
        acc = self.account
        _session_wal(acc["phone"])
        client = build_client(acc, self.proxy)

        for attempt in range(3):
            try:
                await client.connect()
                break
            except Exception as ex:
                if "database is locked" in str(ex).lower() and attempt < 2:
                    self._log("База заблокирована, повтор...", "warn")
                    await asyncio.sleep(3)
                else:
                    self._log(f"Ошибка подключения: {ex}", "err")
                    return

        if not await client.is_user_authorized():
            self._log("Аккаунт не авторизован", "err")
            await client.disconnect()
            return

        total = len(self.recipients) * len(self.pastes)
        self._done = 0
        first = True

        for rec in self.recipients:
            tag   = recipient_tag(rec)
            token = recipient_token(rec)

            if not first:
                wait = self.tag_interval_min if self.tag_interval_min > 0 else self.interval_min
                if wait > 0:
                    if self.tag_interval_min > 0:
                        self._log(f"Ждём {self.tag_interval_min} мин...", "info")
                    await self._sleep(wait * 60)
                if self._stop:
                    await client.disconnect()
                    return
            first = False
            self.current_tag_signal.emit(self.worker_id, tag)

            for i, paste in enumerate(self.pastes):
                if self._stop:
                    self._log("Остановлена", "warn")
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
                    self._log(f"ok  {tag}", "ok")
                except FloodWaitError as e:
                    self._log(f"Flood {e.seconds}s  {tag}", "warn")
                    await self._sleep(e.seconds)
                except (UserPrivacyRestrictedError, UsernameNotOccupiedError):
                    self._log(f"Недоступен  {tag}", "warn")
                    self.failed_signal.emit(tag)
                    self.failed_detail_signal.emit(tag, "Приватность или пользователь не найден")
                    self._done += 1
                    self.progress_signal.emit(self._done, total)
                    break
                except PeerFloodError:
                    self._log("PeerFlood - опрашиваем SpamBot...", "err")
                    reply, buttons = await self._query_spambot(client)
                    self.spamblock_signal.emit(self.worker_id, tag, reply, buttons)
                    await client.disconnect()
                    return
                except Exception as ex:
                    err_str = str(ex).lower()
                    if "database is locked" in err_str:
                        self._log("База заблокирована, ждём...", "warn")
                        await asyncio.sleep(5)
                    elif "disconnected" in err_str or "not connected" in err_str:
                        self._log(f"Соединение потеряно на {tag}, переподключаем...", "warn")
                        attempt = 0
                        while True:
                            if self._stop:
                                await client.disconnect()
                                return
                            await asyncio.sleep(4)
                            attempt += 1
                            try:
                                await client.connect()
                                self._log(f"Соединение восстановлено, продолжаем с {tag}", "ok")
                                break
                            except Exception:
                                self._log(f"Переподключение {attempt}...", "warn")
                    elif any(e in err_str for e in _SKIP_ERRORS):
                        if "allow_payment_required" in err_str:
                            self._log(f"Скип {tag}: требуется оплата", "warn")
                        elif "no user has" in err_str or "as username" in err_str:
                            self._log(f"Скип {tag}: тег не существует", "warn")
                        else:
                            self._log(f"Скип {tag}: {ex}", "warn")
                        self.failed_signal.emit(tag)
                        self.failed_detail_signal.emit(tag, str(ex))
                        self._done += 1
                        self.progress_signal.emit(self._done, total)
                        break
                    else:
                        self._log(f"err  {tag}: {ex}", "err")
                        self.failed_signal.emit(tag)
                        self.failed_detail_signal.emit(tag, str(ex))
                else:
                    self._done += 1
                    self.progress_signal.emit(self._done, total)
                    if i < len(self.pastes) - 1 and self.interval_min > 0:
                        await self._sleep(self.interval_min * 60)
                    continue
                self._done += 1
                self.progress_signal.emit(self._done, total)
                if i < len(self.pastes) - 1 and self.interval_min > 0:
                    await self._sleep(self.interval_min * 60)

        await client.disconnect()

    async def _query_spambot(self, source_client):
        last_reply, buttons = "", []
        try:
            sb = build_client(self.account, self.proxy)
            await sb.connect()
            for attempt in range(3):
                await sb.send_message("@SpamBot", "/start")
                self._log(f"SpamBot /start попытка {attempt+1}/3", "warn")
                reply_text, btn_labels = "", []
                for _ in range(5):
                    await asyncio.sleep(3)
                    async for m in sb.iter_messages("@SpamBot", limit=5):
                        if not m.out and m.message:
                            reply_text = m.message
                            if m.reply_markup:
                                try:
                                    for row in m.reply_markup.rows:
                                        for btn in row.buttons:
                                            if hasattr(btn, "text"):
                                                btn_labels.append(btn.text)
                                except AttributeError:
                                    pass
                            break
                    if reply_text:
                        break
                if reply_text:
                    last_reply, buttons = reply_text, btn_labels
                    self._log(f"SpamBot: {reply_text[:100]}", "warn")
                if attempt < 2:
                    await asyncio.sleep(15)
            await sb.disconnect()
        except Exception as ex:
            self._log(f"SpamBot ошибка: {ex}", "err")
        return last_reply, buttons


class SpamBotLoader(QObject):
    result_signal = pyqtSignal(str, list)
    error_signal  = pyqtSignal(str)
    sent_signal   = pyqtSignal()

    def __init__(self, account, text, proxy=None):
        super().__init__()
        self.account = account
        self.text    = text
        self.proxy   = proxy

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._load())

    async def _load(self):
        _session_wal(self.account["phone"], chat_mode=True)
        try:
            client = build_client(self.account, self.proxy, chat_mode=True)
            await client.connect()
            if not await client.is_user_authorized():
                self.error_signal.emit("Аккаунт не авторизован")
                await client.disconnect()
                return
            await client.send_message("@SpamBot", self.text)
            self.sent_signal.emit()
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


class ChatLoader(QObject):
    messages_loaded = pyqtSignal(str, list)
    error_signal    = pyqtSignal(str)

    def __init__(self, account, recipient, proxy=None):
        super().__init__()
        self.account   = account
        self.recipient = recipient
        self.proxy     = proxy

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._load())

    async def _load(self):
        _session_wal(self.account["phone"], chat_mode=True)
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
                        msgs.append({
                            "sender": "Я" if msg.out else self.recipient,
                            "text": msg.message,
                            "ts": msg.date.strftime("%d.%m %H:%M"),
                            "out": msg.out,
                        })
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
