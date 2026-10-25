# Diskoteket

Egen film- och seriesamling. Mobilanpassad webbsida med streckkodsskanning, flera samlingar,
import från CLZ Movies, omslag från TMDB och koppling till Plex/Jellyfin och Home Assistant.

## Allt viktigt ligger i appdata

```
/mnt/user/appdata/diskoteket/      (i VM:en: mappen data/)
├── diskoteket.db                  databasen – samlingar, titlar och inställningar
├── posters/                       omslag sparade lokalt
└── backup/                        automatiska säkerhetskopior
```

Säkerhetskopiera den mappen så är allt med. Filerna ägs av 99:100 (nobody:users), precis som andra Unraid-appar.

## Installera på Unraid

1. Kopiera hela projektmappen till Unraid, t.ex. till `\\tower\appdata\diskoteket-kod`
   (det är bara koden – dina data hamnar i `appdata\diskoteket`).
2. Öppna Unraids terminal (`>_` uppe till höger) och kör:
   ```
   bash /mnt/user/appdata/diskoteket-kod/unraid/install.sh
   ```
3. Gå till **Docker → Add Container**, välj mallen **Diskoteket** och klicka **Apply**.
4. Öppna `http://tower:8080` → Meny ☰ → **Inställningar** och fyll i din TMDB-nyckel.

### Flytta med samlingen från VM:en

Stoppa containern i VM:en och kopiera innehållet i `data\` därifrån till `\\tower\appdata\diskoteket\`
**innan** du startar Diskoteket på Unraid första gången. En gammal `samling.db` byter namn automatiskt.

### Uppdatera till en ny version

Ersätt filerna i `diskoteket-kod`, kör `install.sh` igen och klicka sedan **Edit → Apply** på containern.
Databasen uppgraderas automatiskt.

## Köra i VM:en (Docker Desktop)

```
docker compose up -d --build
```
Öppna http://localhost:8080. Data sparas i mappen `data` bredvid koden.

## Inställningar

Allt ställs in i appen under **Meny → Inställningar** och sparas i databasen:
TMDB-nyckel och språk, lokala omslag, säkerhetskopior, Plex och Jellyfin.
Har du en gammal `.env` från version 1–2 används den som startvärden tills du sparar något i appen.

## Återställa en säkerhetskopia

Stoppa containern, ersätt `diskoteket.db` i appdata med en fil från `backup/` (döp om den till `diskoteket.db`)
och starta igen. Inför borttagning av en samling tas alltid en extra kopia som inte rensas bort automatiskt.

## Kameran på mobilen

Webbläsare släpper bara fram kameran över **HTTPS** (eller på localhost). Lägg Diskoteket bakom en
reverse proxy med certifikat (t.ex. Nginx Proxy Manager) eller nå den via Tailscale. Tills dess kan
streckkoder skrivas in för hand.

## Home Assistant

`GET /api/ha` ger antal titlar, osedda, önskelista, utlånat, försenade lån och senast tillagda –
totalt och per samling. Färdig YAML finns under Meny → Home Assistant.

## Kod

- `app/main.py` – webbserver (Starlette) och API
- `app/db.py` – databasen och automatiska uppgraderingar
- `app/repo.py` – samlingar, listor, sökning, statistik, backup
- `app/settings.py` – inställningssidan
- `app/enrich.py` – omslag och ”Uppdatera metadata”
- `app/tmdb.py` – TMDB och streckkodsuppslag
- `app/posters.py` – lokala omslag
- `app/clz_import.py` – import från CLZ
- `app/mediaservers.py` – Plex/Jellyfin
- `app/static/` – själva webbsidan
- `unraid/` – Unraid-mall och installationsskript
