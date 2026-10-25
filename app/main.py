"""Diskoteket – egen film-, serie- och musiksamling. Startas med: uvicorn app.main:app"""
import asyncio
import json
import os
import re
import time
from contextlib import asynccontextmanager
from datetime import date, datetime

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import auth, barcodes, clz_import, covers, db, enrich, mediaservers, music, posters, repo, settings, tmdb

STATIC = os.path.join(os.path.dirname(__file__), "static")
VERSION = "4.0"
digital_state = {"last": None, "result": None}
_tasks = set()


def background(coro):
    """Starta ett jobb i bakgrunden (och håll en referens så det inte städas bort)."""
    t = asyncio.create_task(coro)
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)
    return t


# ---------- Hjälpfunktioner ----------

def lib_of(request: Request):
    """?lib=3 → samling 3, ?lib=all eller tomt → alla samlingar."""
    v = request.query_params.get("lib", "")
    return int(v) if v.isdigit() else None


def q(request: Request, name, default=""):
    return request.query_params.get(name, default)


def qbool(request: Request, name):
    return q(request, name).lower() in ("1", "true", "yes", "on")


async def body(request: Request) -> dict:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def need_tmdb():
    if not tmdb.enabled():
        raise HTTPException(400, "TMDB-nyckel saknas – fyll i den under Meny → Inställningar")


def item_or_404(item_id):
    item = repo.get(item_id)
    if not item:
        raise HTTPException(404, "Finns inte")
    return item


def default_lib():
    return repo.libraries()[0]["id"]


# ---------- Samlingar ----------

async def libraries_list(request):
    return JSONResponse(repo.libraries())


async def library_create(request):
    name = (await body(request)).get("name", "").strip()
    if not name:
        raise HTTPException(400, "Ange ett namn")
    return JSONResponse({"id": repo.create_library(name), "libraries": repo.libraries()})


async def library_rename(request):
    lib_id = request.path_params["lib_id"]
    name = (await body(request)).get("name", "").strip()
    if not name or not repo.library(lib_id):
        raise HTTPException(400, "Ogiltigt namn eller samling")
    repo.rename_library(lib_id, name)
    return JSONResponse(repo.libraries())


async def library_delete(request):
    lib_id = request.path_params["lib_id"]
    lib = repo.library(lib_id)
    if not lib:
        raise HTTPException(404, "Samlingen finns inte")
    if len(repo.libraries()) <= 1:
        raise HTTPException(400, "Det måste finnas minst en samling")
    if (await body(request)).get("confirm", "").strip() != lib["name"]:
        raise HTTPException(400, "Namnet stämmer inte – inget togs bort")
    safe = re.sub(r"[^A-Za-z0-9]+", "-", lib["name"]).strip("-")[:30] or "samling"
    backup = await asyncio.to_thread(repo.backup_now, f"fore-borttagning-{safe}")
    n = repo.delete_library(lib_id)
    return JSONResponse({"deleted": n, "backup": backup, "libraries": repo.libraries()})


# ---------- Titlar ----------

async def items_list(request):
    p = request.query_params
    coll = p.get("collection_id", "")
    return JSONResponse(repo.list_items(
        lib=lib_of(request), q=p.get("q", ""), kind=p.get("kind", ""), status=p.get("status", "owned"),
        format=p.get("format", ""), genre=p.get("genre", ""), location=p.get("location", ""),
        watched=p.get("watched", ""), digital=p.get("digital", ""), sort=p.get("sort", "title"),
        missing_poster=qbool(request, "missing_poster"), collection_id=int(coll) if coll.isdigit() else None,
        field=p.get("field", "title")))


async def facets(request):
    return JSONResponse(repo.facets(lib_of(request), q(request, "kind")))


async def item_get(request):
    return JSONResponse(item_or_404(request.path_params["item_id"]))


def clean_changes(changes: dict) -> dict:
    for k in ("year", "season", "library_id", "runtime", "tracks", "nr_discs"):
        if k in changes:
            changes[k] = int(changes[k]) if str(changes[k] or "").strip().isdigit() else None
    for k in ("my_rating", "purchase_price"):
        if k in changes:
            try:
                changes[k] = float(str(changes[k]).replace(",", ".")) if changes[k] not in (None, "") else None
            except ValueError:
                changes[k] = None
    if "watched" in changes:
        changes["watched"] = 1 if changes["watched"] in (1, True, "1", "true") else 0
    return {k: (v.strip() or None) if isinstance(v, str) else v for k, v in changes.items()}


