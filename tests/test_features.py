"""Version 4.1: papperskorg, massredigering, taggar, tittarhistorik, import från Letterboxd/Trakt,
hyllkarta, årsöversikt, utveckling, uppgraderings- och säljlista samt vänsidan."""
import json

import pytest
from starlette.testclient import TestClient

from app import db, history, main, repo, trash

from .test_upgrade import MOVIES_CSV, MUSIC_CSV


@pytest.fixture
def client(config_dir):
    with TestClient(main.app) as c:
        c.post("/api/import", files={"file": ("filmer.csv", MOVIES_CSV)}, data={"library_id": "1"})
        c.post("/api/import", files={"file": ("musik.csv", MUSIC_CSV)}, data={"library_id": "1"})
        yield c


def ids(c, **params):
    return {i["title"]: i["id"] for i in c.get("/api/items", params={"lib": 1, **params}).json()}


def test_trash_and_restore_keeps_history(client):
    alien = ids(client, kind="video")["Alien"]
    client.post(f"/api/items/{alien}/views", json={"date": "2024-12-24"})
    assert client.delete(f"/api/items/{alien}").status_code == 200
    assert "Alien" not in ids(client, kind="video")
    assert [t["title"] for t in client.get("/api/trash").json()] == ["Alien"]

    assert client.post(f"/api/trash/{alien}/restore").status_code == 200
    assert ids(client, kind="video")["Alien"] == alien  # samma id som förut
    assert [v["date"] for v in client.get(f"/api/items/{alien}/views").json()] == ["2024-12-24"]
    assert client.get("/api/trash").json() == []


def test_trash_purge_only_old(config_dir):
    db.init()
    with db.connect() as con:
        con.execute("INSERT INTO trash (id, item, deleted) VALUES (1, '{}', datetime('now', '-40 days')), "
                    "(2, '{}', datetime('now', '-2 days'))")
    assert trash.purge() == 1
    with db.connect() as con:
        assert [r[0] for r in con.execute("SELECT id FROM trash")] == [2]


def test_bulk_edit_and_tags(client):
    m = ids(client, kind="music")
    sel = [m["The Bridge"], m["The ABBA Generation"]]
    r = client.post("/api/items/bulk", json={"ids": sel, "changes": {"location": "Hylla B"}, "add_tags": ["Fest", "90-tal"]})
    assert r.json()["updated"] == 2
    tagged = client.get("/api/items", params={"lib": 1, "kind": "music", "tag": "Fest"}).json()
    assert {i["title"] for i in tagged} == {"The Bridge", "The ABBA Generation"}
    assert {i["location"] for i in tagged} == {"Hylla B"}
    assert client.get("/api/tags").json() == ["90-tal", "Fest"]
    client.post("/api/items/bulk", json={"ids": sel[:1], "remove_tags": ["fest"]})
    assert repo.get(sel[0])["tags"] == "90-tal"
    assert "location" in repo.get(sel[0])["locked"]  # en ny CLZ-import skriver inte över
    client.post("/api/items/bulk", json={"ids": sel, "delete": True})
    assert len(client.get("/api/trash").json()) == 2


def test_upgrade_and_sale_lists(client):
    v = ids(client, kind="video")
    client.patch(f"/api/items/{v['Evil Dead']}", json={"upgrade_to": "4K UHD"})
    client.patch(f"/api/items/{v['Alien']}", json={"collection_status": "For Sale", "sell_price": "79,50",
                                                    "condition": "Mycket bra", "condition_notes": "Repa på skiva 2"})
    assert [i["title"] for i in client.get("/api/items", params={"status": "upgrade"}).json()] == ["Evil Dead"]
    sale = client.get("/api/items", params={"status": "sale"}).json()
    assert [(i["title"], i["sell_price"], i["condition"]) for i in sale] == [("Alien", 79.5, "Mycket bra")]
    assert "Alien" in ids(client, kind="video")  # till salu räknas fortfarande som ägd


def test_watched_adds_history(client):
    alien = ids(client, kind="video")["Alien"]
    client.patch(f"/api/items/{alien}", json={"watched": 1})
    client.post(f"/api/items/{alien}/views", json={"date": "2023-01-02"})
    views = client.get(f"/api/items/{alien}/views").json()
    assert len(views) == 2
    for v in views:
        client.delete(f"/api/views/{v['id']}")
    assert repo.get(alien)["watched"] == 0


