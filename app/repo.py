"""Frågor mot databasen: samlingar, listor, filter, statistik, slump, Home Assistant och backup.
Ingen webbkod här, så allt går att testa fristående. lib=None betyder 'alla samlingar'."""
import glob
import json
import os
import re
import shutil
import sqlite3
from datetime import date, datetime

from . import db, settings

LIST_COLS = ("id, library_id, kind, title, series_name, season, year, format, poster_path, barcode, watched, "
             "genres, sort_title, location, loaned_to, due_date, collection_status, my_rating, "
             "added_date, runtime, collection_id, collection_name, tmdb_id, imdb_id, enriched, "
             "artist, label, tracks, purchase_price, tags, upgrade_to, sell_price, wish_price, condition, "
             "release_physical")

WISH = "(collection_status LIKE '%wish%')"
FOR_SALE = "(collection_status = 'For Sale')"
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
    "artist": "COALESCE(artist, '~') COLLATE NOCASE, year, COALESCE(sort_title, title) COLLATE NOCASE",
    "price": "COALESCE(purchase_price, 0) DESC, title COLLATE NOCASE",
}

# Fliken "Alla" visar film och serier – musiken har en egen flik
KIND_SQL = {"movie": "kind='movie'", "tv": "kind='tv'", "music": "kind='music'", "video": "kind IN ('movie', 'tv')"}


def _kind(kind, prefix=" AND "):
    return f"{prefix}{KIND_SQL[kind]}" if kind in KIND_SQL else ""

# Fält som 'Uppdatera metadata' kan skriva över – men inte om du har ändrat dem själv
LOCKABLE = {"title", "original_title", "year", "series_name", "season", "poster_path", "plot",
            "genres", "runtime", "director", "actors"}
# Interna fält som aldrig låses. Allt annat du ändrar i appen låses, så att en ny CLZ-import
# eller 'Uppdatera metadata' inte skriver över det.
NEVER_LOCK = {"tmdb_id", "imdb_id", "collection_id", "collection_name", "enriched", "coll_checked", "library_id", "kind",
              "mbid", "discogs_id", "tracklist"}


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
               digital="", sort="title", missing_poster=False, collection_id=None, field="title", tag=""):
    sql = f"SELECT {LIST_COLS}, {DIGITAL} AS digital FROM items WHERE 1=1"
    s, args = _lib(lib)
    sql += s
    if status == "owned":
        sql += f" AND {OWNED}"
    elif status == "wish":
        sql += f" AND {WISH}"
    elif status == "loaned":
        sql += f" AND {OWNED} AND loaned_to IS NOT NULL AND loaned_to != ''"
    elif status == "upgrade":  # ägda titlar man vill ha i ett bättre format
        sql += f" AND {OWNED} AND upgrade_to IS NOT NULL AND upgrade_to != ''"
    elif status == "sale":
        sql += f" AND {FOR_SALE}"
    sql += _kind(kind)
    if tag:
        sql += " AND (' | ' || tags || ' | ') LIKE ?"
        args.append(f"% | {tag} | %")
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
    return search_filter(rows, q, field) if q else rows


SEARCH_FIELDS = ("title", "actors", "director", "all")


def search_filter(rows, q, field="title"):
    """Fritextsökning. Görs i Python så att å/ä/ö fungerar oavsett stora/små bokstäver.
    Sökordet måste stå i början av ett ord: 'bert' hittar 'Bert' och 'Berts dagbok',
    men inte 'Albert', 'Herbert' eller 'Robert'.
    field: title (standard), actors, director eller all."""
    q = re.sub(r"\s+", " ", q.strip().lower())
    if field not in SEARCH_FIELDS:
        field = "title"
    word = re.compile(r"(?<!\w)" + re.escape(q))
    digits = re.sub(r"[\s-]", "", q)
    is_code = digits.isdigit() and len(digits) >= 8
    scored = []
    for r in rows:
        if is_code:  # en streckkod hittas oavsett vald sökning
            if r.get("barcode") and digits.lstrip("0") == r["barcode"].lstrip("0"):
                scored.append((0, r))
            continue
        titles = [(r.get(k) or "").lower() for k in ("title", "original_title", "series_name", "artist")]
        names = lambda k: [n.strip().lower() for n in (r.get(k) or "").split(" | ") if n.strip()]  # noqa: E731
        score = None
        if field in ("title", "all"):
            if any(t.startswith(q) for t in titles):
                score = 1
            elif any(word.search(t) for t in titles):
                score = 2
        if score is None and field in ("actors", "all") and any(word.search(n) for n in names("actors")):
            score = 3
        if score is None and field in ("director", "all") and any(word.search(n) for n in names("director")):
            score = 3
        if score is not None:
            scored.append((score, r))
    for _, r in scored:
        for k in ("original_title", "actors", "director"):
            r.pop(k, None)
    scored.sort(key=lambda x: x[0])  # stabil: inom samma nivå behålls vald sortering
    return [r for _, r in scored]


