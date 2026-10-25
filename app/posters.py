"""Omslag sparas lokalt i appdata/posters, så att appen fungerar även om TMDB ligger nere."""
import asyncio
import os
import re

import httpx

from . import db, settings
from .tmdb import IMG

POSTER_DIR = os.path.join(db.CONFIG_DIR, "posters")
SIZE = "w342"  # en storlek räcker – webbläsaren skalar ner till små rutor
NAME_RE = re.compile(r"^/?([A-Za-z0-9_\-]+\.(?:jpg|jpeg|png|webp))$")

state = {"running": False, "done": 0, "total": 0}
_http: httpx.AsyncClient | None = None


def _client():
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=8))
    return _http


def local_path(path: str) -> str | None:
    m = NAME_RE.match(path or "")
    return os.path.join(POSTER_DIR, m.group(1)) if m else None


def remote_url(path: str) -> str:
    return f"{IMG}{SIZE}/{path.lstrip('/')}"


async def fetch(path: str) -> str | None:
    """Ger sökvägen till en lokal kopia, och laddar ner den först om den saknas."""
    dest = local_path(path)
    if not dest:
        return None
    if os.path.exists(dest):
        return dest
    if not settings.get_bool("local_posters"):
        return None
    os.makedirs(POSTER_DIR, exist_ok=True)
    try:
        r = await _client().get(remote_url(path))
        if r.status_code != 200 or not r.content:
            return None
        tmp = dest + ".part"
        with open(tmp, "wb") as f:
            f.write(r.content)
        os.replace(tmp, dest)
        return dest
    except (httpx.HTTPError, OSError):
        return None


async def prefetch_all():
    """Laddar ner alla omslag som inte redan finns lokalt (körs efter import och omslagshämtning)."""
    if state["running"] or not settings.get_bool("local_posters"):
        return
    with db.connect() as con:
        paths = {r[0] for r in con.execute("SELECT DISTINCT poster_path FROM items WHERE poster_path IS NOT NULL")}
    todo = [p for p in paths if local_path(p) and not os.path.exists(local_path(p))]
    state.update(running=True, done=0, total=len(todo))
    sem = asyncio.Semaphore(6)

    async def one(p):
        async with sem:
            await fetch(p)
            state["done"] += 1

    try:
        await asyncio.gather(*(one(p) for p in todo))
    finally:
        state["running"] = False


def disk_usage():
    if not os.path.isdir(POSTER_DIR):
        return {"files": 0, "mb": 0}
    files = [os.path.join(POSTER_DIR, f) for f in os.listdir(POSTER_DIR) if not f.endswith(".part")]
    return {"files": len(files), "mb": round(sum(os.path.getsize(f) for f in files) / 1024 / 1024, 1)}
