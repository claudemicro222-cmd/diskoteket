"""Musik: uppslag i MusicBrainz (gratis, ingen nyckel) och Discogs (valfri nyckel under Inställningar),
låtlistor och omslag. Omslagen sparas lokalt i appdata/posters precis som filmernas.

MusicBrainz tillåter ett anrop per sekund, så allt som går dit köas."""
import asyncio
import os
import re
import time
import unicodedata

import httpx

from . import covers, db, posters, repo, settings

MB = os.environ.get("MUSICBRAINZ_API", "https://musicbrainz.org/ws/2")
CAA = os.environ.get("COVERART_API", "https://coverartarchive.org")
DISCOGS = os.environ.get("DISCOGS_API", "https://api.discogs.com")
UA = "Diskoteket/4.0 ( https://github.com/claudemicro222-cmd/diskoteket )"

state = {"running": False, "done": 0, "total": 0, "failed": 0}
_mb_lock = asyncio.Lock()
_mb_last = 0.0


def mb_enabled():
    return settings.get_bool("lookup_musicbrainz")


def discogs_enabled():
    return bool(settings.get("discogs_token"))


# ---------- MusicBrainz ----------

async def _mb(path: str, params: dict) -> dict | None:
    global _mb_last
    async with _mb_lock:
        wait = 1.1 - (time.monotonic() - _mb_last)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA, "Accept": "application/json"}) as c:
                r = await c.get(f"{MB}{path}", params={**params, "fmt": "json"})
            _mb_last = time.monotonic()
            if r.status_code == 503:  # för många anrop – vänta och försök en gång till
                await asyncio.sleep(2)
                async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA}) as c:
                    r = await c.get(f"{MB}{path}", params={**params, "fmt": "json"})
                _mb_last = time.monotonic()
            return r.json() if r.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            _mb_last = time.monotonic()
            return None


def _credit(ac) -> str:
    return "".join((a.get("name") or (a.get("artist") or {}).get("name") or "") + (a.get("joinphrase") or "")
                   for a in ac or []).strip()


def _formats(media) -> str | None:
    """['CD', 'CD'] -> 'CD' · ['12\" Vinyl'] -> 'Vinyl' · blandat -> första."""
    names = [clean_format(m.get("format")) for m in media or [] if m.get("format")]
    return names[0] if names else None


def clean_format(text: str | None) -> str | None:
    t = (text or "").lower()
    if not t:
        return None
    if "vinyl" in t or "lp" in t.split() or '"' in t:
        return "Vinyl"
    if "sacd" in t:
        return "SACD"
    if "cassette" in t or "kassett" in t:
        return "Kassett"
    if "dvd" in t:
        return "DVD-Audio" if "audio" in t else "DVD"
    if "blu" in t:
        return "Blu-ray"
    if "cd" in t:
        return "CD"
    if "digital" in t or "file" in t:
        return "Digital"
    return text.strip()


def _year(date: str | None):
    m = re.match(r"(\d{4})", date or "")
    return int(m.group(1)) if m else None


def _mb_summary(r: dict) -> dict:
    li = (r.get("label-info") or [{}])[0] if r.get("label-info") else {}
    return {
        "source": "MusicBrainz", "mbid": r["id"], "discogs_id": None,
        "title": r.get("title"), "artist": _credit(r.get("artist-credit")),
        "year": _year(r.get("date")), "country": r.get("country"),
        "format": _formats(r.get("media")), "nr_discs": len(r.get("media") or []) or None,
        "tracks": r.get("track-count"), "barcode": r.get("barcode") or None,
        "label": (li.get("label") or {}).get("name"), "cat_no": li.get("catalog-number"),
        "cover": f"{CAA}/release/{r['id']}/front-250", "score": r.get("score", 0),
    }


async def mb_by_barcode(code: str) -> list[dict]:
    d = await _mb("/release", {"query": f"barcode:{code}", "limit": 8})
    return [_mb_summary(r) for r in (d or {}).get("releases", [])]


def _lucene(text: str) -> str:
    return re.sub(r'([+\-&|!(){}\[\]^"~*?:\\/])', r"\\\1", text)


async def mb_search(query: str, artist: str | None = None) -> list[dict]:
    if artist and artist.strip().lower() not in db.VARIOUS:
        q = f'release:"{_lucene(query)}" AND artist:"{_lucene(artist)}"'
    else:
        q = _lucene(query)
    d = await _mb("/release", {"query": q, "limit": 12})
    return [_mb_summary(r) for r in (d or {}).get("releases", [])]


