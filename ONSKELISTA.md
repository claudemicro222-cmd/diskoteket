# Önskelista och status

Senast uppdaterad: 2026-10-25. Version **4.1.1** är pushad (`:latest`, `:4.1.1`; taggar `v4.0`/`v4.1`/`v4.1.1`):
Jellyfin-inloggning för Jellyfin 12, ikon/logotyp för Home Assistant (`brand/`, HA 2026.3+) och säkrare laddning av HA-kortet.
Arbetssätt: ändringar testas lokalt (testserver på port 8765 med kopia av samlingen) och pushas
först när ägaren säger till.

## Önskemål till nästa version (bygg först när ägaren säger till)

1. **Ta bort / tömma den enda samlingen** – i dag visas ”Ta bort” bara när det finns flera samlingar, utan förklaring.
   - ”Ta bort” visas alltid. Är det den enda samlingen förklarar appen det och skapar automatiskt en ny tom samling.
   - Ny knapp **”Töm samlingen”**: tar bort alla titlar och all musik men behåller samlingen (och namnet).
   - Säkerhetskopia tas först i båda fallen, precis som i dag.

## Att testa / följa upp

- **Jellyfin (4.1.1)** är bara testad mot en låtsas-server – kontrollera ”Testa Jellyfin” mot riktiga servern.

- **4.1 – TMDB-delarna** (trailer, var man kan streama, liknande filmer, skådespelarsida, saknade säsonger,
  släppbevakning) är bara testade mot påhittade TMDB-svar – testkopian saknar TMDB-nyckel. Prova på riktigt med nyckel.
- **4.1 – Prisbevakning:** det finns länkar till Prisjakt/CDON/Tradera och ett maxpris, men ingen automatisk
  avisering när något blir billigt – Prisjakt och CDON har inget öppet API att fråga.
- **4.1 – Offline-läget** fungerar bara över HTTPS (eller localhost) – webbläsare tillåter det inte på vanlig http://.
- **4.1 – Vänsidan** når vänner utanför hemmet bara om appen går att nå utifrån (reverse proxy/Tailscale).

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
- Fler förslag från Claude 2026-10-25 (inte beställda):
  - Utlåning med påminnelse: avisering i Home Assistant/mobilen när ett lån blir försenat, och historik över vem som lånat vad.
  - Filmkväll-läge: flera personer röstar fram kvällens film (tinder-stil på mobilerna) bland osedda titlar.
  - Åldersgräns/barnläge: barnprofil som bara visar barnvänliga titlar (TMDB-certifiering).
  - Musik: favoritlåtar och ”spela i Plex/Jellyfin/Spotify”-länk per album.
  - Säkerhetskopia till annan plats: automatisk kopia till t.ex. en annan Unraid-share eller molnet.
  - Snabbsök med röst: säg titeln i mobilen i stället för att skriva.
  - Kalender med visningar: ”Idag för 10 år sedan såg du…”, och filmer som fyller jämnt i år.
  - Dela ett kort: snygg bild av en film/ett album (omslag + betyg) att skicka till någon.

## Struket av ägaren

- Färdiga Home Assistant-automationer (2026-10-25: ”vi skiter i det”).

## Gjort

- 4.1 (lokalt, inte pushad): bokstavslist (som Radarr), saknade säsonger, egna taggar, välj flera/massredigering,
  papperskorg, vänsida med låneförfrågningar, uppgraderingslista, tittarhistorik + import från Letterboxd/Trakt,
  offline-läge, trailer, skådespelarsida, liknande filmer, släppbevakning, utlåning med streckkod, hyllkarta,
  årsöversikt, var man kan streama, prislänkar + maxpris, samlingens utveckling, skick, säljlista med annonstext.

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