def facets(lib=None, kind=""):
    """Värden till filtermenyerna (för fliken som visas: musik har egna format och genrer)."""
    s, a = _lib(lib)
    s += _kind("music" if kind == "music" else "video" if kind in ("movie", "tv", "video") else "")
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
        tags = _count_names(con, f"SELECT tags FROM items WHERE tags IS NOT NULL AND tags != ''{s}", a)
    return {"formats": formats, "locations": locations,
            "genres": sorted(genres, key=lambda k: -genres[k]), "digital": has_digital,
            "tags": sorted(tags, key=lambda k: k.lower())}


def all_tags():
    with db.connect() as con:
        return sorted(_count_names(con, "SELECT tags FROM items WHERE tags IS NOT NULL AND tags != ''", []),
                      key=str.lower)


def join_tags(tags) -> str | None:
    """['Jul', ' jul ', 'Barn'] -> 'Barn | Jul' (inga dubbletter, oavsett stora/små bokstäver)."""
    seen = {}
    for t in tags:
        t = re.sub(r"\s+", " ", str(t).replace("|", " ")).strip()
        if t and t.lower() not in seen:
            seen[t.lower()] = t
    return " | ".join(sorted(seen.values(), key=str.lower)) or None


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
            "enriched", "coll_checked", "kind",
            "artist", "label", "cat_no", "tracks", "tracklist", "mbid", "discogs_id", "nr_discs",
            "tags", "upgrade_to", "condition", "condition_notes", "sell_price", "wish_price", "release_physical"}

# Det massredigering får ändra
BULK = {"location", "format", "library_id", "collection_status", "upgrade_to", "condition", "watched"}


def bulk_update(ids: list[int], changes: dict, add_tags=(), remove_tags=()) -> int:
    """Samma ändring på många titlar. Ändringarna låses precis som när man redigerar en i taget."""
    changes = {k: v for k, v in changes.items() if k in BULK}
    remove = {t.lower() for t in remove_tags}
    n = 0
    for item_id in ids:
        cur = get(item_id)
        if not cur:
            continue
        ch = dict(changes)
        if add_tags or remove_tags:
            tags = [t for t in (cur.get("tags") or "").split(" | ") if t and t.lower() not in remove]
            ch["tags"] = join_tags(tags + list(add_tags))
        if ch:
            update(item_id, ch, lock=True)
            n += 1
    return n


# ---------- Hyllkartan ----------

def locations(lib=None):
    """Alla platser med antal titlar, beskrivning och foto."""
    s, a = _lib(lib)
    with db.connect() as con:
        counts = {r[0]: r[1] for r in con.execute(
            f"SELECT location, COUNT(*) FROM items WHERE location IS NOT NULL AND location != '' AND {OWNED}{s} "
            "GROUP BY location", a)}
        info = {r["name"]: dict(r) for r in con.execute("SELECT * FROM locations")}
    names = sorted(set(counts) | set(info), key=lambda n: n.lower())
    return [{"name": n, "count": counts.get(n, 0), "description": (info.get(n) or {}).get("description"),
             "photo": (info.get(n) or {}).get("photo")} for n in names]