async def item_patch(request):
    item_id = request.path_params["item_id"]
    item_or_404(item_id)
    changes = clean_changes(await body(request))
    if "library_id" in changes and not repo.library(changes["library_id"] or 0):
        raise HTTPException(400, "Okänd samling")
    return JSONResponse(repo.update(item_id, changes))


async def item_delete(request):
    with db.connect() as con:
        con.execute("DELETE FROM items WHERE id=?", (request.path_params["item_id"],))
    return JSONResponse({"ok": True})


async def item_add(request):
    need_tmdb()
    b = await body(request)
    lib = int(b.get("library_id") or default_lib())
    media = "tv" if b.get("type") == "tv" else "movie"
    season = int(b["season"]) if str(b.get("season") or "").isdigit() else None
    item = await tmdb.details(int(b["tmdb_id"]), media)
    if not b.get("force"):
        existing = [e for e in repo.find_existing(lib, tmdb_id=item["tmdb_id"], imdb_id=item["imdb_id"])
                    if e["kind"] == item["kind"] and (not season or e["season"] == season)]
        if existing:
            return JSONResponse({"exists": existing}, status_code=409)
    item.update(library_id=lib, barcode=(b.get("barcode") or None), format=b.get("format") or None,
                location=(b.get("location") or None), added_date=date.today().isoformat(),
                collection_status="On Wish List" if b.get("wish") else "In Collection")
    if item["kind"] == "tv":
        item["series_name"] = item["title"]
        if season:
            item["season"] = season
            item["title"] = f"{item['title']}: Säsong {season}"
            s = await tmdb.season(item["tmdb_id"], season)
            if s:
                item["poster_path"] = s["poster_path"] or item["poster_path"]
                item["plot"] = s["overview"] or item["plot"]
                item["year"] = s["year"] or item["year"]
    with db.connect() as con:
        item_id, _ = db.upsert(con, item)
        con.execute("UPDATE items SET enriched=1, coll_checked=1 WHERE id=?", (item_id,))
    if item.get("barcode"):
        barcodes.learn(item["barcode"], item["tmdb_id"], item["kind"], item.get("series_name") or item["title"],
                       item.get("year"), item.get("format"))
    if item.get("poster_path"):
        background(posters.fetch(item["poster_path"]))
    return JSONResponse(repo.get(item_id))


async def item_rematch(request):
    """Koppla posten till en annan TMDB-titel (när den automatiska matchningen blev fel).
    För musik: ett annat album från MusicBrainz/Discogs ({source, id})."""
    item_id = request.path_params["item_id"]
    old = item_or_404(item_id)
    b = await body(request)
    if old["kind"] == "music":
        item = await music.refresh_item(item_id, source=b.get("source"), ref=b.get("id"))
        if not item:
            raise HTTPException(404, "Hittade inte albumet")
        return JSONResponse(item)
    need_tmdb()
    media = "tv" if b.get("type") == "tv" else "movie"
    changes = {"tmdb_id": int(b["tmdb_id"]), "enriched": 1, "kind": media}
    if media == "tv" and not old.get("series_name"):
        changes["series_name"] = (await tmdb.details(int(b["tmdb_id"]), "tv"))["title"]
    repo.update(item_id, changes, lock=False, unlock={"poster_path", "plot"})
    item = await enrich.refresh_item(item_id)
    if item and item.get("barcode"):  # rätta även den inlärda streckkoden
        barcodes.learn(item["barcode"], item["tmdb_id"], item["kind"], item.get("series_name") or item["title"],
                       item.get("year"), item.get("format"))
    return JSONResponse(item)


async def item_refresh(request):
    item_id = request.path_params["item_id"]
    it = item_or_404(item_id)
    reset = bool((await body(request)).get("reset"))
    if it["kind"] == "music":
        item = await music.refresh_item(item_id, reset=reset)
        if not item:
            raise HTTPException(404, "Hittade inte albumet i MusicBrainz/Discogs – använd 'Fel album?' och välj rätt")
        return JSONResponse(item)
    need_tmdb()
    item = await enrich.refresh_item(item_id, reset=reset)
    if not item:
        raise HTTPException(404, "Hittade ingen matchning på TMDB – använd 'Fel film?' och välj rätt")
    return JSONResponse(item)


