"""Läser en CSV-export från CLZ Movies och gör om varje rad till en post i databasen."""
import csv
import io
import re
from datetime import datetime

from . import db

SEASON_RE = re.compile(r"^(?P<name>.+?)[:\-–]?\s+(?:Season|Säsong|Series)\s+(?P<num>\d+)\b", re.I)
IMDB_RE = re.compile(r"(tt\d{6,})")

# CLZ-kolumn -> vårt fält
MAP = {
    "Title": "title",
    "Original Title": "original_title",
    "Sort Title": "sort_title",
    "Genres": "genres",
    "Director": "director",
    "Actor": "actors",
    "Plot": "plot",
    "Country": "country",
    "Language": "language",
    "Format": "format",
    "Edition": "edition",
    "Regions": "regions",
    "Audience Rating": "audience_rating",
    "Location": "location",
    "Notes": "notes",
    "Collection Status": "collection_status",
}


def _int(v):
    try:
        return int(float(str(v).replace(",", ".").strip()))
    except (ValueError, TypeError):
        return None


def _float(v):
    try:
        return float(str(v).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


def _date(v):
    """'Feb 24, 2025' -> '2025-02-24'."""
    v = (v or "").strip()
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            pass
    return v or None


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1")


def parse_row(row: dict) -> dict:
    row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
    item = {field: (row.get(col) or None) for col, field in MAP.items()}
    item["title"] = item["title"] or "(utan titel)"

    item["year"] = _int(row.get("Release Year")) or _int(row.get("Release Date"))
    item["runtime"] = _int(row.get("Runtime"))
    item["nr_discs"] = _int(row.get("Nr Discs"))
    item["imdb_rating"] = _float(row.get("IMDb Rating"))
    my = _float(row.get("My Rating"))
    item["my_rating"] = my if my else None
    item["watched"] = 1 if row.get("Watched", "").lower() in ("yes", "ja", "1", "true") else 0
    item["added_date"] = _date(row.get("Added Date"))
    item["clz_index"] = _int(row.get("Index"))
    item["loaned_to"] = row.get("Loaned To") or None
    item["loan_date"] = _date(row.get("Loan Date"))
    item["due_date"] = _date(row.get("Due Date"))
    item["purchase_price"] = _float(row.get("Purchase Price"))

    barcode = re.sub(r"\D", "", row.get("Barcode", ""))
    item["barcode"] = barcode or None

    m = IMDB_RE.search(row.get("IMDb Url", "") or row.get("IMDb Number", ""))
    item["imdb_id"] = m.group(1) if m else None

    # Serie eller film? CLZ har "Is TV Series", men titlar som "24: Season 3" räknas också.
    season = SEASON_RE.match(item["title"])
    is_tv = row.get("Is TV Series", "").lower() in ("yes", "ja", "1", "true") or bool(season)
    item["kind"] = "tv" if is_tv else "movie"
    if season:
        item["series_name"] = season.group("name").strip()
        item["season"] = int(season.group("num"))
    elif is_tv:
        item["series_name"] = row.get("Series") or item["title"]

    used = set(MAP) | {"Release Year", "Release Date", "Runtime", "Nr Discs", "IMDb Rating",
                       "My Rating", "Watched", "Added Date", "Index", "Barcode", "IMDb Url",
                       "IMDb Number", "Is TV Series", "Loaned To", "Loan Date", "Due Date",
                       "Purchase Price"}
    item["extra"] = {k: v for k, v in row.items() if k not in used and v}
    # Bildlänk till omslaget, om exporten har en (t.ex. "Front Cover", "Cover Front", "Image URL")
    for k, v in row.items():
        if re.search(r"cover|image|poster|bild|omslag", k, re.I) and re.match(r"^https?://\S+$", v or "") \
                and not re.search(r"back|bak", k, re.I):
            item["cover_url"] = v
            break
    return item


def import_csv(raw: bytes, library_id: int = 1) -> dict:
    text = _decode(raw)
    reader = csv.DictReader(io.StringIO(text))
    added = updated = 0
    errors = []
    cover_urls = []
    with db.connect() as con:
        for i, row in enumerate(reader, start=2):
            try:
                item = parse_row(row)
                item["library_id"] = library_id
                item_id, new = db.upsert(con, item)
                if item.get("cover_url"):
                    cover_urls.append((item_id, item["cover_url"]))
                added += new
                updated += not new
            except Exception as e:  # en trasig rad ska inte stoppa hela importen
                errors.append(f"Rad {i}: {e}")
    return {"added": added, "updated": updated, "errors": errors[:20], "cover_urls": cover_urls}
