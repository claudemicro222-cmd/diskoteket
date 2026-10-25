# Önskelista och status

Senast uppdaterad: 2026-10-25. Version i drift: **3.1** (Unraid, `ghcr.io/claudemicro222-cmd/diskoteket:latest`).

## Önskemål till nästa version (bygg först när ägaren säger till)

1. **Återställ från säkerhetskopia i appen** – ladda upp en `.db`-fil eller välj en av appens egna kopior
   under Meny → Säkerhetskopior. Appen ska själv ta en kopia av nuvarande databas först, ersätta filen,
   ta bort `-wal`/`-shm` och ladda om, så att inget behöver göras via filsystemet.

## Att testa / följa upp

- **MyMovies-uppslaget** är bara testat mot en kopia av deras sida. Verifiera med en riktig skanning,
  t.ex. Evil Dead DVD `7319980033032` (ska ge ”Hittad!” via MyMovies).
- **HTTPS för kameran** på mobilen – reverse proxy (Nginx Proxy Manager/SWAG) eller Tailscale på Unraid.
- **Omslag från CLZ** – ägaren hade egna omslag i CLZ som inte följde med i CSV-exporten.
  Kolla om CLZ kan exportera en kolumn med bildlänk eller XML; annars använd Meny → Importera omslag.
- Kontrollera att paketet på ghcr.io är **publikt** (GitHub → Packages → diskoteket → Package settings).

## Idéer som nämnts men inte beställts

- Musik (CLZ Music-import + Discogs) som egen flik.
- ”Spela i Plex/Jellyfin”-knapp och lista över titlar som bara finns digitalt.
- Färdiga Home Assistant-automationer (försenade lån, slumpa kvällens film).

## Gjort

- 3.1: titel-sökning med väljare, Plats bort ur filtret, streckkodsuppslag (inlärda koder, andra samlingar,
  MyMovies, UPCitemdb, EAN-DB, sök på nätet), skanningsrutan förstår text, fortsätt-läge/kö/klistra in lista,
  egna omslag och massimport, GitHub Actions + Unraid-mall.
- 3.0: Diskoteket-namn, flera samlingar, vyval, ljust/mörkt, formatmärken, inställningssida, lokala omslag,
  uppdatera metadata, Unraid-format (appdata, 99:100).
- 2.0: filter/sortering, redigering, önskelista, utlåning, inventering, statistik, slump, filmserier,
  Plex/Jellyfin, Home Assistant, säkerhetskopior.
