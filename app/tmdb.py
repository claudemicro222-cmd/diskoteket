"""TMDB (omslag, handling, sökning, filmserier) och streckkodsuppslag på nätet."""
import re
from datetime import date

import httpx

from . import settings

import os

API = os.environ.get("TMDB_API", "https://api.themoviedb.org/3")
IMG = os.environ.get("TMDB_IMG", "https://image.tmdb.org/t/p/")

_client: httpx.AsyncClient | None = None
_client_token = None


def lang():
    return settings.get("tmdb_language") or "sv-SE"


def client() -> httpx.AsyncClient:
    """En delad klient, så att många anrop i rad återanvänder anslutningen.
    Byggs om automatiskt om nyckeln ändras på inställningssidan."""
    global _client, _client_token
    token = settings.get("tmdb_token")
    if _client is None or token != _client_token:
        _client_token = token
        _client = httpx.AsyncClient(
            base_url=API, timeout=20,
            headers={"Authorization": f"Bearer {token}", "accept": "application/json"},
            limits=httpx.Limits(max_connections=10),
        )
    return _client


def enabled():
    return bool(settings.get("tmdb_token"))


async def test() -> tuple[bool, str]:
    """Kontrollerar att nyckeln fungerar (för inställningssidan)."""
    try:
        r = await client().get("/authentication")
        if r.status_code == 200:
            return True, "Nyckeln fungerar"
        return False, "TMDB svarade: fel nyckel" if r.status_code == 401 else f"TMDB svarade {r.status_code}"
    except httpx.HTTPError as e:
        return False, f"Kunde inte nå TMDB: {e}"


async def _get(path, **params):
    params.setdefault("language", lang())
    params = {k: v for k, v in params.items() if v is not None}
    for attempt in range(3):
        r = await client().get(path, params=params)
        if r.status_code == 429:  # för många anrop – vänta lite och försök igen
            import asyncio
            await asyncio.sleep(1 + attempt * 2)
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    return None


async def find_by_imdb(imdb_id: str, season: int | None = None) -> dict | None:
    """Hitta TMDB-ID och omslag utifrån IMDb-ID. För serier hämtas säsongens eget omslag."""
    data = await _get(f"/find/{imdb_id}", external_source="imdb_id")
    if not data:
        return None
    for key in ("movie_results", "tv_results", "tv_episode_results", "tv_season_results"):
        if data.get(key):
            hit = data[key][0]
            result = {"tmdb_id": hit.get("show_id") or hit["id"], "poster_path": hit.get("poster_path"),
                      "overview": hit.get("overview"), "type": "movie" if key == "movie_results" else "tv"}
            if result["type"] == "tv" and season:
                s = await _get(f"/tv/{result['tmdb_id']}/season/{season}")
                if s and s.get("poster_path"):
                    result["poster_path"] = s["poster_path"]
            return result
    return None


async def movie_collection(tmdb_id: int) -> dict | None:
    """Vilken filmserie (t.ex. 'James Bond Collection') hör filmen till?"""
    d = await _get(f"/movie/{tmdb_id}")
    c = (d or {}).get("belongs_to_collection")
    return {"id": c["id"], "name": c["name"]} if c else None


async def season(tv_id: int, number: int) -> dict | None:
    d = await _get(f"/tv/{tv_id}/season/{number}")
    if not d:
        return None
    date = d.get("air_date") or ""
    return {"poster_path": d.get("poster_path"), "overview": d.get("overview"),
            "year": int(date[:4]) if date[:4].isdigit() else None, "episodes": len(d.get("episodes") or [])}


async def collection(collection_id: int) -> dict | None:
    d = await _get(f"/collection/{collection_id}")
    if not d:
        return None
    parts = []
    for p in d.get("parts", []):
        date = p.get("release_date") or ""
        parts.append({"tmdb_id": p["id"], "title": p.get("title"), "poster_path": p.get("poster_path"),
                      "year": int(date[:4]) if date[:4].isdigit() else None, "type": "movie"})
    parts.sort(key=lambda p: p["year"] or 9999)
    return {"id": d["id"], "name": d.get("name"), "poster_path": d.get("poster_path"), "parts": parts}


