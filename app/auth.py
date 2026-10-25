"""Valfri inloggning med lösenord, och en API-nyckel för Home Assistant.

Lösenordet sparas som hash i appdata/auth.json – inte i databasen – så att en återställd
säkerhetskopia aldrig byter eller tar bort lösenordet.
Glömt lösenordet? Ta bort auth.json i appdata-mappen och starta om containern."""
import hashlib
import hmac
import json
import os
import secrets
import time

from . import db

AUTH_PATH = os.path.join(db.CONFIG_DIR, "auth.json")
COOKIE = "diskoteket_session"
MAX_AGE = 365 * 24 * 3600  # ett år – det är en app i hemmet, inte en bank
ITERATIONS = 240_000

_data: dict | None = None


def _load() -> dict:
    global _data
    if _data is None:
        try:
            with open(AUTH_PATH, encoding="utf-8") as f:
                _data = json.load(f)
        except (OSError, ValueError):
            _data = {}
    return _data


def _save(d: dict):
    global _data
    os.makedirs(os.path.dirname(AUTH_PATH), exist_ok=True)
    tmp = AUTH_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f)
    os.replace(tmp, AUTH_PATH)
    try:
        os.chmod(AUTH_PATH, 0o660)
    except OSError:
        pass
    _data = d


def enabled() -> bool:
    return bool(_load().get("hash"))


def _hash(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), iterations).hex()


def set_password(password: str):
    """Nytt lösenord. Alla som var inloggade loggas ut (ny hemlighet för sessionerna)."""
    if len(password) < 4:
        raise ValueError("Lösenordet måste ha minst 4 tecken")
    d = dict(_load())
    salt = secrets.token_hex(16)
    d.update(hash=_hash(password, salt, ITERATIONS), salt=salt, iterations=ITERATIONS,
             secret=secrets.token_hex(32))
    d.setdefault("api_key", secrets.token_urlsafe(24))
    _save(d)


def clear_password():
    d = dict(_load())
    for k in ("hash", "salt", "iterations", "secret"):
        d.pop(k, None)
    _save(d)


def check_password(password: str) -> bool:
    d = _load()
    if not d.get("hash"):
        return False
    return hmac.compare_digest(_hash(password or "", d["salt"], d.get("iterations", ITERATIONS)), d["hash"])


def make_session() -> str:
    ts = str(int(time.time()))
    sig = hmac.new(_load()["secret"].encode(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def valid_session(token: str | None) -> bool:
    d = _load()
    if not token or not d.get("secret") or "." not in token:
        return False
    ts, sig = token.split(".", 1)
    good = hmac.new(d["secret"].encode(), ts.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good) and ts.isdigit() and time.time() - int(ts) < MAX_AGE


def api_key() -> str:
    d = _load()
    if not d.get("api_key"):
        d = {**d, "api_key": secrets.token_urlsafe(24)}
        _save(d)
    return d["api_key"]


def new_api_key() -> str:
    _save({**_load(), "api_key": secrets.token_urlsafe(24)})
    return _load()["api_key"]


def valid_api_key(key: str | None) -> bool:
    return bool(key) and hmac.compare_digest(key, api_key())