def save_location(name, description=None, photo=None, new_name=None):
    """Spara beskrivning/foto, eller byt namn på platsen (då flyttas alla titlar med)."""
    with db.connect() as con:
        con.execute("INSERT INTO locations (name) VALUES (?) ON CONFLICT(name) DO NOTHING", (name,))
        if description is not None:
            con.execute("UPDATE locations SET description=? WHERE name=?", (description.strip() or None, name))
        if photo is not None:
            con.execute("UPDATE locations SET photo=? WHERE name=?", (photo or None, name))
        if not (new_name and new_name.strip() and new_name.strip() != name):
            return name
        new_name = new_name.strip()
        ids = [r[0] for r in con.execute("SELECT id FROM items WHERE location=?", (name,))]
        if con.execute("SELECT 1 FROM locations WHERE name=?", (new_name,)).fetchone():
            con.execute("DELETE FROM locations WHERE name=?", (name,))
        else:
            con.execute("UPDATE locations SET name=? WHERE name=?", (new_name, name))
    for item_id in ids:  # via update(), så att en ny CLZ-import inte skriver tillbaka det gamla namnet
        update(item_id, {"location": new_name})
    return new_name


def update(item_id, changes: dict, lock=True, unlock=()):
    """Spara ändringar. Med lock=True låses fälten som ändrats, så att en ny CLZ-import
    eller 'Uppdatera metadata' inte skriver över dem senare."""
    changes = {k: v for k, v in changes.items() if k in EDITABLE}
    if isinstance(changes.get("tracklist"), list):
        changes["tracklist"] = json.dumps(changes["tracklist"], ensure_ascii=False) if changes["tracklist"] else None
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


def find_music(lib, mbid=None, discogs_id=None, barcode=None):
    """Finns albumet redan i samlingen? Samma MusicBrainz-/Discogs-utgåva eller samma streckkod."""
    conds, args = [], []
    for col, v in (("mbid", mbid), ("discogs_id", discogs_id)):
        if v:
            conds.append(f"{col}=?"); args.append(v)
    found = []
    if conds:
        with db.connect() as con:
            found = [dict(r) for r in con.execute(
                f"SELECT {LIST_COLS} FROM items WHERE kind='music' AND library_id=? AND ({' OR '.join(conds)})",
                [lib] + args)]
    if not found and barcode:
        found = [e for e in find_existing(lib, barcode=barcode) if e["kind"] == "music"]
    return found


# ---------- Statistik ----------

def _count_names(con, sql, args):
    out = {}
    for (v,) in con.execute(sql, args):
        for name in v.split(" | "):
            if name.strip():
                out[name.strip()] = out.get(name.strip(), 0) + 1
    return out


def _top(counts: dict, n: int):
    return [{"label": k, "n": v} for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))[:n]]


def is_various(artist) -> bool:
    return (artist or "").strip().lower() in db.VARIOUS