async def item_posters(request):
    need_tmdb()
    it = item_or_404(request.path_params["item_id"])
    if not it.get("tmdb_id"):
        return JSONResponse([])
    return JSONResponse(await tmdb.posters(it["tmdb_id"], it["kind"], it.get("season")))


async def item_cover(request):
    """Eget omslag: fil/foto (multipart) eller bildadress (JSON {url})."""
    item_id = request.path_params["item_id"]
    item_or_404(item_id)
    try:
        if request.headers.get("content-type", "").startswith("multipart/"):
            form = await request.form()
            upload = form.get("file")
            if not upload or not hasattr(upload, "read"):
                raise HTTPException(400, "Ingen bild vald")
            data = await upload.read()
        else:
            data = await covers.download((await body(request)).get("url", "").strip())
        item = await asyncio.to_thread(covers.save_for_item, item_id, data)
    except covers.CoverError as e:
        raise HTTPException(400, str(e))
    return JSONResponse(item)


async def covers_import(request):
    """Massimport: många bilder eller en zip, namngivna efter streckkod eller titel."""
    form = await request.form()
    uploads = []
    for f in form.getlist("files"):
        if hasattr(f, "read"):
            uploads.append((f.filename or "bild", await f.read()))
    if not uploads:
        raise HTTPException(400, "Inga filer valda")
    lib = form.get("lib", "")
    only_missing = str(form.get("only_missing", "1")) in ("1", "true", "on")
    result = await asyncio.to_thread(covers.bulk_import, uploads, int(lib) if str(lib).isdigit() else None, only_missing)
    return JSONResponse(result)


# ---------- Streckkod & sök ----------

async def barcode(request):
    """Finns streckkoden redan i samlingen? Annars: försök lista ut titeln via nätet och sök på TMDB."""
    code = re.sub(r"\D", "", request.path_params["code"])
    existing = repo.find_existing(lib_of(request), barcode=code)
    if existing or qbool(request, "local"):
        return JSONResponse({"existing": existing})
    return JSONResponse({"existing": [], **(await barcodes.lookup(code))})


# ---------- Musik ----------

async def music_barcode(request):
    code = re.sub(r"\D", "", request.path_params["code"])
    existing = repo.find_existing(lib_of(request), barcode=code)
    if existing:
        return JSONResponse({"existing": existing})
    return JSONResponse({"existing": [], **(await music.lookup(code))})


async def music_search(request):
    if not (music.mb_enabled() or music.discogs_enabled()):
        raise HTTPException(400, "Slå på MusicBrainz eller fyll i en Discogs-nyckel under Meny → Inställningar")
    return JSONResponse(await music.search(q(request, "q"), q(request, "artist") or None))


async def music_add(request):
    b = await body(request)
    lib = int(b.get("library_id") or default_lib())
    source, ref = b.get("source"), b.get("id")
    if not source or not ref:
        raise HTTPException(400, "Välj ett album")
    if not b.get("force"):
        existing = repo.find_music(lib, mbid=ref if source in ("mb", "MusicBrainz") else None,
                                   discogs_id=ref if source in ("discogs", "Discogs") else None,
                                   barcode=b.get("barcode"))
        if existing:
            return JSONResponse({"exists": existing}, status_code=409)
    try:
        item_id = await music.add(source, ref, {
            "library_id": lib, "barcode": re.sub(r"\D", "", b.get("barcode") or "") or None,
            "format": b.get("format") or None, "location": (b.get("location") or "").strip() or None,
            "wish": bool(b.get("wish")), "added_date": date.today().isoformat()})
    except LookupError as e:
        raise HTTPException(404, str(e))
    return JSONResponse(repo.get(item_id))


async def music_manual(request):
    """Album som inte finns i någon databas: skriv in det själv."""
    b = clean_changes(await body(request))
    if not b.get("title"):
        raise HTTPException(400, "Ange en titel")
    item = {k: b.get(k) for k in ("title", "artist", "year", "format", "label", "cat_no", "location", "nr_discs",
                                  "tracks", "genres", "notes")}
    item.update(kind="music", library_id=int(b.get("library_id") or default_lib()),
                barcode=re.sub(r"\D", "", b.get("barcode") or "") or None, added_date=date.today().isoformat(),
                collection_status="On Wish List" if b.get("wish") else "In Collection")
    with db.connect() as con:
        item_id, _ = db.upsert(con, item)
        con.execute("UPDATE items SET enriched=2 WHERE id=?", (item_id,))
    return JSONResponse(repo.get(item_id))