async def mb_release(mbid: str) -> dict | None:
    r = await _mb(f"/release/{mbid}", {"inc": "recordings artist-credits labels genres release-groups"})
    if not r or "id" not in r:
        return None
    d = _mb_summary(r)
    rg = r.get("release-group") or {}
    d["year"] = _year(rg.get("first-release-date")) or d["year"]
    genres = sorted(rg.get("genres") or r.get("genres") or [], key=lambda g: -g.get("count", 0))
    d["genres"] = " | ".join(g["name"].title() for g in genres[:5]) or None
    tracklist, ms = [], 0
    for m in r.get("media") or []:
        for t in m.get("tracks") or []:
            ms += t.get("length") or 0
            tracklist.append({"disc": m.get("position") or 1, "pos": t.get("number") or str(t.get("position")),
                              "title": t.get("title"), "length": _mmss(t.get("length")),
                              "artist": _credit(t.get("artist-credit")) if t.get("artist-credit") else None})
    d["tracklist"] = tracklist
    d["tracks"] = len(tracklist) or d["tracks"]
    d["runtime"] = round(ms / 60000) or None
    # Saknar just den här utgåvan omslag tar vi albumets allmänna omslag (release group)
    d["cover"] = (f"{CAA}/release/{mbid}/front-500" if (r.get("cover-art-archive") or {}).get("front")
                  else f"{CAA}/release-group/{rg['id']}/front-500" if rg.get("id") else None)
    return d


def _mmss(ms):
    if not ms:
        return None
    s = round(ms / 1000)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


# ---------- Discogs ----------

async def _discogs(path: str, params: dict | None = None) -> dict | None:
    token = settings.get("discogs_token")
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA, "Authorization": f"Discogs token={token}"}) as c:
            r = await c.get(f"{DISCOGS}{path}", params=params or {})
        return r.json() if r.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None


def _dg_summary(r: dict) -> dict:
    artist, _, title = (r.get("title") or "").partition(" - ")
    return {
        "source": "Discogs", "mbid": None, "discogs_id": r.get("id"),
        "title": title or artist, "artist": re.sub(r"\s*\(\d+\)$", "", artist) if title else None,
        "year": _int(r.get("year")), "country": r.get("country"),
        "format": clean_format((r.get("format") or [None])[0]), "nr_discs": None, "tracks": None,
        "barcode": None, "label": re.sub(r"\s*\(\d+\)$", "", (r.get("label") or [""])[0]) or None,
        "cat_no": r.get("catno"), "cover": r.get("thumb") or r.get("cover_image"), "score": 0,
    }


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


async def discogs_search(barcode: str | None = None, query: str | None = None, artist: str | None = None) -> list[dict]:
    params = {"type": "release", "per_page": 10}
    if barcode:
        params["barcode"] = barcode
    else:
        params["release_title"] = query
        if artist and artist.strip().lower() not in db.VARIOUS:
            params["artist"] = artist
    d = await _discogs("/database/search", params)
    return [_dg_summary(r) for r in (d or {}).get("results", [])]


async def discogs_release(release_id: int) -> dict | None:
    r = await _discogs(f"/releases/{int(release_id)}")
    if not r or "id" not in r:
        return None
    artist = ""
    for a in r.get("artists") or []:  # t.ex. [{"name": "Roxette (2)", "join": "&"}, …]
        join = (a.get("join") or "").strip()
        artist += re.sub(r"\s*\(\d+\)$", "", a.get("name", "")) + (", " if join == "," else f" {join} " if join else "")
    artist = artist.strip(" ,")
    fmts = r.get("formats") or [{}]
    tracklist, secs = [], 0
    for t in r.get("tracklist") or []:
        if t.get("type_", "track") != "track":
            continue
        pos = t.get("position") or ""
        m = re.match(r"^(?:CD)?(\d+)-(\d+)$", pos)
        tracklist.append({"disc": int(m.group(1)) if m else 1, "pos": m.group(2) if m else pos,
                          "title": t.get("title"), "length": t.get("duration") or None,
                          "artist": ", ".join(a.get("name", "") for a in t.get("artists") or []) or None})
        mm = re.match(r"^(\d+):(\d{2})$", t.get("duration") or "")
        secs += int(mm.group(1)) * 60 + int(mm.group(2)) if mm else 0
    labels = r.get("labels") or [{}]
    images = r.get("images") or []
    primary = next((i for i in images if i.get("type") == "primary"), images[0] if images else {})
    return {
        "source": "Discogs", "mbid": None, "discogs_id": r["id"], "title": r.get("title"), "artist": artist or None,
        "year": _int(r.get("year")) or None, "country": r.get("country"),
        "format": clean_format(fmts[0].get("name")), "nr_discs": _int(fmts[0].get("qty")),
        "tracks": len(tracklist) or None, "tracklist": tracklist, "runtime": round(secs / 60) or None,
        "label": re.sub(r"\s*\(\d+\)$", "", labels[0].get("name") or "") or None, "cat_no": labels[0].get("catno"),
        "genres": " | ".join((r.get("genres") or []) + (r.get("styles") or [])[:3]) or None,
        "barcode": next((re.sub(r"\D", "", i.get("value", "")) for i in r.get("identifiers") or []
                         if i.get("type") == "Barcode"), None),
        "cover": primary.get("uri") or primary.get("resource_url"),
    }


