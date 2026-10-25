"""Frågor mot databasen: samlingar, listor, filter, statistik, slump, Home Assistant och backup.
Ingen webbkod här, så allt går att testa fristående. lib=None betyder 'alla samlingar'."""
import glob
import os
import re
import sqlite3
from datetime import date, datetime

from . import db, settings

LIST_COLS = ("id, library_id, kind, title, series_name, season, year, format, poster_path, barcode, watched, "
             "genres, sort_title, location, loaned_to, due_date, collection_status, my_rating, "
             "added_date, runtime, collection_id, collection_name, tmdb_id, imdb_id, enriched")

WISH = "(collection_status LIKE '%wish%')"
SOLD = "(collection_status LIKE '%sold%')"
OWNED = f"(collection_status IS NULL OR NOT ({WISH} OR {SOLD}))"
DIGITAL = ("(EXISTS (SELECT 1 FROM digital d WHERE (d.imdb_id IS NOT NULL AND d.imdb_id = items.imdb_id) "
           "OR (d.tmdb_id IS NOT NULL AND d.tmdb_id = items.tmdb_id AND d.kind = items.kind)))")

SORTS = {
    "title": "COALESCE(series_name, sort_title, title) COLLATE NOCASE, season",
    "year": "year DESC, COALESCE(series_name, sort_title, title) COLLATE NOCASE, season",
    "year_asc": "year, COALESCE(series_name, sort_title, title) COLLATE NOCASE, season",
    "added": "added_date DESC, id DESC",
    "rating": "COALESCE(my_rating, 0) DESC, imdb_rating DESC",
    "imdb": "imdb_rating DESC",
    "runtime": "runtime",
}

# Fält som 'Uppdatera metadata' kan skriva över – men inte om du har ändrat dem själv
LOCKABLE = {"title", "original_title", "year", "series_name", "season", "poster_path", "plot",
            "genres", "runtime", "director", "actors"}
# Interna fält som aldrig låses. Allt annat du ändrar i appen låses, så att en ny CLZ-import
# eller 'Uppdatera metadata' inte skriver över det.
NEVER_LOCK = {"tmdb_id", "imdb_id", "collection_id", "collection_name", "enriched", "coll_checked", "library_id", "kind"}


def _lib(lib, prefix=" AND "):
    return (f"{prefix}library_id=?", [lib]) if lib else ("", [])


# ---------- Samlingar ----------

def libraries():
    with db.connect() as con:
        return [dict(r) for r in con.execute(
            f"SELECT l.id, l.name, l.created, "
            f"(SELECT COUNT(*) FROM items i WHERE i.library_id=l.id AND {OWNED.replace('collection_status', 'i.collection_status')}) AS owned, "
            f"(SELECT COUNT(*) FROM items i WHERE i.library_id=l.id AND {WISH.replace('collection_status', 'i.collection_status')}) AS wish "
            "FROM libraries l ORDER BY l.id")]


def library(lib_id):
    with db.connect() as con:
        row = con.execute("SELECT id, name FROM libraries WHERE id=?", (lib_id,)).fetchone()
    return dict(row) if row else None


def create_library(name):
    with db.connect() as con:
        cur = con.execute("INSERT INTO libraries (name) VALUES (?)", (name.strip(),))
        return cur.lastrowid


def rename_library(lib_id, name):
    with db.connect() as con:
        con.execute("UPDATE libraries SET name=? WHERE id=?", (name.strip(), lib_id))


def delete_library(lib_id):
    with db.connect() as con:
        n = con.execute("SELECT COUNT(*) FROM items WHERE library_id=?", (lib_id,)).fetchone()[0]
        con.execute("DELETE FROM items WHERE library_id=?", (lib_id,))
        con.execute("DELETE FROM libraries WHERE id=?", (lib_id,))
    return n


# ---------- Listor ----------

