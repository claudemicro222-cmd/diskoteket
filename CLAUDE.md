# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Arbetssätt

- Ägaren skriver på svenska. All text i appen, koden (kommentarer) och dokumentationen är på svenska.
- **Bygg inte en ny version utan att fråga.** Samla önskemål i en numrerad lista och bekräfta tolkningen; bygg först när ägaren säger till.
- Önskemål, status och saker att följa upp står i `ONSKELISTA.md` – läs den först och håll den uppdaterad.
- Projektet är vibecodat: all kod är skriven av Claude, inte av en professionell utvecklare. Varningsrutan högst upp
  i `README.md` ska alltid finnas kvar och stämma, även när README skrivs om. Samma sak nämns i Unraid-mallen och i appens meny.
- Varje push till `main` kör testerna och bygger sedan `ghcr.io/claudemicro222-cmd/diskoteket:latest` plus en tagg med
  versionsnumret (`VERSION` i `app/main.py`, t.ex. `:4.0`) via `.github/workflows/docker.yml`. Ändringar i bara `*.md`,
  `unraid/`, `custom_components/` eller `hacs.json` bygger ingen ny avbild. Höj `VERSION` vid varje ny version.

## Köra lokalt och testa

```
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q                                              # alla tester
python -m pytest -q tests/test_upgrade.py -k music               # ett urval
CONFIG_DIR=./data uvicorn app.main:app --reload --port 8080      # utan Docker
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build   # bygg avbild från koden
```

- Utan `CONFIG_DIR` används `/config` om den finns, annars `./data` (se `app/db.py`).
- Testerna (`tests/`) bygger databaser som de såg ut i version 1, 2 och 3 (`tests/old_schemas.py`) och kontrollerar att
  uppgraderingen inte tappar data. Lägg till ett fall där när schemat ändras. `conftest.py` stänger av alla uppslag på nätet.
- Testa också före push: starta servern mot en **kopia** av en riktig gammal databas, kör API-anrop och klicka igenom i en
  headless-webbläsare. `GET /api/health` är hälsokontrollen (och öppen även med inloggning på).
- `MYMOVIES_URL`, `TMDB_API`, `TMDB_IMG`, `MUSICBRAINZ_API`, `COVERART_API` och `DISCOGS_API` kan pekas mot lokala kopior.
- Ägarens riktiga data (CLZ-exporter, databaser) får aldrig hamna i repot – det är publikt.

## Arkitektur

- **Backend:** Starlette + uvicorn (`app/main.py`) med alla routes i en lista längst ner i filen. Ren JSON-API under `/api/…`,
  plus `/` (index.html) och `/poster/{name}`. `lifespan` kör `db.init()` och startar bakgrundsjobb (säkerhetskopior,
  Plex/Jellyfin-synk, `enrich.run()` för TMDB och `music.enrich_all()` för musik – båda fortsätter efter omstart).
  Fel i bakgrundsjobb loggas men får aldrig stoppa appen.
- **Frontend:** en enda sida, `app/static/app.js` (vanilla JS, ingen bundler) + `style.css` + `index.html` (+ `login.html`).
  Ändra filerna direkt. Vyerna är funktioner `viewX()` som ritar i ett bottenark (`openSheet`) med bakåtstack (`show`/`back`).
- **Databas:** SQLite i WAL-läge, `CONFIG_DIR/diskoteket.db`. `db.connect()` är en contextmanager som committar själv.
  Tabellen `items` har egna kolumner för fälten i `db.FIELDS`; allt annat från CLZ sparas som JSON i kolumnen `extra` så inget går förlorat.
- **Film, serier och musik i samma tabell:** `items.kind` är `movie`, `tv` eller `music`. Fliken "Alla" visar bara film och
  serier (`kind=video` i API:t, se `repo.KIND_SQL`); musik har egen flik, egna filter (`facets(kind=…)`) och egen statistik.
  Musik använder `artist`, `label`, `cat_no`, `tracks`, `tracklist` (JSON), `mbid`, `discogs_id`; speltid i `runtime` (minuter).
