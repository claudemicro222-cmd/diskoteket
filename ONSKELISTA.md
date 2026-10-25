# Önskelista och status

Senast uppdaterad: 2026-10-25. Version i drift: **3.1** (Unraid, `ghcr.io/claudemicro222-cmd/diskoteket:latest`).
Version **4.0** är byggd och testad lokalt men **inte pushad** än – väntar på ägarens klartecken.

## Önskemål till nästa version (bygg först när ägaren säger till)

_Inga just nu._

## Att testa / följa upp

- **4.0 på riktigt:** efter uppdatering på Unraid – kontrollera att musikfliken fylls (låtlistor och omslag hämtas
  i bakgrunden, några sekunder per album) och att filmerna är orörda.
- **Home Assistant-integrationen** är bara kompilerad och kortet bara testat i en fristående testsida, inte i en riktig
  Home Assistant. Installera via HACS (anpassat arkiv), lägg till integrationen och kortet, prova alla tre detaljnivåer.
- **MyMovies-uppslaget** är bara testat mot en kopia av deras sida. Verifiera med en riktig skanning,
  t.ex. Evil Dead DVD `7319980033032` (ska ge ”Hittad!” via MyMovies).
- **HTTPS för kameran** på mobilen – reverse proxy (Nginx Proxy Manager/SWAG) eller Tailscale på Unraid.
  Slå på inloggning (Meny → Inloggning) innan appen nås utifrån.
- **Omslag från CLZ** – ägaren hade egna omslag i CLZ som inte följde med i CSV-exporten.
  Kolla om CLZ kan exportera en kolumn med bildlänk eller XML; annars använd Meny → Importera omslag.
- **Album som inte hittas** i MusicBrainz (Meny → Album utan omslag): prova Discogs-nyckel, ”Fel album?” eller eget omslag.
- CLZ Music-exporten (`export_albums.csv`, 176 album) ligger hos ägaren, inte i repot. CLZ Music har egen `Index`-serie;
  därför är unikhetsregeln `(library_id, kind='music', clz_index)`.

## Idéer som nämnts men inte beställts

- ”Spela i Plex/Jellyfin”-knapp.
- Plex/Jellyfin för musik (vilka album som finns digitalt).
- Inloggning via reverse proxyns användare (t.ex. Authelia) i stället för eget lösenord.

## Struket av ägaren

- Färdiga Home Assistant-automationer (2026-10-25: ”vi skiter i det”).

## Gjort

- 4.0: återställ säkerhetskopia i appen (egen kopia eller uppladdad fil), musik som egen flik (CLZ Music-import,
  MusicBrainz/Discogs, låtlistor, skivomslag, skanning, ”Fel album?”), Home Assistant-integration via HACS med kort i
  tre detaljnivåer, nytt utseende (bio/streaming, ”Nyligen tillagt”, tonfärg från omslaget), ny ikon och logotyp,
  valfri inloggning + API-nyckel, automatiska tester (uppgradering från v1–v3, import, inloggning, återställning, export),
  versionstagg på Docker-avbilden (`:4.0`), export CSV/JSON, statistik för musik/värde/dubbletter, ”Bara digitalt”.
- 3.1: titel-sökning med väljare, Plats bort ur filtret, streckkodsuppslag (inlärda koder, andra samlingar,
  MyMovies, UPCitemdb, EAN-DB, sök på nätet), skanningsrutan förstår text, fortsätt-läge/kö/klistra in lista,
  egna omslag och massimport, GitHub Actions + Unraid-mall.
- 3.0: Diskoteket-namn, flera samlingar, vyval, ljust/mörkt, formatmärken, inställningssida, lokala omslag,
  uppdatera metadata, Unraid-format (appdata, 99:100).
- 2.0: filter/sortering, redigering, önskelista, utlåning, inventering, statistik, slump, filmserier,
  Plex/Jellyfin, Home Assistant, säkerhetskopior.
