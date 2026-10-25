"""Inställningar som fylls i på inställningssidan och sparas i databasen (i appdata).
Miljövariabler (t.ex. från en gammal .env) används som startvärden om inget är sparat."""
import os

from . import db

# nyckel: (miljövariabel, standardvärde, hemlig?)
DEFS = {
    "tmdb_token": ("TMDB_TOKEN", "", True),
    "tmdb_language": ("TMDB_LANGUAGE", "sv-SE", False),
    "local_posters": ("LOCAL_POSTERS", "1", False),
    "backup_hours": ("BACKUP_HOURS", "24", False),
    "backup_keep": ("BACKUP_KEEP", "14", False),
    "plex_url": ("PLEX_URL", "", False),
    "plex_token": ("PLEX_TOKEN", "", True),
    "jellyfin_url": ("JELLYFIN_URL", "", False),
    "jellyfin_api_key": ("JELLYFIN_API_KEY", "", True),
    "digital_sync_hours": ("DIGITAL_SYNC_HOURS", "6", False),
    "lookup_mymovies": ("LOOKUP_MYMOVIES", "1", False),
    "lookup_upcitemdb": ("LOOKUP_UPCITEMDB", "1", False),
    "ean_db_token": ("EAN_DB_TOKEN", "", True),
    "lookup_musicbrainz": ("LOOKUP_MUSICBRAINZ", "1", False),
    "discogs_token": ("DISCOGS_TOKEN", "", True),
}

_cache: dict | None = None


def _load():
    global _cache
    if _cache is None:
        with db.connect() as con:
            _cache = {r["key"]: r["value"] for r in con.execute("SELECT key, value FROM settings")}
    return _cache


def get(key: str) -> str:
    env, default, _ = DEFS[key]
    value = _load().get(key)
    if value is None:
        value = os.environ.get(env, default)
    return (value or "").strip()


def get_float(key: str) -> float:
    try:
        return float(get(key).replace(",", "."))
    except ValueError:
        return float(DEFS[key][1] or 0)


def get_bool(key: str) -> bool:
    return get(key).lower() in ("1", "true", "ja", "yes", "on")


def public() -> dict:
    """Till inställningssidan. Hemligheter visas aldrig i klartext, bara att de finns."""
    out = {}
    for key, (_, _, secret) in DEFS.items():
        v = get(key)
        out[key] = {"set": bool(v), "hint": ("…" + v[-4:]) if v else ""} if secret else v
    return out


def save(changes: dict):
    global _cache
    with db.connect() as con:
        for key, value in changes.items():
            if key not in DEFS:
                continue
            if DEFS[key][2] and value in (None, "__keep__"):
                continue  # tomt hemligt fält i formuläret = behåll det gamla
            con.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value or "").strip()))
    _cache = None