def stats(lib=None):
    s_, a = _lib(lib)
    A = f"WHERE {OWNED}{s_}"
    W = f"{A} AND kind != 'music'"
    M = f"{A} AND kind = 'music'"
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
            "spent": one(f"SELECT COALESCE(SUM(purchase_price), 0) FROM items {A}"),
            "wish": one(f"SELECT COUNT(*) FROM items WHERE {WISH}{s_}"),
            "loaned": one(f"SELECT COUNT(*) FROM items {A} AND loaned_to IS NOT NULL AND loaned_to != ''"),
            "all_discs": one(f"SELECT COALESCE(SUM(COALESCE(nr_discs, 1)), 0) FROM items {A}"),
        }
        rows = lambda sql: [dict(r) for r in con.execute(sql, a)]  # noqa: E731

        # Värde: vad samlingen kostat enligt inköpspriset (finns bara där du fyllt i det)
        priced = rows(f"SELECT id, kind, title, artist, format, purchase_price FROM items {A} "
                      "AND purchase_price > 0 ORDER BY purchase_price DESC")
        s["value"] = {"total": round(sum(r["purchase_price"] for r in priced), 2), "priced": len(priced),
                      "items": one(f"SELECT COUNT(*) FROM items {A}"),
                      "avg": round(sum(r["purchase_price"] for r in priced) / len(priced), 2) if priced else 0,
                      "top": priced[:5]}

        # Musik
        artists = {}
        for (v,) in con.execute(f"SELECT artist FROM items {M} AND artist IS NOT NULL", a):
            if not is_various(v):
                artists[v.strip()] = artists.get(v.strip(), 0) + 1
        s["music"] = {
            "albums": one(f"SELECT COUNT(*) FROM items {M}"),
            "discs": one(f"SELECT COALESCE(SUM(COALESCE(nr_discs, 1)), 0) FROM items {M}"),
            "minutes": one(f"SELECT COALESCE(SUM(runtime), 0) FROM items {M}"),
            "tracks": one(f"SELECT COALESCE(SUM(tracks), 0) FROM items {M}"),
            "compilations": sum(1 for (v,) in con.execute(f"SELECT artist FROM items {M}", a) if is_various(v)),
            "artists_count": len(artists),
            "artists": _top(artists, 10),
            "formats": rows(f"SELECT COALESCE(format, '?') AS label, COUNT(*) AS n FROM items {M} "
                            "GROUP BY format ORDER BY n DESC"),
            "genres": _top(_count_names(con, f"SELECT genres FROM items {M} AND genres IS NOT NULL", a), 12),
            "labels": rows(f"SELECT label, COUNT(*) AS n FROM items {M} AND label IS NOT NULL AND label != '' "
                           "GROUP BY label COLLATE NOCASE ORDER BY n DESC LIMIT 8"),
            "decades": rows(f"SELECT ((year/10)*10) || '-tal' AS label, COUNT(*) AS n FROM items {M} AND year "
                            "GROUP BY year/10 ORDER BY year/10"),
        }
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
    s["duplicates"] = duplicates(lib)
    return s


def duplicates(lib=None):
    """Samma film/säsong (samma TMDB-ID) eller samma album (artist + titel) mer än en gång,
    t.ex. både DVD och Blu-ray. Med lib=None räknas alla samlingar."""
    s, a = _lib(lib)
    with db.connect() as con:
        rows = [dict(r) for r in con.execute(
            f"SELECT id, library_id, kind, title, artist, year, format, edition, season, tmdb_id, poster_path "
            f"FROM items WHERE {OWNED}{s} ORDER BY id", a)]
    groups = {}
    for r in rows:
        if r["kind"] == "music":
            if not r["artist"] or is_various(r["artist"]):
                continue  # samlingsskivor heter ofta likadant utan att vara samma skiva
            key = ("music", r["artist"].strip().lower(), r["title"].strip().lower())
        elif r["tmdb_id"]:
            # Serieboxar utan säsongsnummer (t.ex. "Beck: 13-16" och "Beck: 17-20") är olika – jämför titeln också
            part = r["season"] or (r["title"].strip().lower() if r["kind"] == "tv" else 0)
            key = (r["kind"], r["tmdb_id"], part)
        else:
            continue
        groups.setdefault(key, []).append(r)
    return [{"title": g[0]["title"], "artist": g[0]["artist"], "kind": g[0]["kind"], "items": g}
            for g in groups.values() if len(g) > 1]


# ---------- Slumpa kvällens film ----------

