"""Streckkod -> film. Frågar källorna i tur och ordning och kommer ihåg svaren.

1. Inlärda koder (barcodes-tabellen) och titlar i andra samlingar
2. MyMovies – nordisk databas, ger titel, år, format och IMDb-ID (exakt träff)
3. UPCitemdb – gratis, mest amerikanska utgåvor (100 uppslag/dag)
4. EAN-DB – valfritt, kräver egen nyckel under Inställningar
"""
import html
import os
import re

import httpx

from . import db, settings, tmdb

MYMOVIES_URL = os.environ.get("MYMOVIES_URL", "https://www.mymovies.fi/")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
IMDB_RE = re.compile(r"imdb\.com/title/(tt\d{6,})")
YEAR_TITLE_RE = re.compile(r"^(?P<title>.+?)\s*\((?P<year>\d{4})\)\s*(?:[–\-|]\s*(?P<fmt>[^|]+?))?\s*(?:\||$)")


def normalize(code: str) -> str:
    return re.sub(r"\D", "", code or "")


def variants(code: str) -> list[str]:
    """EAN-13 och UPC-A skiljer sig ibland bara på en inledande nolla."""
    c = normalize(code)
    return list(dict.fromkeys([c, c.lstrip("0"), "0" + c]))


def clean_format(text: str | None) -> str | None:
    t = (text or "").lower()
    if "4k" in t or "uhd" in t:
        return "4K UHD"
    if "3d" in t and "blu" in t:
        return "Blu-ray 3D"
    if "blu" in t:
        return "Blu-ray"
    if "dvd" in t:
        return "DVD"
    if "vhs" in t:
        return "VHS"
    return None


# ---------- Inlärt ----------

def learn(code: str, tmdb_id: int, kind: str, title: str = None, year: int = None, fmt: str = None, source="du"):
    code = normalize(code)
    if not code or not tmdb_id:
        return
    with db.connect() as con:
        con.execute(
            "INSERT INTO barcodes (code, tmdb_id, kind, title, year, format, source) VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(code) DO UPDATE SET tmdb_id=excluded.tmdb_id, kind=excluded.kind, title=excluded.title, "
            "year=excluded.year, format=COALESCE(excluded.format, barcodes.format), source=excluded.source, "
            "updated=datetime('now')", (code, tmdb_id, kind, title, year, fmt, source))


def known(code: str) -> dict | None:
    """Inlärd kod, eller samma streckkod på en titel i någon samling."""
    v = variants(code)
    q = ",".join("?" * len(v))
    with db.connect() as con:
        r = con.execute(f"SELECT tmdb_id, kind, title, year, format, source FROM barcodes WHERE code IN ({q})", v).fetchone()
        if r:
            return {**dict(r), "source": "inlärd" if r["source"] == "du" else r["source"]}
        r = con.execute(f"SELECT tmdb_id, kind, COALESCE(series_name, title) AS title, year, format FROM items "
                        f"WHERE barcode IN ({q}) AND tmdb_id IS NOT NULL LIMIT 1", v).fetchone()
        if r:
            return {**dict(r), "source": "annan samling"}
    return None


# ---------- MyMovies ----------

def parse_mymovies(page: str) -> dict | None:
    """Plockar titel, år, format och IMDb-ID ur en produktsida. Okänd kod ger startsidan -> None."""
    m = (re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', page)
         or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title', page)
         or re.search(r"<title>([^<]+)</title>", page))
    if not m:
        return None
    full = html.unescape(m.group(1)).strip()
    t = YEAR_TITLE_RE.match(full)
    if not t:  # startsidan saknar (år) i titeln
        return None
    names = [n.strip() for n in t.group("title").split(" / ") if n.strip()]
    imdb = IMDB_RE.search(page)
    return {"title": names[0], "titles": names, "year": int(t.group("year")),
            "format": clean_format(t.group("fmt") or full), "imdb_id": imdb.group(1) if imdb else None,
            "source_title": full}


