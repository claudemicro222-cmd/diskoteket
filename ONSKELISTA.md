# Önskelista och status

Senast uppdaterad: 2026-10-25. Version **4.1.2** är pushad (`:latest`, `:4.1.2`) – fixar att det inte gick att skriva i fälten på datorn. 4.1.1:
Jellyfin-inloggning för Jellyfin 12, ikon/logotyp för Home Assistant (`brand/`, HA 2026.3+) och säkrare laddning av HA-kortet.
Arbetssätt: ändringar testas lokalt (testserver på port 8765 med kopia av samlingen) och pushas
först när ägaren säger till.

## Önskemål till nästa version (bygg först när ägaren säger till)

**Version 4.2 pushad 2026-10-25.** Alla fem punkter nedan
är klara: töm/ta bort samling, filter utan omslag, engelska + svenska (engelska standard på nya installationer,
svenska på befintliga; README på engelska + README.sv.md; Unraid-mallen och HA-kortet på engelska/svenska),
filter på skådespelare/regissör, ny meny med undermenyer, och IMDb-betyg med stjärna på filmsidan. 40 tester gröna, skrivning testad med riktiga tangenttryck.

_Pushat i 4.1.2 (2026-10-25), bekräftat av ägaren:_ skanningsrutan har fältet överst (med fokus direkt), kollar om datorn har
en kamera innan den startas, och visar förslag med omslag medan man skriver (film via TMDB, musik via
MusicBrainz – egna skivor först med ✓ Har, ihopskrivna sökord som ”harrypotter” delas automatiskt).
**Buggen hittad och fixad:** fälten hade `onkeydown = (e) => e.key === "Enter" && …`, som svarar `false` för alla
andra tangenter – då stoppar webbläsaren tangenttrycket, så inget gick att skriva på ett riktigt tangentbord
(mobilens skärmtangentbord gick förbi det). Gällde skanningsfältet och sökfälten i Lägg till/Fel film/Fel album.
Verifierat med riktiga tangenttryck i Edge.

1. **Ta bort / tömma den enda samlingen** – i dag visas ”Ta bort” bara när det finns flera samlingar, utan förklaring.
   - ”Ta bort” visas alltid. Är det den enda samlingen förklarar appen det och skapar automatiskt en ny tom samling.
   - Ny knapp **”Töm samlingen”**: tar bort alla titlar och all musik men behåller samlingen (och namnet).
   - Säkerhetskopia tas först i båda fallen, precis som i dag.
2. **Filter: ”Saknar omslag”** – i Filter på varje flik (Alla, Filmer, Serier, Musik, Önskelista) ett val
   ”Bara titlar utan omslag”, så man direkt ser vilka som saknar omslag i rutnätet. Visas som ett filterchip
   som går att kryssa bort, och fungerar ihop med övriga filter (t.ex. format eller samling).
   (Det finns redan Meny → ”Saknar omslag”/”Album utan omslag”, men som separata listor – nu i själva rutnätet.)
3. **Flera språk i appen** – all text i appen (även inloggningssidan, vänsidan och felmeddelanden) översatt.
   - **Engelska är standard** på en nyinstallerad app. Språkval under Meny → Inställningar (sparas per enhet).
     Befintliga installationer (som ägarens) får svenska satt automatiskt vid uppgraderingen, så inget ändras där.
   - **README på engelska** som huvudsida på GitHub, med en svensk version (`README.sv.md`) länkad överst.
     Vibecodat-varningen finns kvar på båda. Unraid-mallen och Home Assistant-integrationens texter på engelska
     som standard (HA har redan engelska och svenska).
   - Börja med **svenska och engelska**. Förslag på fler, i ordning: norska, danska, finska (nordiska användare,
     samma utgåvor via MyMovies), tyska, spanska, franska.
   - Valfritt: hämta handling och titlar från TMDB på samma språk (finns redan som egen inställning i dag).
   - Översättningarna görs av Claude (AI) – märks som sådana, och rättelser från användare tas gärna emot.
4. **Filtrera på skådespelare (och regissör)** i rutnätet – i Filter: ett sökbart fält med förslag ur samlingen
   (”Tom H…” → Tom Hanks, Tom Hardy), med antal titlar per namn. Visas som filterchip och går att kombinera med
   andra filter. Även klick på en skådespelare i en film kan ge ”Visa alla i samlingen” direkt i rutnätet.
5. **Ny, enklare meny (☰)** – färre val på första nivån, resten i undermenyer som hör ihop. Förslag:
   - Överst: kort status (antal filmer/serier/album, pågående hämtning, nya låneförfrågningar).
   - **➕ Lägg till** → film/serie, musik, klistra in en lista, importera från CLZ, importera omslag
   - **📚 Samlingen** → statistik, årsöversikt, filmserier, hyllkarta, inventering, saknar omslag, bara digitalt
   - **🤝 Lån och försäljning** → utlånat, vänsida och låneförfrågningar, säljlista
   - **💾 Data** → säkerhetskopior, exportera, tittarhistorik, papperskorgen, uppdatera metadata
   - **⚙ Inställningar** → allmänt (språk, tema, visning), samlingar, TMDB, musik (MusicBrainz/Discogs),
     streckkoder, Plex/Jellyfin, inloggning, Home Assistant – inställningssidan delas upp i dessa undersidor
     i stället för en lång sida.

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
