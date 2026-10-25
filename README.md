<p align="center"><img src="unraid/icon.png" width="96" alt=""></p>

# Diskoteket

Egen film- och seriesamling som du kör själv, till exempel som Docker-container på Unraid.
Mobilanpassad webbsida med streckkodsskanning, flera samlingar, import från CLZ Movies,
omslag från TMDB och koppling till Plex/Jellyfin och Home Assistant.

## Funktioner

- **Skanna streckkoder** med mobilkameran. Okända koder slås upp i MyMovies (nordiska utgåvor),
  UPCitemdb och valfritt EAN-DB. Koder du kopplar till en film kommer appen ihåg.
- **Flera samlingar**, t.ex. ”Mina filmer” och ”Barnens”, plus vy för alla samlingar på en gång.
- **Import från CLZ Movies** (CSV). Allt följer med, även utlåning och inköpspris.
- **Omslag** från TMDB, sparade lokalt. Egna omslag via foto, fil eller bildadress, och massimport av många bilder.
- **Lägg till många på en gång**: fortsätt-läge, kö från serieskanning eller klistra in en lista med titlar.
- **Sök** på titel (standard), skådespelare, regissör eller allt.
- Filter, sortering, rutnät i tre storlekar, listvyer, ljust/mörkt tema.
- Önskelista, utlåning, inventering av hyllan, statistik, filmserier, slumpa kvällens film.
- Plex/Jellyfin visar vilka titlar som också finns digitalt. Home Assistant-sensor via `/api/ha`.
- Automatiska säkerhetskopior.

## Installera på Unraid

Avbilden byggs automatiskt av GitHub vid varje ny version och hämtas från
`ghcr.io/claudemicro222-cmd/diskoteket:latest`.

### Alternativ A – med mallen (enklast)

1. Öppna Unraids terminal (ikonen **`>_`** uppe till höger) och kör:
   ```
   curl -fsSL https://raw.githubusercontent.com/claudemicro222-cmd/diskoteket/main/unraid/install-template.sh | bash
   ```
2. Gå till **Docker → Add Container**.
3. Välj **Diskoteket** i listan **Template** (under *User templates*).
4. Kontrollera porten (8080) och appdata-sökvägen (`/mnt/user/appdata/diskoteket`) och klicka **Apply**.

### Alternativ B – bara i Unraids gränssnitt

**Docker → Add Container** (slå på **Advanced View** uppe till höger) och fyll i:

| Fält | Värde |
|---|---|
| Name | `Diskoteket` |
| Repository | `ghcr.io/claudemicro222-cmd/diskoteket:latest` |
| Icon URL | `https://raw.githubusercontent.com/claudemicro222-cmd/diskoteket/main/unraid/icon.png` |
| WebUI | `http://[IP]:[PORT:8080]/` |
| Network Type | `Bridge` |

Lägg sedan till (längst ner, **Add another Path, Port, Variable…**):

| Typ | Namn | Container | Host / värde |
|---|---|---|---|
| Port | Webbsida | `8080` | `8080` |
| Path | Appdata | `/config` | `/mnt/user/appdata/diskoteket` |
| Variable | PUID | `PUID` | `99` |
| Variable | PGID | `PGID` | `100` |
| Variable | Tidszon | `TZ` | `Europe/Stockholm` |

Klicka **Apply**.

### Första start

1. Öppna `http://<unraid-ip>:8080` (eller klicka på ikonen → **WebUI**).
2. **Meny ☰ → Inställningar**: klistra in din TMDB-nyckel och tryck **Testa nyckeln**.
3. **Meny ☰ → Importera från CLZ**, eller flytta med samlingen från en tidigare installation (se nedan).

### Flytta med samlingen från VM:en / en tidigare installation

1. Stoppa den gamla containern.
2. Kopiera innehållet i dess `data`-mapp (`diskoteket.db`, `posters`, `backup`)
   till `\\tower\appdata\diskoteket\` – **innan** Diskoteket startas på Unraid första gången.
   En gammal `samling.db` byter namn automatiskt.
3. Starta containern. Databasen uppgraderas automatiskt.

### Uppdatera

- **Manuellt:** Docker-fliken → **Check for Updates** → **apply update** på Diskoteket.
  (Eller avancerad vy → **Force update**.)
- **Automatiskt:** installera **CA Auto Update Applications** från Apps och slå på uppdatering för Diskoteket.

Dina data i appdata påverkas aldrig av en uppdatering.

### Kameran på mobilen

Webbläsare släpper bara fram kameran över **HTTPS**. Lägg Diskoteket bakom en reverse proxy med certifikat
(t.ex. Nginx Proxy Manager eller SWAG), eller nå den via Tailscale. Tills dess kan streckkoder och titlar skrivas in för hand.

## Allt viktigt ligger i appdata

```
/mnt/user/appdata/diskoteket/
├── diskoteket.db     samlingar, titlar, inställningar, inlärda streckkoder
├── posters/          omslag (från TMDB och dina egna)
└── backup/           automatiska säkerhetskopior
```

Filerna ägs av 99:100 (nobody:users), precis som andra Unraid-appar.

**Återställa en säkerhetskopia:** stoppa containern, ersätt `diskoteket.db` med en fil från `backup/`
(döp om den till `diskoteket.db`) och starta igen.

## Köra på en vanlig dator (Docker Desktop)

```
docker compose up -d                              # hämtar färdig avbild
docker compose pull && docker compose up -d       # uppdatera
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build   # bygg från koden
```

Öppna http://localhost:8080. Data sparas i mappen `data` bredvid filerna.

## Egna omslag i mängd

**Meny → Importera omslag**: välj många bilder eller en zip-fil. Döp bilderna efter
streckkod (`7319980033032.jpg`) eller titel, gärna med år (`Evil Dead (1981).jpg`).

## Home Assistant

`GET /api/ha` ger antal titlar, osedda, önskelista, utlånat, försenade lån och senast tillagda –
totalt och per samling. Färdig YAML finns under **Meny → Home Assistant**.

## Kod

| Fil | Innehåll |
|---|---|
| `app/main.py` | webbserver (Starlette) och API |
| `app/db.py` | databasen och automatiska uppgraderingar |
| `app/repo.py` | samlingar, listor, sökning, statistik, backup |
| `app/barcodes.py` | streckkodsuppslag (inlärda, MyMovies, UPCitemdb, EAN-DB) |
| `app/covers.py` | egna omslag och massimport |
| `app/enrich.py` | hämtning från TMDB och ”Uppdatera metadata” |
| `app/tmdb.py` | TMDB-anrop |
| `app/posters.py` | lokala omslag |
| `app/settings.py` | inställningssidan |
| `app/clz_import.py` | import från CLZ |
| `app/mediaservers.py` | Plex/Jellyfin |
| `app/static/` | själva webbsidan |
| `unraid/` | Unraid-mall, ikon och installationsskript |
| `.github/workflows/docker.yml` | bygger och publicerar Docker-avbilden |
