"""Databaser som de såg ut i tidigare versioner. Används för att testa att uppgraderingen
till nuvarande version inte tappar någon data."""
import json
import sqlite3

# Version 1 (samling.db): ingen samlingstabell, utlåning och pris låg i 'extra', clz_index var UNIQUE
V1 = """
CREATE TABLE items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL DEFAULT 'movie',
    title TEXT NOT NULL,
    original_title TEXT, sort_title TEXT, series_name TEXT, season INTEGER,
    year INTEGER, genres TEXT, runtime INTEGER, director TEXT, actors TEXT, plot TEXT,
    country TEXT, language TEXT,
    format TEXT, edition TEXT, barcode TEXT, nr_discs INTEGER, regions TEXT, audience_rating TEXT,
    imdb_id TEXT, imdb_rating REAL, tmdb_id INTEGER, poster_path TEXT,
    my_rating REAL, watched INTEGER DEFAULT 0, location TEXT, notes TEXT,
    collection_status TEXT DEFAULT 'In Collection',
    added_date TEXT, clz_index INTEGER UNIQUE,
    extra TEXT,
    enriched INTEGER DEFAULT 0
);
CREATE TABLE digital (source TEXT NOT NULL, imdb_id TEXT, tmdb_id INTEGER, title TEXT, year INTEGER);
"""

# Version 2: utlåning och filmserier som egna kolumner (tillagda med ALTER TABLE), fortfarande en samling
V2 = V1.replace("enriched INTEGER DEFAULT 0\n)", "enriched INTEGER DEFAULT 0\n, loaned_to TEXT, loan_date TEXT, due_date TEXT, "
                "purchase_price REAL, collection_id INTEGER, collection_name TEXT, coll_checked INTEGER DEFAULT 0)")

# Version 3.0–3.1: flera samlingar, inställningar och inlärda streckkoder
V3 = """
CREATE TABLE items (
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
    locked TEXT,
    extra TEXT,
    enriched INTEGER DEFAULT 0
);
CREATE TABLE libraries (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, created TEXT DEFAULT (date('now')));
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE barcodes (code TEXT PRIMARY KEY, tmdb_id INTEGER, kind TEXT, title TEXT, year INTEGER, format TEXT,
    source TEXT, updated TEXT DEFAULT (datetime('now')));
CREATE TABLE digital (source TEXT NOT NULL, kind TEXT, imdb_id TEXT, tmdb_id INTEGER, title TEXT, year INTEGER);
CREATE UNIQUE INDEX idx_items_clz ON items(library_id, clz_index);
"""

MOVIES = [
    # (titel, år, format, clz_index, streckkod, plats)
    ("Evil Dead", 1981, "DVD", 1, "7319980033032", "Hylla A"),
    ("Alien", 1979, "Blu-ray", 2, "5039036048372", "Hylla A"),
    ("Sökarna", 1993, "DVD", 3, "7321979123456", "Hylla B"),
    ("24: Season 3", 2004, "DVD", 4, None, None),
]


def make(path, version):
    con = sqlite3.connect(path)
    con.executescript({1: V1, 2: V2, 3: V3}[version])
    for title, year, fmt, idx, code, loc in MOVIES:
        kind = "tv" if "Season" in title else "movie"
        extra = {"Loaned To": "Kalle", "Purchase Price": "99,00"} if idx == 1 else {"Subtitles": "Svenska"}
        con.execute("INSERT INTO items (kind, title, year, format, clz_index, barcode, location, extra, tmdb_id, "
                    "poster_path, enriched) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                    (kind, title, year, fmt, idx, code, loc, json.dumps(extra, ensure_ascii=False), 100 + idx,
                     f"/poster{idx}.jpg"))
    if version == 3:
        con.execute("INSERT INTO libraries (id, name) VALUES (1, 'Mina filmer'), (2, 'Barnens')")
        con.execute("INSERT INTO settings (key, value) VALUES ('tmdb_language', 'en-US')")
        con.execute("UPDATE items SET locked='title', title='Ondskans väsen' WHERE clz_index=1")
        con.execute("INSERT INTO barcodes (code, tmdb_id, kind, title) VALUES ('123', 5, 'movie', 'X')")
    con.commit()
    con.close()
