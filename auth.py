import json
import os
import hashlib
import re
import secrets
from datetime import datetime, timedelta

ACCOUNTS_FILE = "accounts.json"
SESSIONS_FILE = "sessions.json"
SESSION_DAYS  = 30


def _load() -> dict:
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(accounts: dict):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)


def _hash(username: str, password: str) -> str:
    raw = f"{username}:{password}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def register(username: str, password: str) -> tuple[bool, str]:
    username = username.strip().lower()
    if not re.match(r"^[a-z0-9_]{3,20}$", username):
        return False, "Логин: 3–20 символов, только латиница, цифры и _"
    if len(password) < 6:
        return False, "Пароль: минимум 6 символов"
    accounts = _load()
    if username in accounts:
        return False, "Пользователь с таким логином уже существует"
    accounts[username] = {
        "password_hash": _hash(username, password),
        "created_at": datetime.now().isoformat(),
    }
    _save(accounts)
    return True, "ok"


def login(username: str, password: str) -> tuple[bool, str]:
    username = username.strip().lower()
    if not username:
        return False, "Введите логин"
    accounts = _load()
    if username not in accounts:
        return False, "Пользователь не найден"
    if accounts[username]["password_hash"] != _hash(username, password):
        return False, "Неверный пароль"
    return True, "ok"


def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
    username = username.strip().lower()
    accounts = _load()
    if username not in accounts:
        return False, "Пользователь не найден"
    if accounts[username]["password_hash"] != _hash(username, old_password):
        return False, "Неверный текущий пароль"
    if len(new_password) < 6:
        return False, "Новый пароль: минимум 6 символов"
    if old_password == new_password:
        return False, "Новый пароль совпадает со старым"
    accounts[username]["password_hash"] = _hash(username, new_password)
    _save(accounts)
    return True, "ok"


def _load_sessions() -> dict:
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_sessions(sessions: dict):
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def create_session(username: str) -> str:
    token    = secrets.token_urlsafe(32)
    expires  = (datetime.now() + timedelta(days=SESSION_DAYS)).isoformat()
    sessions = _load_sessions()
    sessions[token] = {"username": username, "expires": expires}
    _save_sessions(sessions)
    return token


def validate_session(token: str) -> str | None:
    if not token:
        return None
    sessions = _load_sessions()
    entry = sessions.get(token)
    if not entry:
        return None
    try:
        if datetime.fromisoformat(entry["expires"]) < datetime.now():
            del sessions[token]
            _save_sessions(sessions)
            return None
    except Exception:
        return None
    return entry["username"]


def revoke_session(token: str):
    sessions = _load_sessions()
    if token in sessions:
        del sessions[token]
        _save_sessions(sessions)


def get_created_at(username: str) -> str:
    accounts = _load()
    raw = accounts.get(username.strip().lower(), {}).get("created_at", "")
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return raw[:10]
