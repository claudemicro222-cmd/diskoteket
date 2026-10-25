"""Papperskorgen: borttagna titlar sparas (som hela poster) i 30 dagar och går att ångra."""
import json

from . import db

KEEP_DAYS = 30


def delete(ids: list[int]) -> int:
    """Flytta titlar till papperskorgen (i stället för att ta bort dem direkt)."""
    n = 0
    with db.connect() as con:
        for item_id in ids:
            row = con.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
            if not row:
                continue
            views = [dict(v) for v in con.execute("SELECT date, source FROM views WHERE item_id=?", (item_id,))]
            con.execute("INSERT OR REPLACE INTO trash (id, item) VALUES (?, ?)",
                        (item_id, json.dumps({"item": dict(row), "views": views}, ensure_ascii=False)))
            con.execute("DELETE FROM items WHERE id=?", (item_id,))
            con.execute("DELETE FROM views WHERE item_id=?", (item_id,))
            n += 1
    return n


def list_trash() -> list[dict]:
    with db.connect() as con:
        rows = con.execute("SELECT id, item, deleted FROM trash ORDER BY deleted DESC").fetchall()
    out = []
    for r in rows:
        it = json.loads(r["item"])["item"]
        out.append({"id": r["id"], "deleted": r["deleted"], "kind": it.get("kind"), "title": it.get("title"),
                    "artist": it.get("artist"), "year": it.get("year"), "format": it.get("format"),
                    "poster_path": it.get("poster_path"), "library_id": it.get("library_id")})
    return out


def restore(item_id: int) -> bool:
    with db.connect() as con:
        r = con.execute("SELECT item FROM trash WHERE id=?", (item_id,)).fetchone()
        if not r:
            return False
        data = json.loads(r["item"])
        it = data["item"]
        cols = [c for c in it if c in _columns(con)]
        if not con.execute("SELECT 1 FROM libraries WHERE id=?", (it.get("library_id"),)).fetchone():
            it["library_id"] = con.execute("SELECT MIN(id) FROM libraries").fetchone()[0]  # samlingen är borttagen
        if it.get("clz_index") is not None and con.execute(
                "SELECT 1 FROM items WHERE library_id=? AND clz_index=? AND (kind='music')=?",
                (it["library_id"], it["clz_index"], it.get("kind") == "music")).fetchone():
            it["clz_index"] = None  # en ny import har tagit numret – behåll posten ändå
        con.execute(f"INSERT INTO items ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                    [it[c] for c in cols])
        con.executemany("INSERT INTO views (item_id, date, source) VALUES (?, ?, ?)",
                        [(item_id, v["date"], v.get("source")) for v in data.get("views", [])])
        con.execute("DELETE FROM trash WHERE id=?", (item_id,))
    return True


def purge(days: int = KEEP_DAYS, everything: bool = False) -> int:
    with db.connect() as con:
        if everything:
            return con.execute("DELETE FROM trash").rowcount
        return con.execute("DELETE FROM trash WHERE deleted < datetime('now', 'localtime', ?)",
                           (f"-{int(days)} days",)).rowcount


def _columns(con):
    return {r["name"] for r in con.execute("PRAGMA table_info(items)")}