def list_items(lib=None, q="", kind="", status="owned", format="", genre="", location="", watched="",
               digital="", sort="title", missing_poster=False, collection_id=None):
    sql = f"SELECT {LIST_COLS}, {DIGITAL} AS digital FROM items WHERE 1=1"
    s, args = _lib(lib)
    sql += s
    if status == "owned":
        sql += f" AND {OWNED}"
    elif status == "wish":
        sql += f" AND {WISH}"
    elif status == "loaned":
        sql += f" AND {OWNED} AND loaned_to IS NOT NULL AND loaned_to != ''"
    if kind in ("movie", "tv"):
        sql += " AND kind=?"
        args.append(kind)
    if format:
        sql += " AND format=?"
        args.append(format)
    if genre:
        sql += " AND (' | ' || genres || ' | ') LIKE ?"
        args.append(f"% | {genre} | %")
    if location:
        sql += " AND location=?"
        args.append(location)
    if watched in ("0", "1"):
        sql += " AND COALESCE(watched, 0)=?"
        args.append(int(watched))
    if digital == "yes":
        sql += f" AND {DIGITAL}"
    elif digital == "no":
        sql += f" AND NOT {DIGITAL}"
    if missing_poster:
        sql += " AND (poster_path IS NULL OR poster_path = '')"
    if collection_id:
        sql += " AND collection_id=?"
        args.append(collection_id)
    if q:
        sql = sql.replace(" FROM items", ", original_title, actors, director FROM items", 1)
    sql += " ORDER BY " + SORTS.get(sort, SORTS["title"])
    with db.connect() as con:
        rows = [dict(r) for r in con.execute(sql, args)]
    return search_filter(rows, q) if q else rows


def search_filter(rows, q):
    """Fritextsökning. Görs i Python så att å/ä/ö fungerar oavsett stora/små bokstäver.
    Titlar matchar var som helst, men personnamn bara i början av ett ord –
    annars ger 'bert' alla filmer med Robert, Albert och Herbert."""
    q = q.strip().lower()
    word = re.compile(r"(?:^|[\s\-.'(])" + re.escape(q))
    digits = re.sub(r"\D", "", q)
    scored = []
    for r in rows:
        titles = [(r.get(k) or "").lower() for k in ("title", "original_title", "series_name")]
        people = [n.strip().lower() for k in ("actors", "director") for n in (r.get(k) or "").split(" | ") if n.strip()]
        if digits and len(digits) >= 8 and r.get("barcode") and digits.lstrip("0") == r["barcode"].lstrip("0"):
            score = 0
        elif any(t.startswith(q) for t in titles):
            score = 1
        elif any(word.search(t) for t in titles):
            score = 2
        elif any(q in t for t in titles):
            score = 3
        elif any(word.search(p) for p in people):
            score = 4
        else:
            continue
        for k in ("original_title", "actors", "director"):
            r.pop(k, None)
        scored.append((score, r))
    scored.sort(key=lambda x: x[0])  # stabil: inom samma nivå behålls vald sortering
    return [r for _, r in scored]


def facets(lib=None):
    """Värden till filtermenyerna."""
    s, a = _lib(lib)
    with db.connect() as con:
        formats = [r[0] for r in con.execute(
            f"SELECT format FROM items WHERE format IS NOT NULL AND format != '' AND {OWNED}{s} "
            "GROUP BY format ORDER BY COUNT(*) DESC", a)]
        locations = [r[0] for r in con.execute(
            f"SELECT location FROM items WHERE location IS NOT NULL AND location != '' AND {OWNED}{s} "
            "GROUP BY location ORDER BY location", a)]
        genres = {}
        for (g,) in con.execute(f"SELECT genres FROM items WHERE genres IS NOT NULL AND {OWNED}{s}", a):
            for name in g.split(" | "):
                if name.strip():
                    genres[name.strip()] = genres.get(name.strip(), 0) + 1
        has_digital = con.execute("SELECT COUNT(*) FROM digital").fetchone()[0] > 0
    return {"formats": formats, "locations": locations,
            "genres": sorted(genres, key=lambda k: -genres[k]), "digital": has_digital}


def get(item_id):
    with db.connect() as con:
        row = con.execute(f"SELECT items.*, {DIGITAL} AS digital, l.name AS library_name FROM items "
                          "LEFT JOIN libraries l ON l.id = items.library_id WHERE items.id=?", (item_id,)).fetchone()
        if not row:
            return None
        d = db.row_to_dict(row)
        d["digital_sources"] = [r[0] for r in con.execute(
            "SELECT DISTINCT source FROM digital WHERE (imdb_id IS NOT NULL AND imdb_id=?) "
            "OR (tmdb_id IS NOT NULL AND tmdb_id=? AND kind=?)", (d["imdb_id"], d["tmdb_id"], d["kind"]))]
    return d


EDITABLE = {"title", "year", "format", "edition", "barcode", "location", "notes", "my_rating", "watched",
            "loaned_to", "loan_date", "due_date", "collection_status", "season", "series_name",
            "purchase_price", "added_date", "tmdb_id", "poster_path", "plot", "imdb_id", "collection_id",
            "collection_name", "library_id", "original_title", "genres", "runtime", "director", "actors",
            "enriched", "coll_checked", "kind"}


