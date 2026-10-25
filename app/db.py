"""SQLite-databasen. Allt som är viktigt ligger i CONFIG_DIR (på Unraid: /mnt/user/appdata/diskoteket)."""
import json
import os
import sqlite3
from contextlib import contextmanager

CONFIG_DIR = (os.environ.get("CONFIG_DIR") or os.environ.get("DATA_DIR")
              or ("/config" if os.path.isdir("/config") else os.path.join(os.path.dirname(__file__), "..", "data")))
DB_PATH = os.path.join(CONFIG_DIR, "diskoteket.db")
LEGACY_DB = os.path.join(CONFIG_DIR, "samling.db")  # namnet i version 1–2

# Fält som har egna kolumner. Allt annat från CLZ sparas i "extra" (JSON) så inget går förlorat.
FIELDS = [
    "library_id", "kind",
    "title", "original_title", "sort_title", "series_name", "season",
    "year", "genres", "runtime", "director", "actors", "plot", "country", "language",
    "format", "edition", "barcode", "nr_discs", "regions", "audience_rating",
    "imdb_id", "imdb_rating", "tmdb_id", "poster_path",
    "my_rating", "watched", "location", "notes", "collection_status",
    "added_date", "clz_index",
    "loaned_to", "loan_date", "due_date", "purchase_price",
    "collection_id", "collection_name",
]

ITEMS_TABLE = """
CREATE TABLE {name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    library_id INTEGER NOT NULL DEFAULT 1,
    kind TEXT NOT NULL DEFAULT 'movie',
    title TEXT NOT NULL,
    original_title TEXT, sort_title TEXT, series_name TEXT, season INTEGER,
    year INTEGER, genres TEXT, runtime INTEGER, director TEXT, actors TEXT, plot TEXT,
    country TEXT, language TEXT,
    format TEXT, edition TEXT, barcode TEXT, nr_discs INTEGER, regions TEXT, audience_rating TEXT,
    imdb_id TEXT, imdb_rating REAL, tmdb_id INTEGER, poster_path TEXT,
    my_rating REAL, watched INTEGER DEFAULT 0, location TEXT, notes TEXT,
    collection_status TEXT DEFAULT 'In Collection',
    added_date TEXT, clz_index INTEGER,
    loaned_to TEXT, loan_date TEXT, due_date TEXT, purchase_price REAL,
    collection_id INTEGER, collection_name TEXT, coll_checked INTEGER DEFAULT 0,
    locked TEXT,            -- fält du ändrat själv; skrivs inte över av 'Uppdatera metadata'
    extra TEXT,
    enriched INTEGER DEFAULT 0
)"""

OTHER_TABLES = """
CREATE TABLE IF NOT EXISTS libraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created TEXT DEFAULT (date('now'))
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS digital (
    source TEXT NOT NULL,       -- 'plex' eller 'jellyfin'
    kind TEXT,                  -- 'movie' eller 'tv' (TMDB-ID kan krocka mellan filmer och serier)
    imdb_id TEXT, tmdb_id INTEGER, title TEXT, year INTEGER
);
CREATE INDEX IF NOT EXISTS idx_items_barcode ON items(barcode);
CREATE INDEX IF NOT EXISTS idx_items_imdb ON items(imdb_id);
CREATE INDEX IF NOT EXISTS idx_items_tmdb ON items(tmdb_id);
CREATE INDEX IF NOT EXISTS idx_items_lib ON items(library_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_items_clz ON items(library_id, clz_index);
CREATE INDEX IF NOT EXISTS idx_digital_imdb ON digital(imdb_id);
CREATE INDEX IF NOT EXISTS idx_digital_tmdb ON digital(tmdb_id);
"""


@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _columns(con, table):
    return [r["name"] for r in con.execute(f"PRAGMA table_info({table})")]