def test_letterboxd_and_trakt_import(client):
    lb = "Date,Name,Year,Letterboxd URI,Rating,Rewatch,Tags,Watched Date\n" \
         "2024-02-01,Alien,1979,https://boxd.it/x,4,,,2024-01-31\n" \
         "2024-03-01,The Matrix,1999,https://boxd.it/y,5,,,2024-03-01\n"
    r = client.post("/api/import/history", files={"file": ("diary.csv", lb.encode())}).json()
    assert (r["source"], r["matched"], r["views_added"], r["not_owned"]) == ("Letterboxd", 1, 1, 1)
    trakt = [{"watched_at": "2022-05-05T20:00:00.000Z", "type": "movie", "movie": {"title": "Evil Dead", "year": 1981, "ids": {}}},
             {"watched_at": "2024-01-31T20:00:00.000Z", "type": "movie", "movie": {"title": "Alien", "year": 1979, "ids": {}}}]
    r = client.post("/api/import/history", files={"file": ("history.json", json.dumps(trakt).encode())}).json()
    assert (r["source"], r["matched"], r["views_added"]) == ("Trakt", 2, 1)  # Alien 2024-01-31 fanns redan
    assert client.post("/api/import/history", files={"file": ("x.csv", b"a,b\n1,2\n")}).status_code == 400


def test_year_review_and_growth(client):
    alien = ids(client, kind="video")["Alien"]
    with db.connect() as con:
        con.execute("UPDATE items SET added_date='2025-06-01', purchase_price=99, genres='Skräck | Sci-Fi' WHERE id=?", (alien,))
    history.add_view(alien, "2025-07-01")
    history.add_view(alien, "2025-08-01")
    y = client.get("/api/year", params={"year": 2025, "lib": 1}).json()
    assert 2025 in y["years"] and 2026 in y["years"]
    assert y["added"]["movies"] == 1 and y["spent"] == 99
    assert y["watched"]["views"] == 2 and y["watched"]["most"][0]["n"] == 2
    assert y["watched"]["genres"][0]["label"] in ("Skräck", "Sci-Fi") and y["watched"]["months"][6] == 1
    g = client.get("/api/growth", params={"lib": 1}).json()
    totals = {row["year"]: row["total"] for row in g["years"]}
    assert totals[2025] == 1 and totals[max(totals)] == 4  # Alien 2025 + 3 album 2026 (filmerna saknar datum)
    assert g["undated"] == 1


def test_locations_rename_and_photo(client):
    v = ids(client, kind="video")
    client.put("/api/locations", json={"name": "Hylla A", "description": "Vardagsrummet, vänster"})
    locs = {l["name"]: l for l in client.get("/api/locations").json()}
    assert locs["Hylla A"]["count"] == 2 and locs["Hylla A"]["description"] == "Vardagsrummet, vänster"
    client.put("/api/locations", json={"name": "Hylla A", "new_name": "Hylla 1"})
    assert repo.get(v["Alien"])["location"] == "Hylla 1" and "location" in repo.get(v["Alien"])["locked"]
    assert "Hylla A" not in {l["name"] for l in client.get("/api/locations").json()}


def test_share_page_and_loan_request(client):
    client.put("/api/auth", json={"password": "hemligt"})
    t = client.put("/api/share", json={"enable": True}).json()["token"]
    client.cookies.clear()
    assert client.get("/api/items").status_code == 401  # appen är låst …
    page = client.get(f"/share/{t}")
    assert page.status_code == 200  # … men vänsidan fungerar med länken
    items = client.get(f"/api/share/{t}/items", params={"kind": "music"}).json()["items"]
    assert len(items) == 3 and "purchase_price" not in items[0] and "barcode" not in items[0]
    assert client.get("/api/share/fel/items").status_code == 404
    assert client.post(f"/api/share/{t}/request", json={"item_id": items[0]["id"], "name": ""}).status_code == 400
    assert client.post(f"/api/share/{t}/request", json={"item_id": items[0]["id"], "name": "Kalle"}).status_code == 200

    assert client.post("/api/login", json={"password": "hemligt"}).status_code == 200
    reqs = client.get("/api/loan-requests").json()
    assert [r["name"] for r in reqs] == ["Kalle"]
    client.post(f"/api/loan-requests/{reqs[0]['id']}", json={"lend": True})
    assert repo.get(items[0]["id"])["loaned_to"] == "Kalle"
    assert client.get("/api/loan-requests").json() == []
    client.put("/api/share", json={"enable": False})
    assert client.get(f"/api/share/{t}/items").status_code == 404