def update(item_id, changes: dict, lock=True, unlock=()):
    """Spara ändringar. Med lock=True låses fälten som ändrats, så att en ny CLZ-import
    eller 'Uppdatera metadata' inte skriver över dem senare."""
    changes = {k: v for k, v in changes.items() if k in EDITABLE}
    with db.connect() as con:
        cur = con.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        if not cur:
            return None
        locked = set(f for f in (cur["locked"] or "").split(",") if f) - set(unlock)
        if lock:
            locked |= {k for k, v in changes.items() if k not in NEVER_LOCK and cur[k] != v}
        sets = [f"{k}=?" for k in changes] + ["locked=?"]
        con.execute(f"UPDATE items SET {', '.join(sets)} WHERE id=?",
                    [*changes.values(), ",".join(sorted(locked)) or None, item_id])
    return get(item_id)


def clear_locks(item_id):
    with db.connect() as con:
        con.execute("UPDATE items SET locked=NULL WHERE id=?", (item_id,))


def find_existing(lib=None, tmdb_id=None, imdb_id=None, barcode=None):
    """Finns titeln redan i samlingen (eller på dess önskelista)? Används för varningar."""
    conds, args = [], []
    if tmdb_id:
        conds.append("tmdb_id=?"); args.append(tmdb_id)
    if imdb_id:
        conds.append("imdb_id=?"); args.append(imdb_id)
    if barcode:
        code = "".join(ch for ch in barcode if ch.isdigit())
        conds.append("barcode IN (?, ?, ?)"); args += [code, code.lstrip("0"), "0" + code]
    if not conds:
        return []
    s, a = _lib(lib)
    with db.connect() as con:
        return [dict(r) for r in con.execute(
            f"SELECT {LIST_COLS} FROM items WHERE ({' OR '.join(conds)}){s}", args + a)]


# ---------- Statistik ----------

def _count_names(con, sql, args):
    out = {}
    for (v,) in con.execute(sql, args):
        for name in v.split(" | "):
            if name.strip():
                out[name.strip()] = out.get(name.strip(), 0) + 1
    return out


def stats(lib=None):
    s_, a = _lib(lib)
    W = f"WHERE {OWNED}{s_}"
    with db.connect() as con:
        one = lambda sql: con.execute(sql, a).fetchone()[0]  # noqa: E731
        s = {
            "titles": one(f"SELECT COUNT(*) FROM items {W}"),
            "movies": one(f"SELECT COUNT(*) FROM items {W} AND kind='movie'"),
            "series": one(f"SELECT COUNT(DISTINCT series_name) FROM items {W} AND kind='tv'"),
            "seasons": one(f"SELECT COUNT(*) FROM items {W} AND kind='tv'"),
            "discs": one(f"SELECT COALESCE(SUM(COALESCE(nr_discs, 1)), 0) FROM items {W}"),
            "minutes": one(f"SELECT COALESCE(SUM(runtime), 0) FROM items {W}"),
            "watched": one(f"SELECT COUNT(*) FROM items {W} AND watched=1"),
            "spent": one(f"SELECT COALESCE(SUM(purchase_price), 0) FROM items {W}"),
            "wish": one(f"SELECT COUNT(*) FROM items WHERE {WISH}{s_}"),
            "loaned": one(f"SELECT COUNT(*) FROM items {W} AND loaned_to IS NOT NULL AND loaned_to != ''"),
        }
        rows = lambda sql: [dict(r) for r in con.execute(sql, a)]  # noqa: E731
        s["formats"] = rows(f"SELECT COALESCE(format, '?') AS label, COUNT(*) AS n FROM items {W} "
                            "GROUP BY format ORDER BY n DESC")
        s["decades"] = rows(f"SELECT ((year/10)*10) || '-tal' AS label, COUNT(*) AS n FROM items {W} AND year "
                            "GROUP BY year/10 ORDER BY year/10")
        s["added_per_year"] = rows(f"SELECT substr(added_date, 1, 4) AS label, COUNT(*) AS n FROM items {W} "
                                   "AND added_date IS NOT NULL GROUP BY label ORDER BY label")
        s["locations"] = rows(f"SELECT location AS label, COUNT(*) AS n FROM items {W} AND location IS NOT NULL "
                              "AND location != '' GROUP BY location ORDER BY n DESC LIMIT 10")
        genres = _count_names(con, f"SELECT genres FROM items {W} AND genres IS NOT NULL", a)
        s["genres"] = [{"label": k, "n": v} for k, v in sorted(genres.items(), key=lambda kv: -kv[1])[:15]]
        dirs = _count_names(con, f"SELECT director FROM items {W} AND director IS NOT NULL AND kind='movie'", a)
        s["directors"] = [{"label": k, "n": v} for k, v in sorted(dirs.items(), key=lambda kv: -kv[1])[:10]]
    return s


# ---------- Slumpa kvällens film ----------