def random_pick(lib=None, kind="movie", unwatched=False, max_runtime=None, genre="", format=""):
    s, args = _lib(lib)
    sql = f"SELECT {LIST_COLS} FROM items WHERE {OWNED} AND (loaned_to IS NULL OR loaned_to = ''){s}"
    sql += _kind(kind if kind in ("movie", "tv", "music") else "video")
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
    """Allt som Home Assistant-integrationen och dess kort visar. Nycklarna från version 3
    (total, movies, latest_title …) finns kvar så att gamla REST-sensorer fungerar."""
    today = date.today().isoformat()
    with db.connect() as con:
        one = lambda sql, *a: con.execute(sql, a).fetchone()[0]  # noqa: E731
        latest = con.execute(
            f"SELECT id, kind, title, artist, year, added_date, format, poster_path FROM items WHERE {OWNED} "
            "ORDER BY added_date DESC, id DESC LIMIT 10").fetchall()
        overdue = con.execute(
            f"SELECT id, kind, title, artist, loaned_to, due_date FROM items WHERE {OWNED} AND loaned_to IS NOT NULL "
            "AND loaned_to != '' AND due_date IS NOT NULL AND due_date < ? ORDER BY due_date", (today,)).fetchall()
        per_lib = {r["library_id"]: dict(r) for r in con.execute(
            f"SELECT library_id, SUM(kind='movie') AS movies, SUM(kind='tv') AS seasons, SUM(kind='music') AS music "
            f"FROM items WHERE {OWNED} GROUP BY library_id")}
        formats = [dict(r) for r in con.execute(
            f"SELECT COALESCE(format, '?') AS label, COUNT(*) AS n FROM items WHERE {OWNED} "
            "GROUP BY format ORDER BY n DESC LIMIT 8")]
        return {
            "total": one(f"SELECT COUNT(*) FROM items WHERE {OWNED}"),
            "video": one(f"SELECT COUNT(*) FROM items WHERE {OWNED} AND kind != 'music'"),
            "movies": one(f"SELECT COUNT(*) FROM items WHERE {OWNED} AND kind='movie'"),
            "series": one(f"SELECT COUNT(DISTINCT series_name) FROM items WHERE {OWNED} AND kind='tv'"),
            "seasons": one(f"SELECT COUNT(*) FROM items WHERE {OWNED} AND kind='tv'"),
            "music": one(f"SELECT COUNT(*) FROM items WHERE {OWNED} AND kind='music'"),
            "discs": one(f"SELECT COALESCE(SUM(COALESCE(nr_discs, 1)), 0) FROM items WHERE {OWNED}"),
            "unwatched": one(f"SELECT COUNT(*) FROM items WHERE {OWNED} AND kind != 'music' AND COALESCE(watched,0)=0"),
            "wishlist": one(f"SELECT COUNT(*) FROM items WHERE {WISH}"),
            "loaned": one(f"SELECT COUNT(*) FROM items WHERE {OWNED} AND loaned_to IS NOT NULL AND loaned_to != ''"),
            "value": one(f"SELECT COALESCE(SUM(purchase_price), 0) FROM items WHERE {OWNED}"),
            "overdue": len(overdue),
            "overdue_list": [dict(r) for r in overdue],
            "latest_title": latest[0]["title"] if latest else None,
            "latest_added": latest[0]["added_date"] if latest else None,
            "latest": [dict(r) for r in latest],
            "formats": formats,
            "collections": [{"name": l["name"], "titles": l["owned"], "wishlist": l["wish"],
                             "movies": per_lib.get(l["id"], {}).get("movies") or 0,
                             "seasons": per_lib.get(l["id"], {}).get("seasons") or 0,
                             "music": per_lib.get(l["id"], {}).get("music") or 0} for l in libraries()],
        }


# ---------- Bara digitalt ----------

def digital_only(lib=None):
    """Titlar som finns i Plex/Jellyfin men inte på skiva (i vald samling). Önskade markeras."""
    s, a = _lib(lib, " AND i.")
    match = ("((d.imdb_id IS NOT NULL AND d.imdb_id = i.imdb_id) OR "
             "(d.tmdb_id IS NOT NULL AND d.tmdb_id = i.tmdb_id AND d.kind = i.kind))")
    owned = OWNED.replace("collection_status", "i.collection_status")
    wish = WISH.replace("collection_status", "i.collection_status")
    with db.connect() as con:
        rows = [dict(r) for r in con.execute(
            f"SELECT d.source, d.kind, d.imdb_id, d.tmdb_id, d.title, d.year, "
            f"EXISTS (SELECT 1 FROM items i WHERE {match} AND {wish}{s}) AS wished "
            f"FROM digital d WHERE NOT EXISTS (SELECT 1 FROM items i WHERE {match} AND {owned}{s}) "
            "ORDER BY d.title COLLATE NOCASE, d.year", a + a)]
    out, seen = [], {}
    for r in rows:  # samma titel i både Plex och Jellyfin blir en rad
        key = r["imdb_id"] or (r["kind"], r["tmdb_id"]) or (r["title"], r["year"])
        if key in seen:
            seen[key]["sources"].append(r["source"])
            continue
        r["sources"] = [r.pop("source")]
        seen[key] = r
        out.append(r)
    return out


