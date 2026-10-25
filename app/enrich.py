"""Hämtar omslag, handling och filmserie från TMDB för många titlar på en gång (parallellt),
och 'Uppdatera metadata' för en titel eller en hel samling."""
import asyncio

from . import db, posters, repo, tmdb

PARALLEL = 8  # samtidiga anrop – TMDB tillåter ungefär 40 per sekund

state = {"running": False, "done": 0, "total": 0, "failed": 0, "mode": ""}


async def match(it: dict) -> dict | None:
    """Hitta rätt TMDB-titel för en post (via IMDb-ID, annars titel och år)."""
    if it.get("imdb_id"):
        hit = await tmdb.find_by_imdb(it["imdb_id"], it.get("season"))
        if hit:
            return hit
    results = await tmdb.search(it.get("series_name") or it["title"], it.get("year"))
    wanted = "tv" if it["kind"] == "tv" else "movie"
    found = [r for r in results if r["type"] == wanted and (wanted == "tv" or r["year"] == it.get("year"))]
    if found:
        return {"tmdb_id": found[0]["tmdb_id"], "poster_path": found[0]["poster_path"],
                "overview": found[0].get("overview"), "type": wanted}
    return None


async def _first_time(it: dict):
    """Första hämtningen efter import: omslag, ev. handling och filmserie."""
    if it["enriched"] == 0:
        hit = await match(it)
        with db.connect() as con:
            if not hit:
                con.execute("UPDATE items SET enriched=2 WHERE id=?", (it["id"],))
                state["failed"] += 1
                return
            con.execute(
                "UPDATE items SET tmdb_id=?, poster_path=COALESCE(?, poster_path), "
                "plot=COALESCE(NULLIF(plot,''), ?), enriched=1 WHERE id=?",
                (hit["tmdb_id"], hit["poster_path"], hit.get("overview"), it["id"]))
        it["tmdb_id"] = hit["tmdb_id"]
    if it["kind"] == "movie" and it["tmdb_id"]:
        coll = await tmdb.movie_collection(it["tmdb_id"])
        with db.connect() as con:
            con.execute("UPDATE items SET collection_id=?, collection_name=?, coll_checked=1 WHERE id=?",
                        (coll and coll["id"], coll and coll["name"], it["id"]))


async def refresh_item(item_id: int, reset: bool = False) -> dict | None:
    """Hämtar metadata på nytt. Fält du ändrat själv behålls – utom med reset=True."""
    it = repo.get(item_id)
    if not it:
        return None
    if not it["tmdb_id"]:
        hit = await match(it)
        if not hit:
            return None
        it["tmdb_id"] = hit["tmdb_id"]
        repo.update(item_id, {"tmdb_id": hit["tmdb_id"]}, lock=False)
    kind = "tv" if it["kind"] == "tv" else "movie"
    d = await tmdb.details(it["tmdb_id"], kind)
    changes = {"original_title": d["original_title"], "genres": d["genres"] or None,
               "director": d["director"], "actors": d["actors"], "imdb_id": d["imdb_id"] or it["imdb_id"],
               "plot": d["plot"] or it["plot"], "poster_path": d["poster_path"] or it["poster_path"],
               "enriched": 1, "coll_checked": 1}
    if kind == "movie":
        changes.update(runtime=d["runtime"] or it["runtime"],
                       collection_id=d["collection_id"], collection_name=d["collection_name"])
        if reset:
            changes.update(title=d["title"], year=d["year"])
    else:
        s = await tmdb.season(it["tmdb_id"], it["season"]) if it.get("season") else None
        if s:
            changes["poster_path"] = s["poster_path"] or changes["poster_path"]
            changes["plot"] = s["overview"] or changes["plot"]
        if reset:
            changes.update(series_name=d["title"], year=(s or {}).get("year") or d["year"],
                           title=f"{d['title']}: Säsong {it['season']}" if it.get("season") else d["title"])
    if reset:
        repo.update(item_id, {}, lock=False, unlock=repo.LOCKABLE)
    else:
        changes = {k: v for k, v in changes.items() if k not in it["locked"]}
    item = repo.update(item_id, changes, lock=False)
    if item.get("poster_path"):
        await posters.fetch(item["poster_path"])
    return item


async def _run(todo, fn, mode):
    state.update(running=True, done=0, total=len(todo), failed=0, mode=mode)
    sem = asyncio.Semaphore(PARALLEL)

    async def worker(x):
        async with sem:
            try:
                await fn(x)
            except Exception:
                state["failed"] += 1
            state["done"] += 1

    try:
        await asyncio.gather(*(worker(x) for x in todo))
    finally:
        state["running"] = False
    asyncio.create_task(posters.prefetch_all())


async def run():
    """Matchar nya titlar och hämtar filmserier, i alla samlingar."""
    if state["running"] or not tmdb.enabled():
        return
    with db.connect() as con:
        todo = [dict(r) for r in con.execute(
            "SELECT id, title, series_name, season, year, imdb_id, tmdb_id, kind, enriched FROM items "
            "WHERE enriched=0 OR (kind='movie' AND enriched=1 AND COALESCE(coll_checked,0)=0)")]
    if todo:
        await _run(todo, _first_time, "match")
    else:
        asyncio.create_task(posters.prefetch_all())


async def refresh_library(lib: int | None, reset: bool = False):
    """Uppdatera metadata för en hel samling (eller alla)."""
    if state["running"] or not tmdb.enabled():
        return
    s, a = repo._lib(lib, " WHERE ")
    with db.connect() as con:
        ids = [r[0] for r in con.execute(f"SELECT id FROM items{s}", a)]

    async def one(item_id):
        if not await refresh_item(item_id, reset):
            state["failed"] += 1

    await _run(ids, one, "refresh")
