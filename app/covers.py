"""Egna omslag: uppladdning (foto/fil/bildadress) och massimport av många bilder på en gång."""
import io
import os
import re
import time
import unicodedata
import zipfile

import httpx
from PIL import Image, ImageOps

from . import db, posters, repo

MAX_BYTES = 25 * 1024 * 1024
MAX_HEIGHT = 900
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")


class CoverError(Exception):
    pass


def to_jpeg(data: bytes) -> bytes:
    """Rättar rotation från mobilkameran, skalar ner och sparar som JPEG.
    Bilden beskärs inte – rutnätet visar den i omslagsformat ändå."""
    if len(data) > MAX_BYTES:
        raise CoverError("Bilden är för stor (max 25 MB)")
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
    except Exception:
        raise CoverError("Filen är ingen bild som går att läsa (JPG, PNG eller WebP fungerar)")
    if img.mode not in ("RGB", "L"):
        bg = Image.new("RGB", img.size, (20, 22, 26))
        img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1])
        img = bg
    img = img.convert("RGB")
    if img.height > MAX_HEIGHT:
        img = img.resize((round(img.width * MAX_HEIGHT / img.height), MAX_HEIGHT), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=86, optimize=True)
    return out.getvalue()


def save_for_item(item_id: int, data: bytes) -> dict:
    """Sparar bilden i appdata/posters och kopplar den till titeln (låses mot 'Uppdatera metadata')."""
    jpeg = to_jpeg(data)
    os.makedirs(posters.POSTER_DIR, exist_ok=True)
    name = f"custom-{item_id}-{int(time.time() * 1000)}.jpg"
    with open(os.path.join(posters.POSTER_DIR, name), "wb") as f:
        f.write(jpeg)
    old = repo.get(item_id) or {}
    item = repo.update(item_id, {"poster_path": "/" + name})  # lock=True -> skrivs inte över
    prev = (old.get("poster_path") or "").lstrip("/")
    if prev.startswith(f"custom-{item_id}-") and prev != name:  # städa bort förra egna omslaget
        try:
            os.remove(os.path.join(posters.POSTER_DIR, prev))
        except OSError:
            pass
    return item


async def download(url: str) -> bytes:
    if not re.match(r"^https?://", url or ""):
        raise CoverError("Ange en adress som börjar med http:// eller https://")
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 Diskoteket"}) as c:
            r = await c.get(url)
    except httpx.HTTPError as e:
        raise CoverError(f"Kunde inte hämta bilden: {e}")
    if r.status_code != 200:
        raise CoverError(f"Kunde inte hämta bilden (svar {r.status_code})")
    return r.content


# ---------- Massimport ----------

def norm(text: str) -> str:
    """'Sökarna – Återkomsten!' -> 'sokarna aterkomsten' (för att jämföra titlar mot filnamn)."""
    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def parse_name(filename: str):
    """'Evil Dead (1981).jpg' -> ('evil dead', 1981, None) · '7319980033032.jpg' -> (None, None, '7319980033032')."""
    stem = os.path.splitext(os.path.basename(filename))[0].strip()
    digits = re.sub(r"[\s\-_]", "", stem)
    if digits.isdigit() and 8 <= len(digits) <= 14:
        return None, None, digits
    m = re.match(r"^(.*?)[\s_\-.]*[(\[]?((?:19|20)\d{2})[)\]]?$", stem)
    if m and m.group(1).strip():
        return norm(m.group(1)), int(m.group(2)), None
    return norm(stem), None, None


def collect_files(uploads: list[tuple[str, bytes]]) -> list[tuple[str, bytes]]:
    """Packar upp zip-filer och plockar ut bilderna."""
    out = []
    for name, data in uploads:
        if name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    for info in z.infolist():
                        base = os.path.basename(info.filename)
                        if (not info.is_dir() and base.lower().endswith(IMG_EXT) and not base.startswith(".")
                                and "__MACOSX" not in info.filename and info.file_size <= MAX_BYTES):
                            out.append((base, z.read(info)))
            except zipfile.BadZipFile:
                out.append((name, b""))
        elif name.lower().endswith(IMG_EXT):
            out.append((name, data))
    return out


def bulk_import(uploads: list[tuple[str, bytes]], lib: int | None, only_missing: bool = True) -> dict:
    files = collect_files(uploads)
    s, a = repo._lib(lib)
    with db.connect() as con:
        rows = [dict(r) for r in con.execute(
            f"SELECT id, title, original_title, series_name, season, year, barcode, poster_path, locked "
            f"FROM items WHERE 1=1{s}", a)]
    by_code, by_title = {}, {}
    for r in rows:
        if r["barcode"]:
            by_code.setdefault(r["barcode"].lstrip("0"), []).append(r)
        names = {norm(r["title"]), norm(r["original_title"])}
        if r["series_name"] and r["season"]:
            names |= {norm(f"{r['series_name']} season {r['season']}"), norm(f"{r['series_name']} säsong {r['season']}"),
                      norm(f"{r['series_name']} s{r['season']}")}
        for n in names - {""}:
            by_title.setdefault(n, []).append(r)

    result = {"matched": [], "unmatched": [], "ambiguous": [], "skipped": [], "errors": []}
    for name, data in files:
        title, year, code = parse_name(name)
        hits = by_code.get(code.lstrip("0"), []) if code else by_title.get(title, [])
        if not hits and title and len(title) >= 4:
            # Reserv: filnamnet står som hela ord i titeln, t.ex. "Quantum of Solace" -> "007 Quantum of Solace".
            # Används bara om det ger exakt en film (efter ev. år).
            pat = re.compile(r"(?<![a-z0-9])" + re.escape(title) + r"(?![a-z0-9])")
            loose = {h["id"]: h for n, hs in by_title.items() if pat.search(n) for h in hs}
            loose = [h for h in loose.values() if not year or h["year"] == year]
            if len(loose) == 1:
                hits = loose
        if year and len(hits) > 1:
            hits = [h for h in hits if h["year"] == year] or hits
        if not hits:
            result["unmatched"].append(name)
            continue
        if len(hits) > 1 and not code:
            result["ambiguous"].append({"file": name, "titles": [f"{h['title']} ({h['year'] or '?'})" for h in hits[:4]]})
            continue
        for h in hits:
            if only_missing and h["poster_path"]:
                result["skipped"].append({"file": name, "title": h["title"]})
                continue
            try:
                save_for_item(h["id"], data)
                result["matched"].append({"file": name, "title": h["title"]})
            except CoverError as e:
                result["errors"].append({"file": name, "error": str(e)})
    return result