async def search(query: str, year: int | None = None) -> list[dict]:
    data = await _get("/search/multi", query=query, include_adult="false") or {}
    out = []
    for h in data.get("results", []):
        if h.get("media_type") not in ("movie", "tv"):
            continue
        date = h.get("release_date") or h.get("first_air_date") or ""
        out.append({
            "tmdb_id": h["id"], "type": h["media_type"],
            "title": h.get("title") or h.get("name"),
            "original_title": h.get("original_title") or h.get("original_name"),
            "year": int(date[:4]) if date[:4].isdigit() else None,
            "poster_path": h.get("poster_path"),
            "overview": h.get("overview"),
        })
    if year:  # samma år först
        out.sort(key=lambda x: x["year"] != year)
    return out[:10]


async def details(tmdb_id: int, media_type: str) -> dict:
    """Allt som behövs för att skapa en ny post från en TMDB-träff."""
    path = "movie" if media_type == "movie" else "tv"
    d = await _get(f"/{path}/{tmdb_id}", append_to_response="credits,external_ids")
    if not d:
        raise ValueError("Hittades inte på TMDB")
    if not d.get("overview") and lang() != "en-US":  # saknas svensk text, ta engelsk
        en = await _get(f"/{path}/{tmdb_id}", language="en-US")
        d["overview"] = (en or {}).get("overview")
    date = d.get("release_date") or d.get("first_air_date") or ""
    crew = d.get("credits", {}).get("crew", [])
    directors = [p["name"] for p in crew if p.get("job") == "Director"] or \
                [p["name"] for p in d.get("created_by", [])]
    runtime = d.get("runtime") or (d.get("episode_run_time") or [None])[0]
    coll = d.get("belongs_to_collection")
    return {
        "kind": "movie" if media_type == "movie" else "tv",
        "title": d.get("title") or d.get("name"),
        "original_title": d.get("original_title") or d.get("original_name"),
        "year": int(date[:4]) if date[:4].isdigit() else None,
        "genres": " | ".join(g["name"] for g in d.get("genres", [])),
        "runtime": runtime,
        "director": " | ".join(directors[:3]) or None,
        "actors": " | ".join(p["name"] for p in d.get("credits", {}).get("cast", [])[:5]) or None,
        "plot": d.get("overview"),
        "imdb_id": (d.get("external_ids") or {}).get("imdb_id") or d.get("imdb_id"),
        "tmdb_id": d["id"],
        "poster_path": d.get("poster_path"),
        "collection_id": coll["id"] if coll else None,
        "collection_name": coll["name"] if coll else None,
    }


async def posters(tmdb_id: int, media_type: str, season: int | None = None) -> list[str]:
    """Alla omslag som finns för en titel, så man kan välja ett annat."""
    path = f"/{'movie' if media_type == 'movie' else 'tv'}/{tmdb_id}"
    if media_type == "tv" and season:
        path += f"/season/{season}"
    d = await _get(path + "/images", language=None, include_image_language=f"{lang()[:2]},en,null") or {}
    return [p["file_path"] for p in d.get("posters", [])][:30]


# ---------- Trailer, streaming, liknande, personer, säsonger, släppdatum ----------

def _kind_path(kind: str) -> str:
    return "tv" if kind == "tv" else "movie"


def _card(h: dict, kind: str | None = None) -> dict:
    """En träff i kortformat (som search)."""
    date = h.get("release_date") or h.get("first_air_date") or ""
    return {"tmdb_id": h["id"], "type": kind or h.get("media_type") or "movie",
            "title": h.get("title") or h.get("name"), "year": int(date[:4]) if date[:4].isdigit() else None,
            "poster_path": h.get("poster_path"), "popularity": h.get("popularity") or 0}


