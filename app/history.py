"""Tittarhistorik (när och hur många gånger), import från Letterboxd och Trakt,
årsöversikten och samlingens utveckling över tid."""
import csv
import io
import json
import re
from datetime import date

from . import db, repo
from .covers import norm


# ---------- Visningar ----------

def add_view(item_id: int, day: str | None = None, source: str = "du") -> dict:
    day = day or date.today().isoformat()
    with db.connect() as con:
        if not con.execute("SELECT 1 FROM views WHERE item_id=? AND date=?", (item_id, day)).fetchone():
            con.execute("INSERT INTO views (item_id, date, source) VALUES (?, ?, ?)", (item_id, day, source))
        con.execute("UPDATE items SET watched=1 WHERE id=?", (item_id,))
    return views_for(item_id)


def remove_view(view_id: int) -> int | None:
    with db.connect() as con:
        r = con.execute("SELECT item_id FROM views WHERE id=?", (view_id,)).fetchone()
        if not r:
            return None
        con.execute("DELETE FROM views WHERE id=?", (view_id,))
        if not con.execute("SELECT 1 FROM views WHERE item_id=?", (r["item_id"],)).fetchone():
            con.execute("UPDATE items SET watched=0 WHERE id=?", (r["item_id"],))
    return r["item_id"]


def views_for(item_id: int) -> list[dict]:
    with db.connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT id, date, source FROM views WHERE item_id=? ORDER BY date DESC", (item_id,))]


# ---------- Import från Letterboxd och Trakt ----------

def _owned_index(con):
    """Uppslag för matchning: IMDb-, TMDB-ID och titel + år."""
    rows = [dict(r) for r in con.execute(
        f"SELECT id, kind, title, original_title, series_name, season, year, imdb_id, tmdb_id FROM items "
        f"WHERE kind != 'music' AND {repo.OWNED}")]
    by_imdb, by_tmdb, by_title = {}, {}, {}
    for r in rows:
        if r["imdb_id"]:
            by_imdb.setdefault(r["imdb_id"], []).append(r)
        if r["tmdb_id"]:
            by_tmdb.setdefault((r["kind"], r["tmdb_id"]), []).append(r)
        for t in {norm(r["title"]), norm(r["original_title"]), norm(r["series_name"])} - {""}:
            by_title.setdefault(t, []).append(r)
    return by_imdb, by_tmdb, by_title


def _match(index, kind="movie", title=None, year=None, imdb=None, tmdb_id=None, season=None):
    by_imdb, by_tmdb, by_title = index
    hits = (by_imdb.get(imdb) if imdb else None) or (by_tmdb.get((kind, tmdb_id)) if tmdb_id else None)
    if not hits and title:
        hits = [h for h in by_title.get(norm(title), []) if h["kind"] == kind
                and (not year or not h["year"] or abs(h["year"] - int(year)) <= 1 or kind == "tv")]
    if hits and season is not None:
        hits = [h for h in hits if h["season"] in (season, None)] or hits
    return hits or []


def _save(con, matches: dict, source: str) -> int:
    n = 0
    for (item_id, day) in matches:
        if not con.execute("SELECT 1 FROM views WHERE item_id=? AND date=?", (item_id, day)).fetchone():
            con.execute("INSERT INTO views (item_id, date, source) VALUES (?, ?, ?)", (item_id, day, source))
            n += 1
        con.execute("UPDATE items SET watched=1 WHERE id=?", (item_id,))
    return n