async def mymovies(code: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers={"User-Agent": UA}) as c:
            r = await c.get(MYMOVIES_URL, params={"tuote": normalize(code)})
        return parse_mymovies(r.text) if r.status_code == 200 else None
    except httpx.HTTPError:
        return None


# ---------- UPCitemdb och EAN-DB ----------

async def upcitemdb(code: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.get("https://api.upcitemdb.com/prod/trial/lookup", params={"upc": normalize(code)})
        if r.status_code == 200 and r.json().get("items"):
            return r.json()["items"][0].get("title")
    except (httpx.HTTPError, ValueError):
        pass
    return None


async def ean_db(code: str) -> str | None:
    token = settings.get("ean_db_token")
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=8, headers={"Authorization": f"Bearer {token}",
                                                         "Accept": "application/json"}) as c:
            r = await c.get(f"https://ean-db.com/api/v2/product/{normalize(code)}")
        if r.status_code == 200:
            titles = (r.json().get("product") or {}).get("titles") or {}
            return titles.get("sv") or titles.get("en") or next(iter(titles.values()), None)
    except (httpx.HTTPError, ValueError):
        pass
    return None


# ---------- Allt i tur och ordning ----------

async def _match_from(found: dict, source: str) -> dict | None:
    """Gör en exakt TMDB-träff av ett IMDb-ID, annars titel + år."""
    hit = None
    if found.get("imdb_id") and tmdb.enabled():
        f = await tmdb.find_by_imdb(found["imdb_id"])
        if f:
            hit = {"tmdb_id": f["tmdb_id"], "type": f["type"]}
    if not hit and tmdb.enabled():
        for name in found.get("titles") or [found["title"]]:
            res = [r for r in await tmdb.search(name, found.get("year"))
                   if not found.get("year") or not r["year"] or abs(r["year"] - found["year"]) <= 1]
            if res:
                hit = {"tmdb_id": res[0]["tmdb_id"], "type": res[0]["type"]}
                break
    if not hit:
        return None
    d = await tmdb.details(hit["tmdb_id"], hit["type"])
    return {"tmdb_id": d["tmdb_id"], "type": d["kind"], "title": d["title"], "year": d["year"],
            "poster_path": d["poster_path"], "original_title": d["original_title"],
            "format": found.get("format"), "source": source}


async def lookup(code: str) -> dict:
    """Svar: {match, product_title, query, candidates, tried}."""
    out = {"match": None, "product_title": None, "query": "", "candidates": [], "tried": []}

    k = known(code)
    if k and tmdb.enabled():
        try:
            d = await tmdb.details(k["tmdb_id"], "tv" if k["kind"] == "tv" else "movie")
            out["match"] = {"tmdb_id": d["tmdb_id"], "type": d["kind"], "title": d["title"], "year": d["year"],
                            "poster_path": d["poster_path"], "original_title": d["original_title"],
                            "format": k.get("format"), "source": k["source"]}
            return out
        except Exception:
            pass
    out["tried"].append("dina samlingar")

    if settings.get_bool("lookup_mymovies"):
        out["tried"].append("MyMovies")
        mm = await mymovies(code)
        if mm:
            out["product_title"] = mm["source_title"]
            out["query"] = mm["titles"][-1]
            try:
                match = await _match_from(mm, "MyMovies")
            except Exception:
                match = None
            if match:
                out["match"] = match
                learn(code, match["tmdb_id"], match["type"], match["title"], match["year"], match["format"], "MyMovies")
                return out

    title = None
    if not out["product_title"] and settings.get_bool("lookup_upcitemdb"):
        out["tried"].append("UPCitemdb")
        title = await upcitemdb(code)
    if not title and not out["product_title"] and settings.get("ean_db_token"):
        out["tried"].append("EAN-DB")
        title = await ean_db(code)
    if title:
        out["product_title"] = title
        out["query"] = tmdb.clean_product_title(title)

    if out["query"] and tmdb.enabled():
        out["candidates"] = await tmdb.search(out["query"])
    return out
