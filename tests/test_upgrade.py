"""Uppgradering av gamla databaser och import från CLZ – ingen data får försvinna."""
import json
import os
import sqlite3

import pytest

from app import clz_import, db, repo, settings

from .old_schemas import MOVIES, make

MOVIES_CSV = """Title,Release Year,Format,Index,Barcode,Location,Director,Is TV Series
Evil Dead,1981,DVD,1,7319980033032,Hylla A,Sam Raimi,No
Alien,1979,Blu-ray,2,5039036048372,Hylla A,Ridley Scott,No
""".encode()

MUSIC_CSV = (
    'Artist,"Artist Sort",Barcode,"Cat No",Format,Genre,Label,"Original Release Year","Release Year",'
    '"Sort Title",Title,Discs,Length,Tracks,"Added Date","Collection Status",Index,"My Rating",'
    '"Purchase Price",Location,"Loaned To"\n'
    'A*Teens,A*Teens,731454766623,"547 666-2",CD,"Electronic | Euro House","Stockholm Records",,1999,'
    '"The ABBA Generation","The ABBA Generation",1,42:54,11,"Mar 26, 2026","In Collection",1,0,,,\n'
    '"Ace Of Base","Ace Of Base",5708992012166,"MRCD 3295",CD,"Pop | Reggae","Mega Records",,1996,'
    '"The Bridge","The Bridge",1,1:02:11,17,"Mar 19, 2026","In Collection",2,8,40.00,"Lådan",Lisa\n'
    'Various,Various,,,CD,Pop,"EVA Records (5)",,1997,"Absolute Music 24","Absolute Music 24",2,0:00,40,'
    '"Mar 18, 2026","In Collection",3,0,,,\n'
).encode()


def counts():
    with db.connect() as con:
        return dict(con.execute("SELECT kind, COUNT(*) FROM items GROUP BY kind").fetchall())


def titles(kind=None):
    with db.connect() as con:
        sql = "SELECT title FROM items" + (" WHERE kind=?" if kind else "") + " ORDER BY id"
        return [r[0] for r in con.execute(sql, (kind,) if kind else ())]


@pytest.mark.parametrize("version", [1, 2, 3])
def test_old_database_upgrades_without_data_loss(config_dir, version):
    path = db.LEGACY_DB if version == 1 else db.DB_PATH
    make(path, version)
    db.init()
    db.init()  # en andra start ska inte ändra något

    assert os.path.exists(db.DB_PATH)
    assert counts() == {"movie": 3, "tv": 1}
    with db.connect() as con:
        rows = {r["clz_index"]: dict(r) for r in con.execute("SELECT * FROM items")}
        cols = [r["name"] for r in con.execute("PRAGMA table_info(items)")]
        indexes = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='index'")]
    for f in ("artist", "tracklist", "mbid", "library_id", "locked", "loaned_to"):
        assert f in cols
    assert "idx_items_clz" not in indexes and "idx_items_clz2" in indexes
    for _, year, fmt, idx, code, loc in MOVIES:
        r = rows[idx]
        assert (r["year"], r["format"], r["barcode"], r["location"]) == (year, fmt, code, loc)
        assert r["tmdb_id"] == 100 + idx and r["poster_path"] == f"/poster{idx}.jpg"
        assert r["library_id"] == 1
    if version == 1:
        assert rows[1]["loaned_to"] == "Kalle" and rows[1]["purchase_price"] == 99.0  # flyttat från 'extra'
    if version == 3:
        assert rows[1]["title"] == "Ondskans väsen" and rows[1]["locked"] == "title"
        assert [l["name"] for l in repo.libraries()] == ["Mina filmer", "Barnens"]
        assert settings.get("tmdb_language") == "en-US"
    assert json.loads(rows[2]["extra"]) == {"Subtitles": "Svenska"}


def test_music_import_never_overwrites_movies(config_dir):
    db.init()
    clz_import.import_csv(MOVIES_CSV, 1)
    before = titles("movie")
    r = clz_import.import_csv(MUSIC_CSV, 1)  # samma Index 1–2 som filmerna, i samma samling
    assert r["kind"] == "music" and r["added"] == 3 and r["updated"] == 0 and not r["errors"]
    assert titles("movie") == before == ["Evil Dead", "Alien"]
    assert counts() == {"movie": 2, "music": 3}

    r = clz_import.import_csv(MUSIC_CSV, 1)  # samma fil igen: uppdaterar, dubblerar inte
    assert (r["added"], r["updated"]) == (0, 3)
    r = clz_import.import_csv(MOVIES_CSV, 1)
    assert (r["kind"], r["added"], r["updated"]) == ("movie", 0, 2)
    assert counts() == {"movie": 2, "music": 3}