# ---------- Uppslag ----------

def norm(text: str | None) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


async def lookup(code: str) -> dict:
    """Streckkod -> album. Svar: {match, candidates, product_title, tried}."""
    out = {"match": None, "candidates": [], "product_title": None, "tried": []}
    if mb_enabled():
        out["tried"].append("MusicBrainz")
        found = await mb_by_barcode(code)
        if found:
            out["match"], out["candidates"] = found[0], found
            return out
    if discogs_enabled():
        out["tried"].append("Discogs")
        found = await discogs_search(barcode=code)
        if found:
            out["match"], out["candidates"] = found[0], found
            return out
    if settings.get_bool("lookup_upcitemdb"):
        from .barcodes import upcitemdb
        out["tried"].append("UPCitemdb")
        title = await upcitemdb(code)
        if title:
            out["product_title"] = title
            out["candidates"] = await search(re.sub(r"\(.*?\)|\[.*?\]|\bCD\b", "", title).strip())
    return out


async def search(query: str, artist: str | None = None) -> list[dict]:
    """Titel (och ev. artist) -> förslag från MusicBrainz och Discogs."""
    if not query.strip():
        return []
    m = re.match(r"^(.+?)\s+[-–]\s+(.+)$", query.strip())  # "Artist - Album"
    if m and not artist:
        artist, query = m.group(1), m.group(2)
    res = []
    if mb_enabled():
        res += await mb_search(query, artist)
    if discogs_enabled() and len(res) < 5:
        res += await discogs_search(query=query, artist=artist)
    return res


async def details(source: str, ref) -> dict | None:
    if source in ("mb", "MusicBrainz"):
        return await mb_release(str(ref))
    if source in ("discogs", "Discogs"):
        return await discogs_release(int(ref))
    return None


# ---------- Spara ----------

async def save_cover(item_id: int, url: str | None, force=False) -> bool:
    """Hämtar omslaget och sparar det lokalt (inte om du valt ett eget omslag)."""
    it = repo.get(item_id)
    if not url or not it or ("poster_path" in it["locked"] and not force):
        return False
    try:
        data = await covers.download(url)
        jpeg = await asyncio.to_thread(covers.to_jpeg, data)
    except covers.CoverError:
        return False
    os.makedirs(posters.POSTER_DIR, exist_ok=True)
    name = f"music-{item_id}-{int(time.time())}.jpg"
    with open(os.path.join(posters.POSTER_DIR, name), "wb") as f:
        f.write(jpeg)
    prev = (it.get("poster_path") or "").lstrip("/")
    repo.update(item_id, {"poster_path": "/" + name}, lock=False)
    if prev.startswith(f"music-{item_id}-") and prev != name:
        try:
            os.remove(os.path.join(posters.POSTER_DIR, prev))
        except OSError:
            pass
    return True


FILL = ("title", "artist", "year", "label", "cat_no", "format", "nr_discs", "tracks", "runtime", "genres", "country")


def changes_from(d: dict, it: dict | None, reset=False) -> dict:
    """Vad som ska sparas från ett uppslag. Tomma fält fylls i; fält du ändrat själv rörs aldrig.
    Med reset skrivs även titel, artist m.m. över (utom låsta fält)."""
    ch = {"mbid": d.get("mbid"), "discogs_id": d.get("discogs_id"), "enriched": 1}
    if d.get("tracklist"):
        ch["tracklist"] = d["tracklist"]
    for k in FILL:
        v = d.get(k)
        if v in (None, "", 0):
            continue
        if it is None or reset or it.get(k) in (None, "", 0):
            ch[k] = v
    if it:
        ch = {k: v for k, v in ch.items() if k not in it["locked"]}
    return ch