def init():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if not os.path.exists(DB_PATH) and os.path.exists(LEGACY_DB):
        os.rename(LEGACY_DB, DB_PATH)  # uppgradering från version 1–2
    with connect() as con:
        con.execute("PRAGMA journal_mode=WAL")
        exists = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='items'").fetchone()
        needs_backfill = False
        if not exists:
            con.execute(ITEMS_TABLE.format(name="items"))
        else:
            old = _columns(con, "items")
            con.execute("DROP TABLE IF EXISTS items_new")
            con.execute(ITEMS_TABLE.format(name="items_new"))
            new = _columns(con, "items_new")
            if set(new) - set(old) or "clz_index INTEGER UNIQUE" in exists["sql"]:
                # Bygg om tabellen (SQLite kan inte ändra en UNIQUE-regel på plats). All data följer med.
                common = [c for c in new if c in old]
                cols = ", ".join(common)
                con.execute(f"INSERT INTO items_new ({cols}) SELECT {cols} FROM items")
                con.execute("DROP TABLE items")
                con.execute("ALTER TABLE items_new RENAME TO items")
                needs_backfill = "loaned_to" not in old
            else:
                con.execute("DROP TABLE items_new")
        con.executescript(OTHER_TABLES)
        if "kind" not in _columns(con, "digital"):
            con.execute("ALTER TABLE digital ADD COLUMN kind TEXT")
        if not con.execute("SELECT 1 FROM libraries").fetchone():
            con.execute("INSERT INTO libraries (id, name) VALUES (1, 'Mina filmer')")
        first = con.execute("SELECT MIN(id) FROM libraries").fetchone()[0]
        con.execute("UPDATE items SET library_id=? WHERE library_id IS NULL "
                    "OR library_id NOT IN (SELECT id FROM libraries)", (first,))
        if needs_backfill:
            backfill_from_extra(con)
    # SQLite skapar filer som bara ägaren får skriva till. Gör dem skrivbara för gruppen (users på Unraid).
    for f in (DB_PATH, DB_PATH + "-wal", DB_PATH + "-shm"):
        try:
            os.chmod(f, 0o664)
        except OSError:
            pass


def backfill_from_extra(con):
    """Poster från version 1 har utlån och pris kvar i 'extra'. Flytta dit dem."""
    from .clz_import import _date, _float  # undvik cirkulär import
    for row in con.execute("SELECT id, extra FROM items WHERE extra IS NOT NULL").fetchall():
        x = json.loads(row["extra"] or "{}")
        con.execute(
            "UPDATE items SET loaned_to=?, loan_date=?, due_date=?, purchase_price=? WHERE id=?",
            (x.get("Loaned To") or None, _date(x.get("Loan Date")), _date(x.get("Due Date")),
             _float(x.get("Purchase Price")), row["id"]))


def row_to_dict(row):
    d = dict(row)
    d["extra"] = json.loads(d["extra"]) if d.get("extra") else {}
    d["locked"] = [f for f in (d.get("locked") or "").split(",") if f]
    return d


def upsert(con, item: dict):
    """Lägg till eller uppdatera. Matchar på CLZ-index inom samma samling, annars ny post."""
    cols = [f for f in FIELDS if f in item]
    values = [item[c] for c in cols]
    extra = json.dumps(item.get("extra", {}), ensure_ascii=False)

    existing = None
    if item.get("clz_index") is not None:
        existing = con.execute("SELECT id, locked FROM items WHERE library_id=? AND clz_index=?",
                               (item.get("library_id", 1), item["clz_index"])).fetchone()
    if existing:
        locked = set((existing["locked"] or "").split(","))
        keep = [(c, v) for c, v in zip(cols, values) if c not in locked]  # dina egna ändringar ligger kvar
        sets = ", ".join(f"{c}=?" for c, _ in keep)
        con.execute(f"UPDATE items SET {sets}, extra=? WHERE id=?", [v for _, v in keep] + [extra, existing["id"]])
        return existing["id"], False
    placeholders = ", ".join("?" for _ in cols)
    cur = con.execute(
        f"INSERT INTO items ({', '.join(cols)}, extra) VALUES ({placeholders}, ?)", values + [extra]
    )
    return cur.lastrowid, True