async def search(request):
    need_tmdb()
    query, year = q(request, "q").strip(), q(request, "year")
    m = re.match(r"^(.*?)[\s,]*\(?((?:19|20)\d{2})\)?$", query)  # "Alien 1979" / "Alien (1979)"
    if not year and m and m.group(1).strip():
        query, year = m.group(1).strip(), m.group(2)
    return JSONResponse(await tmdb.search(query, int(year) if str(year).isdigit() else None))


# ---------- Import & metadata ----------

async def import_clz(request):
    form = await request.form()
    upload = form.get("file")
    if not upload or not hasattr(upload, "read"):
        raise HTTPException(400, "Ingen fil vald")
    new_name = (form.get("new_library") or "").strip()
    lib = repo.create_library(new_name) if new_name else int(form.get("library_id") or default_lib())
    result = clz_import.import_csv(await upload.read(), lib)
    result["library_id"] = lib
    cover_urls = result.pop("cover_urls", [])
    result["cover_urls"] = len(cover_urls)
    if cover_urls:
        background(fetch_clz_covers(cover_urls))
    background(music.enrich_all() if result["kind"] == "music" else enrich.run())
    return JSONResponse(result)


async def fetch_clz_covers(pairs):
    """Bildlänkar från CLZ-exporten (om sådana finns) blir egna omslag."""
    for item_id, url in pairs:
        it = repo.get(item_id)
        if not it or "poster_path" in it["locked"]:
            continue  # redan ett eget omslag
        try:
            data = await covers.download(url)
            await asyncio.to_thread(covers.save_for_item, item_id, data)
        except covers.CoverError:
            pass


async def enrich_start(request):
    if q(request, "kind") == "music":
        background(music.enrich_all(retry_failed=qbool(request, "retry_failed")))
        return JSONResponse(music.state)
    need_tmdb()
    if qbool(request, "retry_failed"):
        with db.connect() as con:
            con.execute("UPDATE items SET enriched=0 WHERE enriched=2 AND kind != 'music'")
    background(enrich.run())
    return JSONResponse(enrich.state)


async def refresh_library(request):
    need_tmdb()
    if enrich.state["running"]:
        raise HTTPException(409, "En hämtning pågår redan – vänta tills den är klar")
    b = await body(request)
    lib = int(b["lib"]) if str(b.get("lib") or "").isdigit() else None
    background(enrich.refresh_library(lib, bool(b.get("reset"))))
    await asyncio.sleep(0.2)
    return JSONResponse(enrich.state)


async def status(request):
    lib = lib_of(request)
    s, a = repo._lib(lib)
    with db.connect() as con:
        counts = dict(con.execute(
            f"SELECT COUNT(*) AS total, SUM(kind='movie') AS movies, SUM(kind='tv') AS tv, SUM(kind='music') AS music, "
            f"SUM(enriched=0) AS waiting, SUM(enriched=2) AS not_found, "
            f"SUM((poster_path IS NULL OR poster_path='') AND kind != 'music') AS no_poster, "
            f"SUM((poster_path IS NULL OR poster_path='') AND kind = 'music') AS music_no_cover, "
            f"SUM(kind='music' AND enriched=2) AS music_not_found, SUM({repo.WISH}) AS wish "
            f"FROM items WHERE 1=1{s}", a).fetchone())
        digital_count = dict(con.execute("SELECT source, COUNT(*) FROM digital GROUP BY source").fetchall())
    return JSONResponse({
        "version": VERSION, "tmdb": tmdb.enabled(), "counts": counts, "enrich": enrich.state, "music": music.state,
        "music_lookup": music.mb_enabled() or music.discogs_enabled(), "auth": auth.enabled(),
        "posters": {**posters.state, **posters.disk_usage(), "local": settings.get_bool("local_posters")},
        "digital": {"configured": mediaservers.configured(), "counts": digital_count, **digital_state},
        "backups": repo.list_backups()[:8], "backup_hours": settings.get_float("backup_hours"),
        "config_dir": os.path.abspath(db.CONFIG_DIR)})


# ---------- Statistik, slump, filmserier ----------

async def stats(request):
    return JSONResponse(repo.stats(lib_of(request)))


