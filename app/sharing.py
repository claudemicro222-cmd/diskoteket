"""Vänsidan: en hemlig länk där vänner kan bläddra i samlingen (utan att kunna ändra något)
och be om att få låna. Länken slutar fungera när den stängs av eller byts."""
import hmac
import secrets
from datetime import date

from . import db, repo, settings

# Det vänner får se. Inga priser, anteckningar, streckkoder eller namn på den som lånat.
PUBLIC_COLS = ("id, library_id, kind, title, series_name, season, year, format, poster_path, genres, runtime, "
               "director, actors, plot, artist, label, tracks, collection_status, added_date, "
               "(loaned_to IS NOT NULL AND loaned_to != '') AS loaned")


def token() -> str | None:
    with db.connect() as con:
        r = con.execute("SELECT value FROM settings WHERE key='share_token'").fetchone()
    return r["value"] if r and r["value"] else None


def enable() -> str:
    t = secrets.token_urlsafe(18)
    with db.connect() as con:
        con.execute("INSERT INTO settings (key, value) VALUES ('share_token', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (t,))
    settings._cache = None
    return t


def disable():
    with db.connect() as con:
        con.execute("DELETE FROM settings WHERE key='share_token'")
    settings._cache = None


def valid(t: str | None) -> bool:
    current = token()
    return bool(t and current and hmac.compare_digest(t, current))


def items(kind: str = "video", q: str = "", wish: bool = False) -> list[dict]:
    status = repo.WISH if wish else repo.OWNED
    with db.connect() as con:
        rows = [dict(r) for r in con.execute(
            f"SELECT {PUBLIC_COLS} FROM items WHERE {status}{repo._kind(kind)} "
            "ORDER BY COALESCE(series_name, sort_title, title) COLLATE NOCASE, season")]
    if q:
        rows = repo.search_filter(rows, q, "all")
    return rows


def item(item_id: int) -> dict | None:
    with db.connect() as con:
        r = con.execute(f"SELECT {PUBLIC_COLS}, tracklist FROM items WHERE id=? AND {repo.OWNED}", (item_id,)).fetchone()
    return db.row_to_dict(r) if r else None


def request_loan(item_id: int, name: str, message: str = "") -> bool:
    name = (name or "").strip()[:60]
    if not name or not item(item_id):
        return False
    with db.connect() as con:
        if con.execute("SELECT COUNT(*) FROM loan_requests WHERE handled=0").fetchone()[0] > 200:
            return False  # skydd mot att någon fyller databasen
        con.execute("INSERT INTO loan_requests (item_id, name, message) VALUES (?, ?, ?)",
                    (item_id, name, (message or "").strip()[:500] or None))
    return True


def requests(include_handled=False) -> list[dict]:
    with db.connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT r.id, r.item_id, r.name, r.message, r.created, r.handled, i.title, i.artist, i.kind, i.poster_path, "
            "i.loaned_to FROM loan_requests r LEFT JOIN items i ON i.id = r.item_id "
            + ("" if include_handled else "WHERE r.handled=0 ") + "ORDER BY r.created DESC")]


def handle(request_id: int, lend: bool, due_date: str | None = None) -> dict | None:
    """Godkänn (låna ut till den som frågade) eller avböj en förfrågan."""
    with db.connect() as con:
        r = con.execute("SELECT * FROM loan_requests WHERE id=?", (request_id,)).fetchone()
        if not r:
            return None
        con.execute("UPDATE loan_requests SET handled=1 WHERE id=?", (request_id,))
    if lend:
        repo.update(r["item_id"], {"loaned_to": r["name"], "loan_date": date.today().isoformat(), "due_date": due_date})
    return dict(r)