async def trailer(tmdb_id: int, kind: str) -> dict | None:
    """Bästa trailern på YouTube: svensk om det finns, annars engelsk."""
    for language in (lang(), "en-US"):
        d = await _get(f"/{_kind_path(kind)}/{tmdb_id}/videos", language=language) or {}
        vids = [v for v in d.get("results", []) if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser")]
        vids.sort(key=lambda v: (v.get("type") != "Trailer", not v.get("official"), -(v.get("size") or 0)))
        if vids:
            return {"key": vids[0]["key"], "name": vids[0].get("name")}
    return None


async def watch_providers(tmdb_id: int, kind: str, country: str = "SE") -> dict:
    """Var filmen går att streama, hyra eller köpa digitalt i Sverige (data från JustWatch via TMDB)."""
    d = await _get(f"/{_kind_path(kind)}/{tmdb_id}/watch/providers", language=None) or {}
    r = (d.get("results") or {}).get(country) or {}
    pick = lambda key: [{"name": p["provider_name"], "logo": p.get("logo_path")}  # noqa: E731
                        for p in sorted(r.get(key) or [], key=lambda p: p.get("display_priority", 99))]
    return {"link": r.get("link"), "stream": pick("flatrate") + pick("free") + pick("ads"),
            "rent": pick("rent"), "buy": pick("buy")}


async def recommendations(tmdb_id: int, kind: str) -> list[dict]:
    d = await _get(f"/{_kind_path(kind)}/{tmdb_id}/recommendations") or {}
    out = [_card(h, _kind_path(kind)) for h in d.get("results", [])]
    if len(out) < 8:
        s = await _get(f"/{_kind_path(kind)}/{tmdb_id}/similar") or {}
        seen = {o["tmdb_id"] for o in out}
        out += [_card(h, _kind_path(kind)) for h in s.get("results", []) if h["id"] not in seen]
    return out[:30]


async def person(name: str) -> dict | None:
    """Skådespelare/regissör: vem det är och allt hen medverkat i."""
    d = await _get("/search/person", query=name, include_adult="false") or {}
    hits = d.get("results") or []
    if not hits:
        return None
    exact = [h for h in hits if (h.get("name") or "").lower() == name.lower()]
    p = (exact or hits)[0]
    credits = await _get(f"/person/{p['id']}/combined_credits") or {}
    works = {}
    for h in (credits.get("cast") or []) + [c for c in credits.get("crew") or [] if c.get("job") in ("Director", "Creator")]:
        if h.get("media_type") not in ("movie", "tv"):
            continue
        if h.get("media_type") == "tv" and h.get("character") and "self" in h["character"].lower():
            continue  # talkshowgäster m.m.
        c = _card(h)
        c["role"] = "Regi" if h.get("job") == "Director" else "Skapare" if h.get("job") == "Creator" else h.get("character")
        works.setdefault((c["type"], c["tmdb_id"]), c)
    lst = sorted(works.values(), key=lambda c: -(c["year"] or 0))
    return {"id": p["id"], "name": p.get("name"), "profile_path": p.get("profile_path"),
            "known_for": p.get("known_for_department"), "works": lst}


async def tv_seasons(tv_id: int) -> list[dict]:
    today = date.today().isoformat()
    d = await _get(f"/tv/{tv_id}") or {}
    out = []
    for s in d.get("seasons") or []:
        if not s.get("season_number"):
            continue  # säsong 0 = specialavsnitt
        aired = s.get("air_date") or ""
        out.append({"season": s["season_number"], "name": s.get("name"), "episodes": s.get("episode_count"),
                    "year": int(aired[:4]) if aired[:4].isdigit() else None, "poster_path": s.get("poster_path"),
                    "aired": bool(aired) and aired <= today})
    return out


async def physical_release(tmdb_id: int, country: str = "SE") -> str | None:
    """Första släppdatum på skiva (TMDB-typ 5 = fysisk utgåva). Svenskt datum i första hand."""
    d = await _get(f"/movie/{tmdb_id}/release_dates", language=None) or {}
    dates = {}
    for r in d.get("results") or []:
        for x in r.get("release_dates") or []:
            if x.get("type") == 5 and x.get("release_date"):
                dates.setdefault(r.get("iso_3166_1"), []).append(x["release_date"][:10])
    if dates.get(country):
        return min(dates[country])
    every = [x for v in dates.values() for x in v]
    return min(every) if every else None


# ---------- Streckkod på nätet ----------

JUNK = re.compile(
    r"\[.*?\]|\(.*?\)|\b(dvd|blu[\s-]?ray|4k|uhd|ultra hd|steelbook|import|region \w+|"
    r"widescreen|special edition|collector'?s edition|\d+[\s-]?disc|box ?set|nordic|svensk text)\b",
    re.I,
)


def clean_product_title(t: str) -> str:
    t = JUNK.sub(" ", t)
    t = re.sub(r"\b(s[äa]song|season)\s*\d+\b", " ", t, flags=re.I)
    t = re.sub(r"[-–:|/,+&]+\s*$", "", t.strip())
    return re.sub(r"\s+", " ", t).strip(" -–:|+")
