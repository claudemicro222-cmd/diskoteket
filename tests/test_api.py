"""Webb-API:t: inloggning, export, återställning och musik – utan att gå ut på nätet."""
import json

import pytest
from starlette.testclient import TestClient

from app import auth, db, main

from .test_upgrade import MOVIES_CSV, MUSIC_CSV


@pytest.fixture
def client(config_dir):
    with TestClient(main.app) as c:
        c.post("/api/import", files={"file": ("filmer.csv", MOVIES_CSV)}, data={"library_id": "1"})
        c.post("/api/import", files={"file": ("musik.csv", MUSIC_CSV)}, data={"library_id": "1"})
        yield c


def test_tabs_and_facets(client):
    assert {i["kind"] for i in client.get("/api/items?lib=1&kind=video").json()} == {"movie"}
    music = client.get("/api/items?lib=1&kind=music&sort=artist").json()
    assert [m["title"] for m in music] == ["The ABBA Generation", "The Bridge", "Absolute Music 24"]
    assert "CD" in client.get("/api/facets?lib=1&kind=music").json()["formats"]
    s = client.get("/api/stats?lib=1").json()
    assert s["movies"] == 2 and s["music"]["albums"] == 3 and s["music"]["compilations"] == 1
    assert s["value"]["total"] == 40.0
    ha = client.get("/api/ha").json()
    assert (ha["movies"], ha["music"], ha["total"]) == (2, 3, 5)


def test_login_protects_everything_but_static(client):
    assert client.get("/api/auth").json() == {"enabled": False, "api_key": None}
    r = client.put("/api/auth", json={"password": "hemligt"})
    assert r.status_code == 200 and r.json()["enabled"]
    key = r.json()["api_key"]
    assert client.get("/api/items").status_code == 200  # den som satte lösenordet är inloggad

    client.cookies.clear()
    assert client.get("/api/items").status_code == 401
    assert "Logga in" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/ha", headers={"Authorization": f"Bearer {key}"}).status_code == 200
    assert client.get("/api/items", headers={"Authorization": f"Bearer {key}"}).status_code == 401  # bara /api/ha
    assert client.get("/api/ha", headers={"Authorization": "Bearer fel"}).status_code == 401

    assert client.post("/api/login", json={"password": "fel"}).status_code == 401
    assert client.post("/api/login", json={"password": "hemligt"}).status_code == 200
    assert client.get("/api/items").status_code == 200
    client.put("/api/auth", json={"disable": True})
    client.cookies.clear()
    assert client.get("/api/items").status_code == 200


def test_restore_keeps_password(client):
    """Lösenordet ligger utanför databasen, så en gammal säkerhetskopia tar inte bort det."""
    name = client.post("/api/backup").json()["name"]
    client.put("/api/auth", json={"password": "hemligt"})
    r = client.post("/api/restore", json={"name": name})
    assert r.status_code == 200, r.text
    assert auth.enabled()
    r = client.post("/api/restore", files={"file": ("x.db", "skräp".encode())})
    assert r.status_code == 400


def test_export(client):
    r = client.get("/api/export?format=csv&lib=1")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    text = r.content.decode("utf-8-sig")
    assert "The Bridge" in text and "Alien" in text and "Mina filmer" in text
    data = json.loads(client.get("/api/export?format=json").content)
    assert len(data["items"]) == 5 and data["libraries"][0]["name"] == "Mina filmer"


def test_music_manual_add_and_duplicates(client):
    r = client.post("/api/music/manual", json={"title": "The Bridge", "artist": "Ace of Base", "format": "Vinyl",
                                               "library_id": 1, "barcode": "123"})
    assert r.status_code == 200 and r.json()["kind"] == "music"
    dupes = client.get("/api/stats?lib=1").json()["duplicates"]
    assert len(dupes) == 1 and {i["format"] for i in dupes[0]["items"]} == {"CD", "Vinyl"}
    assert client.get("/api/barcode/123?lib=1").json()["existing"][0]["title"] == "The Bridge"


def test_digital_only(client):
    with db.connect() as con:
        con.execute("UPDATE items SET imdb_id='tt0083907' WHERE title='Evil Dead'")
        con.executemany("INSERT INTO digital (source, kind, imdb_id, tmdb_id, title, year) VALUES (?, ?, ?, ?, ?, ?)",
                        [("plex", "movie", "tt0083907", None, "The Evil Dead", 1981),
                         ("plex", "movie", "tt0133093", 603, "The Matrix", 1999),
                         ("jellyfin", "movie", "tt0133093", 603, "The Matrix", 1999)])
    only = client.get("/api/digital/only?lib=1").json()
    assert [(o["title"], sorted(o["sources"])) for o in only] == [("The Matrix", ["jellyfin", "plex"])]