- **CLZ-import:** `clz_import.import_csv` känner igen CLZ Movies eller CLZ Music på kolumnerna. CLZ numrerar varje export
  från 1, så unika nyckeln är `(library_id, kind='music', clz_index)` (`idx_items_clz2`) – musik får aldrig skriva över film.
- **Schemauppgradering** (`db.init()`): det finns inga migrationsfiler. Lägg till nya kolumner i `ITEMS_TABLE`/`FIELDS`;
  vid start byggs `items` om (via `items_new`) när kolumner saknas och all gemensam data kopieras över. Övriga tabeller i
  `OTHER_TABLES` skapas med `IF NOT EXISTS`, nya kolumner där läggs till med `ALTER TABLE`. Ändringar måste fungera på en
  befintlig databas utan dataförlust. Obs: `ITEMS_TABLE` körs genom `.format()` – inga `{}` i SQL-kommentarer.
- **Låsta fält:** `items.locked` är en kommaseparerad lista med fält som ägaren ändrat i appen. `db.upsert` (CLZ-import),
  `enrich` / `music.refresh_item` (”Uppdatera metadata”/”Hämta info igen”) och omslagsbyte måste hoppa över dem.
- **Musikuppslag** (`app/music.py`): MusicBrainz (max ett anrop per sekund, köas med ett lås) och valfritt Discogs.
  Omslag sparas lokalt som `posters/music-<id>-<tid>.jpg`; egna omslag heter `custom-…`. Sådana filer finns bara lokalt
  (`posters.is_tmdb`) – allt annat i `poster_path` är TMDB-sökvägar.
- **Inställningar** (`app/settings.py`): sparas i tabellen `settings` via inställningssidan. Nya inställningar läggs i `DEFS`;
  miljövariabeln där är bara startvärde om inget är sparat. Använd inte `.env` för nya inställningar.
- **Inloggning** (`app/auth.py`, `AuthMiddleware` i `main.py`): valfritt lösenord, hash i `CONFIG_DIR/auth.json` – medvetet
  utanför databasen så att en återställd säkerhetskopia inte ändrar lösenordet. Öppna vägar: `PUBLIC` (statiska filer,
  omslag, inloggning, hälsa). API-nyckeln (Bearer) ger bara läsrätt till `/api/ha`.
- **Återställning** (`repo.restore_backup`): validerar filen, tar en säkerhetskopia, checkpointar WAL, byter fil, tar bort
  gamla `-wal`/`-shm` och kör `db.init()`. Vägras medan bakgrundsjobb pågår.
- **Home Assistant** (`custom_components/diskoteket/`, installeras via HACS): coordinator som läser `GET /api/ha`, sensorer
  (huvudsensorn bär hela sammanfattningen som attribut) och Lovelace-kortet `frontend/diskoteket-card.js` (vanilla JS,
  laddas automatiskt via `add_extra_js_url`). Omslag i kortet går via HA-vyn `/api/diskoteket/<entry>/poster/<namn>`
  med signerade adresser. Ändrar du `/api/ha` – behåll gamla nycklar, äldre REST-sensorer använder dem.
- **Övriga moduler:** `repo.py` (samlingar, listor, sökning, statistik, dubbletter, bara digitalt, export, backup),
  `barcodes.py` (film: inlärda koder → andra samlingar → MyMovies → UPCitemdb → EAN-DB), `enrich.py`/`tmdb.py` (TMDB),
  `posters.py`/`covers.py` (lokala och egna omslag), `mediaservers.py` (Plex/Jellyfin).

## Drift (Unraid)

- Körs via mallen `unraid/diskoteket.xml`. All data ligger i `/config` (= `/mnt/user/appdata/diskoteket`):
  `diskoteket.db`, `auth.json`, `posters/`, `backup/`.
- `entrypoint.sh` sätter ägare till PUID:PGID (99:100) och startar uvicorn med `setpriv`. `db.init()` gör DB-filerna
  grupp-skrivbara (0664) – nya filer i `/config` ska också fungera för `nobody:users`.
- Kameran (streckkodsskanning) kräver HTTPS i mobilens webbläsare.
- Ikonen ritas i `app/static/icon.svg`; PNG-filerna (`icon-*.png`, `unraid/icon.png`) är renderade från den.