def test_music_fields(config_dir):
    db.init()
    clz_import.import_csv(MUSIC_CSV, 1)
    with db.connect() as con:
        rows = {r["title"]: db.row_to_dict(r) for r in con.execute("SELECT * FROM items")}
    b = rows["The Bridge"]
    assert (b["artist"], b["label"], b["cat_no"], b["year"], b["format"]) == ("Ace Of Base", "Mega Records", "MRCD 3295", 1996, "CD")
    assert (b["runtime"], b["tracks"], b["nr_discs"], b["my_rating"]) == (62, 17, 1, 8)
    assert (b["purchase_price"], b["location"], b["loaned_to"], b["added_date"]) == (40.0, "Lådan", "Lisa", "2026-03-19")
    a = rows["Absolute Music 24"]
    assert a["label"] == "EVA Records"  # Discogs-numret '(5)' tvättas bort
    assert a["runtime"] is None and a["barcode"] is None and a["artist"] == "Various"
    assert rows["The ABBA Generation"]["my_rating"] is None  # 0 = inget betyg i CLZ


def test_locked_fields_survive_reimport(config_dir):
    db.init()
    clz_import.import_csv(MUSIC_CSV, 1)
    with db.connect() as con:
        item_id = con.execute("SELECT id FROM items WHERE title='The Bridge'").fetchone()[0]
    repo.update(item_id, {"title": "Bron", "location": "Vardagsrummet"})
    clz_import.import_csv(MUSIC_CSV, 1)
    it = repo.get(item_id)
    assert (it["title"], it["location"]) == ("Bron", "Vardagsrummet")


def test_tabs_keep_music_apart(config_dir):
    db.init()
    clz_import.import_csv(MOVIES_CSV, 1)
    clz_import.import_csv(MUSIC_CSV, 1)
    assert {i["kind"] for i in repo.list_items(lib=1, kind="video")} == {"movie"}  # fliken "Alla" = film och serier
    assert {i["kind"] for i in repo.list_items(lib=1)} == {"movie", "music"}  # t.ex. utlånat och inventering
    music = repo.list_items(lib=1, kind="music", sort="artist")
    assert [i["artist"] for i in music] == ["A*Teens", "Ace Of Base", "Various"]
    assert repo.list_items(lib=1, kind="music", q="ace", field="all")[0]["title"] == "The Bridge"
    assert "Electronic" in repo.facets(1, "music")["genres"] and not repo.facets(1, "movie")["genres"]


def test_restore_backup(config_dir):
    db.init()
    clz_import.import_csv(MOVIES_CSV, 1)
    name = repo.backup_now()
    clz_import.import_csv(MUSIC_CSV, 1)
    assert counts() == {"movie": 2, "music": 3}

    result = repo.restore_backup(name=name)
    assert counts() == {"movie": 2}
    assert result["safety_copy"] in [b["name"] for b in repo.list_backups()]
    assert not os.path.exists(db.DB_PATH + "-wal") or os.path.getsize(db.DB_PATH + "-wal") == 0

    # och tillbaka igen från säkerhetskopian som togs automatiskt
    repo.restore_backup(name=result["safety_copy"])
    assert counts() == {"movie": 2, "music": 3}


def test_restore_rejects_bad_files(config_dir, tmp_path):
    db.init()
    with pytest.raises(repo.RestoreError):
        repo.restore_backup(data=b"inte en databas")
    other = tmp_path / "annan.db"
    con = sqlite3.connect(other)
    con.execute("CREATE TABLE foo (x)")
    con.commit()
    con.close()
    with pytest.raises(repo.RestoreError):
        repo.restore_backup(data=other.read_bytes())
    with pytest.raises(repo.RestoreError):
        repo.restore_backup(name="../diskoteket.db")


def test_restore_old_version_backup_is_upgraded(config_dir, tmp_path):
    db.init()
    old = tmp_path / "gammal.db"
    make(str(old), 2)
    repo.restore_backup(data=old.read_bytes())
    assert counts() == {"movie": 3, "tv": 1}
    assert repo.libraries()[0]["name"] == "Mina filmer"


@pytest.mark.parametrize("version", [1, 2, 3])
def test_old_installations_keep_swedish(config_dir, version):
    make(db.LEGACY_DB if version == 1 else db.DB_PATH, version)
    db.init()
    assert settings.get("language") == "sv"