def random_pick(lib=None, kind="movie", unwatched=False, max_runtime=None, genre="", format=""):
    s, args = _lib(lib)
    sql = f"SELECT {LIST_COLS} FROM items WHERE {OWNED} AND (loaned_to IS NULL OR loaned_to = ''){s}"
    if kind in ("movie", "tv"):
        sql += " AND kind=?"
        args.append(kind)
        if kind == "tv":
            sql += " AND (season IS NULL OR season = 1)"  # börja en serie från början
    if unwatched:
        sql += " AND COALESCE(watched, 0)=0"
    if max_runtime:
        sql += " AND runtime IS NOT NULL AND runtime <= ?"
        args.append(int(max_runtime))
    if genre:
        sql += " AND (' | ' || genres || ' | ') LIKE ?"
        args.append(f"% | {genre} | %")
    if format:
        sql += " AND format=?"
        args.append(format)
    sql += " ORDER BY RANDOM() LIMIT 1"
    with db.connect() as con:
        row = con.execute(sql, args).fetchone()
    return dict(row) if row else None


# ---------- Filmserier (TMDB collections) ----------

def collections(lib=None):
    s, a = _lib(lib)
    with db.connect() as con:
        rows = con.execute(
            f"SELECT collection_id AS id, collection_name AS name, COUNT(*) AS owned, "
            f"MAX(poster_path) AS poster_path FROM items WHERE collection_id IS NOT NULL AND {OWNED}{s} "
            "GROUP BY collection_id ORDER BY collection_name COLLATE NOCASE", a).fetchall()
    return [dict(r) for r in rows]


# ---------- Home Assistant ----------

def ha_summary():
    today = date.today().isoformat()
    with db.connect() as con:
        one = lambda sql, *a: con.execute(sql, a).fetchone()[0]  # noqa: E731
        latest = con.execute(
            f"SELECT title, added_date, format FROM items WHERE {OWNED} ORDER BY added_date DESC, id DESC LIMIT 5"
        ).fetchall()
        overdue = con.execute(
            f"SELECT title, loaned_to, due_date FROM items WHERE {OWNED} AND loaned_to IS NOT NULL "
            "AND loaned_to != '' AND due_date IS NOT NULL AND due_date < ?", (today,)).fetchall()
        return {
            "total": one(f"SELECT COUNT(*) FROM items WHERE {OWNED}"),
            "movies": one(f"SELECT COUNT(*) FROM items WHERE {OWNED} AND kind='movie'"),
            "series": one(f"SELECT COUNT(DISTINCT series_name) FROM items WHERE {OWNED} AND kind='tv'"),
            "seasons": one(f"SELECT COUNT(*) FROM items WHERE {OWNED} AND kind='tv'"),
            "unwatched": one(f"SELECT COUNT(*) FROM items WHERE {OWNED} AND COALESCE(watched,0)=0"),
            "wishlist": one(f"SELECT COUNT(*) FROM items WHERE {WISH}"),
            "loaned": one(f"SELECT COUNT(*) FROM items WHERE {OWNED} AND loaned_to IS NOT NULL AND loaned_to != ''"),
            "overdue": len(overdue),
            "overdue_list": [dict(r) for r in overdue],
            "latest_title": latest[0]["title"] if latest else None,
            "latest_added": latest[0]["added_date"] if latest else None,
            "latest": [dict(r) for r in latest],
            "collections": [{"name": l["name"], "titles": l["owned"], "wishlist": l["wish"]} for l in libraries()],
        }


# ---------- Säkerhetskopior ----------

BACKUP_DIR = os.environ.get("BACKUP_DIR", os.path.join(db.CONFIG_DIR, "backup"))


def backup_now(reason=""):
    """Säker kopia även medan appen används (SQLite:s inbyggda backup)."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    name = f"diskoteket-{datetime.now():%Y%m%d-%H%M%S}{('-' + reason) if reason else ''}.db"
    path = os.path.join(BACKUP_DIR, name)
    src = sqlite3.connect(db.DB_PATH)
    dst = sqlite3.connect(path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    keep = max(1, int(settings.get_float("backup_keep")))
    auto = sorted(f for f in glob.glob(os.path.join(BACKUP_DIR, "*.db")) if re.search(r"-\d{6}\.db$", f))
    for old in auto[:-keep]:  # bara automatiska kopior rensas; de som tas inför borttagning sparas
        os.remove(old)
    return name


def list_backups():
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "*.db")), key=os.path.getmtime, reverse=True)
    return [{"name": os.path.basename(f), "size": os.path.getsize(f),
             "time": datetime.fromtimestamp(os.path.getmtime(f)).isoformat(timespec="minutes")} for f in files]
