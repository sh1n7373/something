import re
import json
from pathlib import Path
import sys


def _get_app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


APP_DIR = _get_app_dir()
DATA_FILE = APP_DIR / "data.json"

_DEFAULTS = {
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
    "app_proxies": [],
    "active_app_proxy_idx": -1,
}

_DICT_KEYS = {"chat_log", "account_proxies", "account_recipients"}


def load_data():
    if DATA_FILE.exists():
        try:
            d = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            for key, default in _DEFAULTS.items():
                if key not in d:
                    d[key] = default
            return d
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_DEFAULTS)


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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


def parse_recipient_line(line):
    line = line.strip()
    m = re.match(r'^(@?\S+)\s*[-]\s*(\$\S+)$', line)
    if m:
        tag, token = m.group(1), m.group(2)
    else:
        tag, token = line, ""
    if not tag.startswith("@"):
        tag = "@" + tag
    return tag, token


def parse_recipients_bulk(text):
    result = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            tag, token = parse_recipient_line(line)
            result.append({"tag": tag, "token": token})
    return result