# ---------- Export ----------

EXPORT_SKIP = {"extra", "locked", "enriched", "coll_checked", "tracklist"}


def export_rows(lib=None):
    s, a = _lib(lib, " WHERE items.")
    with db.connect() as con:
        rows = [db.row_to_dict(r) for r in con.execute(
            f"SELECT items.*, l.name AS library_name FROM items LEFT JOIN libraries l ON l.id = items.library_id{s} "
            "ORDER BY l.id, items.kind, COALESCE(items.artist, ''), COALESCE(items.sort_title, items.title)", a)]
    return rows


def export_csv(lib=None) -> str:
    import csv
    import io
    rows = export_rows(lib)
    cols = ["library_name"] + [f for f in db.FIELDS if f not in EXPORT_SKIP and f != "library_id"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(cols + ["tracklist"])
    for r in rows:
        tracks = " | ".join(t.get("title", "") for t in r.get("tracklist") or [])
        w.writerow([r.get(c) if r.get(c) is not None else "" for c in cols] + [tracks])
    return "﻿" + out.getvalue()  # BOM så att Excel visar å, ä och ö rätt


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


BACKUP_NAME_RE = re.compile(r"[A-Za-z0-9_\-]+\.db")


class RestoreError(Exception):
    pass


def _check_db(path):
    """Är filen en hel SQLite-databas från Diskoteket (vilken version som helst)?"""
    try:
        con = sqlite3.connect(f"file:{path.replace(os.sep, '/')}?mode=ro", uri=True)
        try:
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RestoreError("Databasen är skadad (integritetskontrollen misslyckades)")
            cols = [r[1] for r in con.execute("PRAGMA table_info(items)")]
            if "title" not in cols:
                raise RestoreError("Filen är en databas, men inte från Diskoteket")
            return con.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        finally:
            con.close()
    except sqlite3.DatabaseError:
        raise RestoreError("Filen är ingen databas som går att läsa")


def restore_backup(name: str | None = None, data: bytes | None = None) -> dict:
    """Ersätter databasen med en säkerhetskopia (en av appens egna, eller en uppladdad fil).
    Tar först en kopia av nuvarande databas, så att det alltid går att ångra."""
    tmp = os.path.join(db.CONFIG_DIR, ".aterstall.db")
    for f in (tmp, tmp + "-wal", tmp + "-shm"):
        if os.path.exists(f):
            os.remove(f)
    if name:
        if not BACKUP_NAME_RE.fullmatch(name) or not os.path.exists(os.path.join(BACKUP_DIR, name)):
            raise RestoreError("Säkerhetskopian finns inte")
        shutil.copyfile(os.path.join(BACKUP_DIR, name), tmp)
    elif data:
        if not data.startswith(b"SQLite format 3\x00"):
            raise RestoreError("Filen är ingen databas (välj en .db-fil från Diskoteket)")
        with open(tmp, "wb") as f:
            f.write(data)
    else:
        raise RestoreError("Välj en säkerhetskopia eller en fil")
    try:
        items = _check_db(tmp)
    except RestoreError:
        os.remove(tmp)
        raise

    safety = backup_now("fore-aterstallning")
    con = sqlite3.connect(db.DB_PATH)
    try:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")  # allt skrivet ligger nu i själva filen
    finally:
        con.close()
    os.replace(tmp, db.DB_PATH)
    # Gamla -wal/-shm hör till den förra databasen och skulle förstöra den nya om de låg kvar
    for f in (db.DB_PATH + "-wal", db.DB_PATH + "-shm", tmp + "-wal", tmp + "-shm"):
        try:
            os.remove(f)
        except OSError:
            pass
    db.init()  # uppgraderar en kopia från en äldre version
    settings._cache = None
    return {"safety_copy": safety, "items": items}