async def random_pick(request):
    mr = q(request, "max_runtime")
    pick = repo.random_pick(lib_of(request), q(request, "kind", "movie"), qbool(request, "unwatched"),
                            int(mr) if mr.isdigit() else None, q(request, "genre"), q(request, "format"))
    if not pick:
        raise HTTPException(404, "Inget matchade filtren")
    return JSONResponse(pick)


async def collections(request):
    return JSONResponse(repo.collections(lib_of(request)))


async def collection(request):
    need_tmdb()
    c = await tmdb.collection(request.path_params["coll_id"])
    if not c:
        raise HTTPException(404, "Okänd filmserie")
    lib = lib_of(request)
    for p in c["parts"]:
        mine = [r for r in repo.find_existing(lib, tmdb_id=p["tmdb_id"]) if r["kind"] == "movie"]
        p["owned"] = [r for r in mine if "wish" not in (r["collection_status"] or "").lower()]
        p["wished"] = any("wish" in (r["collection_status"] or "").lower() for r in mine)
    return JSONResponse(c)


# ---------- Plex / Jellyfin ----------

async def digital_sync(request):
    if not mediaservers.configured():
        raise HTTPException(400, "Ingen Plex- eller Jellyfin-server inställd – se Meny → Inställningar")
    digital_state.update(result=await mediaservers.sync(), last=date.today().isoformat())
    return JSONResponse(digital_state)


async def digital_only(request):
    return JSONResponse(repo.digital_only(lib_of(request)))


# ---------- Home Assistant ----------

async def home_assistant(request):
    """Sammanfattning för en REST-sensor i Home Assistant."""
    return JSONResponse(repo.ha_summary())


# ---------- Säkerhetskopior ----------

async def backup(request):
    name = await asyncio.to_thread(repo.backup_now)
    return JSONResponse({"name": name, "backups": repo.list_backups()})