def import_letterboxd(raw: bytes) -> dict:
    """diary.csv eller watched.csv från Letterboxd (Settings → Import & Export → Export your data)."""
    text = raw.decode("utf-8-sig", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or "Name" not in rows[0]:
        raise ValueError("Det här ser inte ut som en export från Letterboxd (diary.csv eller watched.csv)")
    found, missing = {}, []
    with db.connect() as con:
        index = _owned_index(con)
        for r in rows:
            day = (r.get("Watched Date") or r.get("Date") or "")[:10]
            hits = _match(index, "movie", r.get("Name"), r.get("Year") or None)
            if hits and re.match(r"\d{4}-\d{2}-\d{2}$", day):
                for h in hits:
                    found[(h["id"], day)] = True
            elif not hits:
                missing.append(f"{r.get('Name')} ({r.get('Year')})")
        added = _save(con, found, "letterboxd")
    return {"rows": len(rows), "matched": len({k[0] for k in found}), "views_added": added,
            "not_owned": len(missing), "examples": missing[:10]}


def import_trakt(raw: bytes) -> dict:
    """JSON från Trakt: historik (watched_at per visning) eller watched-listan (last_watched_at)."""
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except ValueError:
        raise ValueError("Filen är ingen JSON-export från Trakt")
    if isinstance(data, dict):
        data = data.get("history") or data.get("watched") or data.get("movies") or []
    found, missing = {}, []
    with db.connect() as con:
        index = _owned_index(con)
        for e in data if isinstance(data, list) else []:
            day = (e.get("watched_at") or e.get("last_watched_at") or "")[:10]
            if not re.match(r"\d{4}-\d{2}-\d{2}$", day):
                continue
            if e.get("movie"):
                m = e["movie"]
                ids = m.get("ids") or {}
                hits = _match(index, "movie", m.get("title"), m.get("year"), ids.get("imdb"), ids.get("tmdb"))
                label = f"{m.get('title')} ({m.get('year')})"
            elif e.get("show"):
                s = e["show"]
                ids = s.get("ids") or {}
                season = (e.get("episode") or {}).get("season")
                hits = _match(index, "tv", s.get("title"), s.get("year"), ids.get("imdb"), ids.get("tmdb"), season)
                label = s.get("title")
            else:
                continue
            for h in hits:
                found[(h["id"], day)] = True
            if not hits:
                missing.append(label)
        added = _save(con, found, "trakt")
    return {"rows": len(data) if isinstance(data, list) else 0, "matched": len({k[0] for k in found}),
            "views_added": added, "not_owned": len(set(missing)), "examples": sorted(set(missing))[:10]}


# ---------- Årsöversikt ----------

def years(lib=None) -> list[int]:
    s, a = repo._lib(lib, " AND i.")
    with db.connect() as con:
        ys = {int(r[0]) for r in con.execute(
            f"SELECT DISTINCT substr(added_date, 1, 4) FROM items i WHERE added_date GLOB '[12][0-9][0-9][0-9]*'{s}", a)}
        ys |= {int(r[0]) for r in con.execute(
            f"SELECT DISTINCT substr(v.date, 1, 4) FROM views v JOIN items i ON i.id = v.item_id WHERE 1=1{s}", a)}
    return sorted(ys, reverse=True)


def year_review(year: int, lib=None) -> dict:
    y = str(year)
    s, a = repo._lib(lib, " AND i.")
    with db.connect() as con:
        q = lambda sql, *args: [dict(r) for r in con.execute(sql, [*args, *a])]  # noqa: E731
        added = q(f"SELECT i.id, i.kind, i.title, i.artist, i.year, i.format, i.poster_path, i.purchase_price, "
                  f"i.added_date FROM items i WHERE substr(i.added_date, 1, 4)=? AND {repo.OWNED}{s} "
                  "ORDER BY i.added_date DESC, i.id DESC", y)
        watched = q(f"SELECT v.date, i.id, i.kind, i.title, i.genres, i.runtime, i.poster_path, i.year FROM views v "
                    f"JOIN items i ON i.id = v.item_id WHERE substr(v.date, 1, 4)=?{s} ORDER BY v.date", y)
    genres, per_title, months = {}, {}, [0] * 12
    for w in watched:
        for g in (w["genres"] or "").split(" | "):
            if g.strip():
                genres[g.strip()] = genres.get(g.strip(), 0) + 1
        per_title.setdefault(w["id"], {**w, "n": 0})["n"] += 1
        months[int(w["date"][5:7]) - 1] += 1
    artists = {}
    for it in added:
        if it["kind"] == "music" and it["artist"] and not repo.is_various(it["artist"]):
            artists[it["artist"]] = artists.get(it["artist"], 0) + 1
    priced = sorted([i for i in added if i["purchase_price"]], key=lambda i: -i["purchase_price"])
    return {
        "year": year,
        "added": {"total": len(added), "movies": sum(i["kind"] == "movie" for i in added),
                  "seasons": sum(i["kind"] == "tv" for i in added), "music": sum(i["kind"] == "music" for i in added),
                  "latest": added[:18]},
        "spent": round(sum(i["purchase_price"] or 0 for i in added), 2),
        "most_expensive": priced[:5],
        "watched": {"views": len(watched), "titles": len(per_title),
                    "minutes": sum(w["runtime"] or 0 for w in watched),
                    "genres": repo._top(genres, 8), "months": months,
                    "most": sorted(per_title.values(), key=lambda t: -t["n"])[:6],
                    "first": watched[0] if watched else None, "last": watched[-1] if watched else None},
        "top_artists": repo._top(artists, 6),
    }


# ---------- Samlingens utveckling ----------

def growth(lib=None) -> dict:
    """Per år: hur många titlar som tillkom och vad de kostade, plus löpande summor."""
    s, a = repo._lib(lib)
    with db.connect() as con:
        rows = [dict(r) for r in con.execute(
            f"SELECT substr(added_date, 1, 4) AS y, kind, COUNT(*) AS n, COALESCE(SUM(purchase_price), 0) AS spent "
            f"FROM items WHERE {repo.OWNED} AND added_date GLOB '[12][0-9][0-9][0-9]*'{s} GROUP BY y, kind ORDER BY y", a)]
        undated = con.execute(f"SELECT COUNT(*) FROM items WHERE {repo.OWNED} AND (added_date IS NULL OR added_date = ''){s}",
                              a).fetchone()[0]
    out, total, spent = {}, 0, 0.0
    for r in rows:
        y = out.setdefault(r["y"], {"year": int(r["y"]), "movie": 0, "tv": 0, "music": 0, "added": 0, "spent": 0.0})
        y[r["kind"]] = y.get(r["kind"], 0) + r["n"]
        y["added"] += r["n"]
        y["spent"] += r["spent"]
    years_ = list(out.values())
    for y in years_:
        total += y["added"]
        spent += y["spent"]
        y["total"], y["spent_total"], y["spent"] = total, round(spent, 2), round(y["spent"], 2)
    return {"years": years_, "undated": undated}
