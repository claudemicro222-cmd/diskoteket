"""Hämtar vilka filmer och serier som finns digitalt i Plex och/eller Jellyfin.
Matchning sker på IMDb- och TMDB-ID, så titlar på olika språk spelar ingen roll."""
import re

import httpx

from . import db, settings


def _url(key):
    u = settings.get(key).rstrip("/")
    return u if not u or u.startswith("http") else "http://" + u


def configured():
    out = []
    if _url("plex_url") and settings.get("plex_token"):
        out.append("plex")
    if _url("jellyfin_url") and settings.get("jellyfin_api_key"):
        out.append("jellyfin")
    return out


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def jellyfin_headers() -> dict:
    """Jellyfin 10.10+ vill ha nyckeln i Authorization-headern. Det gamla sättet (X-Emby-Token)
    är avstängt som standard från Jellyfin 12 och ger då '401 Unauthorized'."""
    key = settings.get("jellyfin_api_key")
    return {"Authorization": f'MediaBrowser Client="Diskoteket", Device="Server", DeviceId="diskoteket", '
                             f'Version="4.1", Token="{key}"'}


async def fetch_jellyfin() -> list[dict]:
    async with httpx.AsyncClient(timeout=60, headers=jellyfin_headers()) as c:
        r = await c.get(f"{_url('jellyfin_url')}/Items", params={
            "IncludeItemTypes": "Movie,Series", "Recursive": "true", "Fields": "ProviderIds"})
        r.raise_for_status()
    out = []
    for it in r.json().get("Items", []):
        ids = {k.lower(): v for k, v in (it.get("ProviderIds") or {}).items()}
        out.append({"kind": "tv" if it.get("Type") == "Series" else "movie",
                    "imdb_id": ids.get("imdb"), "tmdb_id": _int(ids.get("tmdb")),
                    "title": it.get("Name"), "year": it.get("ProductionYear")})
    return out


async def fetch_plex() -> list[dict]:
    headers = {"X-Plex-Token": settings.get("plex_token"), "Accept": "application/json"}
    PLEX_URL = _url("plex_url")
    out = []
    async with httpx.AsyncClient(timeout=60, headers=headers) as c:
        r = await c.get(f"{PLEX_URL}/library/sections")
        r.raise_for_status()
        sections = [d for d in r.json()["MediaContainer"].get("Directory", []) if d.get("type") in ("movie", "show")]
        for s in sections:
            r = await c.get(f"{PLEX_URL}/library/sections/{s['key']}/all", params={"includeGuids": 1})
            r.raise_for_status()
            for m in r.json()["MediaContainer"].get("Metadata", []):
                imdb = tmdb = None
                for g in m.get("Guid", []):
                    gid = g.get("id", "")
                    if gid.startswith("imdb://"):
                        imdb = gid[7:]
                    elif gid.startswith("tmdb://"):
                        tmdb = _int(gid[7:])
                # äldre Plex-agenter lägger IMDb-ID i 'guid'
                if not imdb:
                    mm = re.search(r"(tt\d{6,})", m.get("guid", ""))
                    imdb = mm.group(1) if mm else None
                out.append({"kind": "tv" if s["type"] == "show" else "movie", "imdb_id": imdb, "tmdb_id": tmdb, "title": m.get("title"), "year": m.get("year")})
    return out


async def sync(only: str | None = None) -> dict:
    result = {}
    for source, fetch in (("plex", fetch_plex), ("jellyfin", fetch_jellyfin)):
        if source not in configured() or (only and source != only):
            continue
        try:
            rows = await fetch()
        except Exception as e:  # visa felet i appen i stället för att krascha
            result[source] = f"Fel: {e}"
            continue
        with db.connect() as con:
            con.execute("DELETE FROM digital WHERE source=?", (source,))
            con.executemany(
                "INSERT INTO digital (source, kind, imdb_id, tmdb_id, title, year) VALUES (?, ?, ?, ?, ?, ?)",
                [(source, r["kind"], r["imdb_id"], r["tmdb_id"], r["title"], r["year"]) for r in rows])
        result[source] = len(rows)
    return result