async def backup_download(request):
    name = request.path_params["name"]
    if not re.fullmatch(r"[A-Za-z0-9_\-]+\.db", name):
        raise HTTPException(400, "Ogiltigt namn")
    path = os.path.join(repo.BACKUP_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(404, "Finns inte")
    return FileResponse(path, filename=name, media_type="application/octet-stream")


async def backup_restore(request):
    """Återställ: en av appens egna kopior (JSON {name}) eller en uppladdad .db-fil (multipart)."""
    if enrich.state["running"] or music.state["running"] or posters.state["running"]:
        raise HTTPException(409, "En hämtning pågår i bakgrunden – vänta tills den är klar och försök igen")
    try:
        if request.headers.get("content-type", "").startswith("multipart/"):
            form = await request.form()
            upload = form.get("file")
            if not upload or not hasattr(upload, "read"):
                raise HTTPException(400, "Ingen fil vald")
            result = await asyncio.to_thread(repo.restore_backup, data=await upload.read())
        else:
            result = await asyncio.to_thread(repo.restore_backup, name=(await body(request)).get("name"))
    except repo.RestoreError as e:
        raise HTTPException(400, str(e))
    background(enrich.run())
    background(music.enrich_all())
    return JSONResponse({**result, "libraries": repo.libraries()})


# ---------- Export ----------

async def export(request):
    lib = lib_of(request)
    stamp = datetime.now().strftime("%Y%m%d")
    if q(request, "format") == "json":
        data = json.dumps({"exported": datetime.now().isoformat(timespec="seconds"), "version": VERSION,
                           "libraries": repo.libraries(), "items": repo.export_rows(lib)}, ensure_ascii=False, indent=1)
        return Response(data, media_type="application/json", headers={
            "Content-Disposition": f'attachment; filename="diskoteket-{stamp}.json"'})
    return Response(repo.export_csv(lib), media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="diskoteket-{stamp}.csv"'})


# ---------- Inloggning ----------

def _cookie(response, request, value, max_age):
    response.set_cookie(auth.COOKIE, value, max_age=max_age, httponly=True, samesite="lax",
                        secure=request.url.scheme == "https")


async def login(request):
    b = await body(request)
    if not auth.enabled():
        return JSONResponse({"ok": True})
    if not auth.check_password(b.get("password", "")):
        await asyncio.sleep(1)  # bromsa den som gissar
        raise HTTPException(401, "Fel lösenord")
    r = JSONResponse({"ok": True})
    _cookie(r, request, auth.make_session(), auth.MAX_AGE)
    return r


async def logout(request):
    r = JSONResponse({"ok": True})
    r.delete_cookie(auth.COOKIE)
    return r


async def auth_get(request):
    return JSONResponse({"enabled": auth.enabled(), "api_key": auth.api_key() if auth.enabled() else None})


async def auth_put(request):
    """Sätt/byt lösenord ({password}) eller stäng av inloggningen ({disable: true})."""
    b = await body(request)
    if b.get("disable"):
        auth.clear_password()
        return JSONResponse({"enabled": False, "api_key": None})
    try:
        auth.set_password(b.get("password") or "")
    except ValueError as e:
        raise HTTPException(400, str(e))
    r = JSONResponse({"enabled": True, "api_key": auth.api_key()})
    _cookie(r, request, auth.make_session(), auth.MAX_AGE)  # du som bytte lösenord förblir inloggad
    return r


async def auth_new_key(request):
    return JSONResponse({"enabled": auth.enabled(), "api_key": auth.new_api_key()})


async def health(request):
    return JSONResponse({"ok": True, "version": VERSION})


PUBLIC = ("/api/login", "/api/health", "/static/", "/manifest.webmanifest", "/poster/", "/favicon")
KEY_PATHS = ("/api/ha",)  # det API-nyckeln (Home Assistant) får läsa


class AuthMiddleware:
    """Släpper bara igenom inloggade när ett lösenord är satt. Utan lösenord: allt öppet, som förut."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not auth.enabled():
            return await self.app(scope, receive, send)
        request = Request(scope)
        path = scope["path"]
        if path.startswith(PUBLIC) or auth.valid_session(request.cookies.get(auth.COOKIE)):
            return await self.app(scope, receive, send)
        key = request.headers.get("x-api-key") or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if path.startswith(KEY_PATHS) and request.method == "GET" and auth.valid_api_key(key):
            return await self.app(scope, receive, send)
        if path.startswith("/api/"):
            response = JSONResponse({"detail": "Du behöver logga in", "login": True}, status_code=401)
        else:
            response = FileResponse(os.path.join(STATIC, "login.html"), headers={"Cache-Control": "no-cache"})
        await response(scope, receive, send)


# ---------- Inställningar ----------

async def settings_get(request):
    return JSONResponse(settings.public())


async def settings_put(request):
    settings.save(await body(request))
    return JSONResponse(settings.public())


async def settings_test(request):
    what = request.path_params["what"]
    if what == "tmdb":
        ok, msg = await tmdb.test()
        if ok:
            background(enrich.run())
        return JSONResponse({"ok": ok, "message": msg})
    if what in ("plex", "jellyfin"):
        if what not in mediaservers.configured():
            return JSONResponse({"ok": False, "message": "Adress eller nyckel saknas"})
        r = await mediaservers.sync(only=what)
        v = r.get(what)
        digital_state.update(result=r, last=date.today().isoformat())
        ok = isinstance(v, int)
        return JSONResponse({"ok": ok, "message": f"Hittade {v} titlar" if ok else str(v)})
    if what in ("discogs", "musicbrainz"):
        if what == "discogs" and not music.discogs_enabled():
            return JSONResponse({"ok": False, "message": "Nyckel saknas"})
        found = (await music.discogs_search(barcode="5708992012166") if what == "discogs"
                 else await music.mb_by_barcode("5708992012166"))  # Ace of Base – The Bridge
        if found:
            background(music.enrich_all())
            return JSONResponse({"ok": True, "message": f"Fungerar ({found[0]['artist']} – {found[0]['title']})"})
        return JSONResponse({"ok": False, "message": "Fick inget svar – kontrollera nyckeln"})
    raise HTTPException(404, "Okänt test")


# ---------- Omslag ----------

async def poster(request):
    """Lokalt sparat omslag om det finns (laddas ner första gången), annars direkt från TMDB."""
    path = request.path_params["name"]
    local = await posters.fetch(path)
    if local:
        return FileResponse(local, headers={"Cache-Control": "public, max-age=2592000, immutable"})
    if not posters.local_path(path) or not posters.is_tmdb(path):
        raise HTTPException(404, "Omslaget finns inte")
    return RedirectResponse(posters.remote_url(path))


# ---------- Bakgrundsjobb ----------

async def housekeeping():
    """Körs i bakgrunden: säkerhetskopia och synk mot Plex/Jellyfin med jämna mellanrum."""
    last_sync = 0.0
    await asyncio.sleep(5)
    while True:
        try:
            now = time.time()
            hours = settings.get_float("backup_hours")
            backups = [b for b in repo.list_backups() if "fore-borttagning" not in b["name"]]
            last_backup = os.path.getmtime(os.path.join(repo.BACKUP_DIR, backups[0]["name"])) if backups else 0
            if hours > 0 and now - last_backup > hours * 3600:
                await asyncio.to_thread(repo.backup_now)
            sync_hours = settings.get_float("digital_sync_hours")
            if mediaservers.configured() and sync_hours > 0 and now - last_sync > sync_hours * 3600:
                digital_state.update(result=await mediaservers.sync(), last=date.today().isoformat())
                last_sync = now
        except Exception as e:  # ett fel här får aldrig stoppa appen
            print("Bakgrundsjobb:", e)
        await asyncio.sleep(600)


@asynccontextmanager
async def lifespan(app):
    db.init()
    background(housekeeping())
    background(enrich.run())  # fortsätt där den slutade vid omstart
    background(music.enrich_all())
    yield
    for t in list(_tasks):
        t.cancel()


async def http_error(request, exc: HTTPException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


async def server_error(request, exc: Exception):
    return JSONResponse({"detail": f"Serverfel: {exc}"}, status_code=500)


async def index(request):
    return FileResponse(os.path.join(STATIC, "index.html"), headers={"Cache-Control": "no-cache"})


async def manifest(request):
    return FileResponse(os.path.join(STATIC, "manifest.webmanifest"), media_type="application/manifest+json")


routes = [
    Route("/", index),
    Route("/manifest.webmanifest", manifest),
    Route("/poster/{name}", poster),
    Route("/api/libraries", libraries_list),
    Route("/api/libraries", library_create, methods=["POST"]),
    Route("/api/libraries/{lib_id:int}", library_rename, methods=["PATCH"]),
    Route("/api/libraries/{lib_id:int}", library_delete, methods=["DELETE"]),
    Route("/api/items", items_list),
    Route("/api/items", item_add, methods=["POST"]),
    Route("/api/items/{item_id:int}", item_get),
    Route("/api/items/{item_id:int}", item_patch, methods=["PATCH"]),
    Route("/api/items/{item_id:int}", item_delete, methods=["DELETE"]),
    Route("/api/items/{item_id:int}/rematch", item_rematch, methods=["POST"]),
    Route("/api/items/{item_id:int}/refresh", item_refresh, methods=["POST"]),
    Route("/api/items/{item_id:int}/posters", item_posters),
    Route("/api/items/{item_id:int}/cover", item_cover, methods=["POST"]),
    Route("/api/covers/import", covers_import, methods=["POST"]),
    Route("/api/facets", facets),
    Route("/api/barcode/{code}", barcode),
    Route("/api/search", search),
    Route("/api/import", import_clz, methods=["POST"]),
    Route("/api/enrich", enrich_start, methods=["POST"]),
    Route("/api/refresh", refresh_library, methods=["POST"]),
    Route("/api/status", status),
    Route("/api/stats", stats),
    Route("/api/random", random_pick),
    Route("/api/collections", collections),
    Route("/api/collections/{coll_id:int}", collection),
    Route("/api/digital/sync", digital_sync, methods=["POST"]),
    Route("/api/digital/only", digital_only),
    Route("/api/music/barcode/{code}", music_barcode),
    Route("/api/music/search", music_search),
    Route("/api/music", music_add, methods=["POST"]),
    Route("/api/music/manual", music_manual, methods=["POST"]),
    Route("/api/ha", home_assistant),
    Route("/api/backup", backup, methods=["POST"]),
    Route("/api/backups/{name}", backup_download),
    Route("/api/restore", backup_restore, methods=["POST"]),
    Route("/api/export", export),
    Route("/api/settings", settings_get),
    Route("/api/settings", settings_put, methods=["PUT"]),
    Route("/api/settings/test/{what}", settings_test, methods=["POST"]),
    Route("/api/login", login, methods=["POST"]),
    Route("/api/logout", logout, methods=["POST"]),
    Route("/api/auth", auth_get),
    Route("/api/auth", auth_put, methods=["PUT"]),
    Route("/api/auth/apikey", auth_new_key, methods=["POST"]),
    Route("/api/health", health),
    Mount("/static", StaticFiles(directory=STATIC), name="static"),
]

app = Starlette(routes=routes, lifespan=lifespan, middleware=[Middleware(AuthMiddleware)],
                exception_handlers={HTTPException: http_error, Exception: server_error})