async def refresh_item(item_id: int, reset=False, source=None, ref=None, covers_later: list | None = None) -> dict | None:
    """Hämta låtlista, omslag m.m. på nytt. source/ref väljer ett annat album ('Fel album?').
    covers_later: lägg omslaget i en lista i stället för att vänta på det (snabbare vid många album)."""
    it = repo.get(item_id)
    if not it:
        return None
    d = None
    if source and ref:
        d = await details(source, ref)
    elif it.get("mbid"):
        d = await mb_release(it["mbid"])
    elif it.get("discogs_id"):
        d = await discogs_release(it["discogs_id"])
    else:
        hit = await find_match(it)
        d = hit and await details(hit["source"], hit["mbid"] or hit["discogs_id"])
    if not d:
        return None
    if source:  # nytt album valt: glöm det gamla
        repo.update(item_id, {"mbid": None, "discogs_id": None, "tracklist": []}, lock=False)
        reset = True
    repo.update(item_id, changes_from(d, it, reset), lock=False)
    if d.get("cover") and (reset or source or not it.get("poster_path")):
        if covers_later is not None:
            covers_later.append((item_id, d["cover"]))
        else:
            await save_cover(item_id, d["cover"])
    return repo.get(item_id)


async def find_match(it: dict) -> dict | None:
    """Hitta albumet för en importerad post: streckkod först, annars titel och artist."""
    want = norm(it["title"])
    if it.get("barcode"):
        found = await mb_by_barcode(it["barcode"]) if mb_enabled() else []
        if not found and discogs_enabled():
            found = await discogs_search(barcode=it["barcode"])
        if found:
            # samma streckkod kan finnas på flera utgåvor – ta den vars titel stämmer bäst
            return next((f for f in found if norm(f["title"]) == want), found[0])
    found = await search(it["title"], it.get("artist"))
    for f in found:
        if norm(f["title"]) == want and (not it.get("artist") or repo.is_various(it["artist"])
                                         or norm(f["artist"]) == norm(it["artist"])):
            return f
    return None


async def add(source: str, ref, extra: dict) -> int:
    """Lägg till ett album från MusicBrainz/Discogs. extra: library_id, barcode, format, location, wish."""
    d = await details(source, ref)
    if not d:
        raise LookupError("Hittade inte albumet")
    item = {k: v for k, v in changes_from(d, None).items() if k != "enriched"}
    item.update(kind="music", library_id=extra["library_id"], added_date=extra["added_date"],
                barcode=extra.get("barcode") or d.get("barcode"), location=extra.get("location"),
                collection_status="On Wish List" if extra.get("wish") else "In Collection")
    if extra.get("format"):
        item["format"] = extra["format"]
    with db.connect() as con:
        item_id, _ = db.upsert(con, item)
        con.execute("UPDATE items SET enriched=1 WHERE id=?", (item_id,))
    if d.get("cover"):
        await save_cover(item_id, d["cover"])
    return item_id


# ---------- Bakgrundsjobb efter import ----------

async def enrich_all(retry_failed=False):
    """Låtlistor och omslag för importerade album. Ett i taget (MusicBrainz: ett anrop per sekund)."""
    if state["running"] or not (mb_enabled() or discogs_enabled()):
        return
    with db.connect() as con:
        if retry_failed:
            con.execute("UPDATE items SET enriched=0 WHERE kind='music' AND enriched=2")
        ids = [r[0] for r in con.execute("SELECT id FROM items WHERE kind='music' AND enriched=0 ORDER BY id")]
    if not ids:
        return
    state.update(running=True, done=0, total=len(ids), failed=0)
    sem = asyncio.Semaphore(4)  # omslagen hämtas parallellt medan nästa album slås upp
    tasks = []

    async def cover(item_id, url):
        async with sem:
            await save_cover(item_id, url)

    try:
        for item_id in ids:
            try:
                it = repo.get(item_id)
                if it and it["enriched"] == 0:
                    later = []
                    if not await refresh_item(item_id, covers_later=later):
                        with db.connect() as con:
                            con.execute("UPDATE items SET enriched=2 WHERE id=?", (item_id,))
                        state["failed"] += 1
                    tasks += [asyncio.create_task(cover(i, u)) for i, u in later]
            except Exception as e:  # ett album som strular ska inte stoppa resten
                print("Musikuppslag:", item_id, e)
                state["failed"] += 1
            state["done"] += 1
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        state["running"] = False
