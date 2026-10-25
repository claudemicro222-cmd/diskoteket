// Översättning av gränssnittet. Svenska är källspråket i koden – den här filen byter ut texten
// i webbläsaren när ett annat språk är valt. Översättningarna är gjorda av Claude (AI).
// Tre nivåer: exakt text → mönster med siffror/namn → ord för ord (bara om alla ord är kända).
// Filmtitlar, handling, namn och egna anteckningar översätts aldrig (se SKIP).
"use strict";

const I18N = (() => {
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem("lang")); } catch { /* privat läge */ }
  const lang = saved || document.documentElement.dataset.lang || "en";
  document.documentElement.lang = lang;
  return { lang };
})();
function appLang() { return I18N.lang; }
function setLang(lang) {
  try { localStorage.setItem("lang", JSON.stringify(lang)); } catch { /* privat läge */ }
  location.reload();
}

const EN = {
  exact: {
    // Allmänt
    "Alla": "All", "Filmer": "Movies", "Serier": "Series", "Musik": "Music", "Önskelista": "Wish list",
    "Filter": "Filter", "Meny": "Menu", "Spara": "Save", "Avbryt": "Cancel", "Klar": "Done", "Klart": "Done", "Välj": "Select",
    "Ta bort": "Delete", "Redigera": "Edit", "Sök": "Search", "Hämta": "Fetch", "Hämtar…": "Loading…", "Söker…": "Searching…",
    "Sparar…": "Saving…", "Läser…": "Reading…", "Testar…": "Testing…", "Letar…": "Looking…", "Importerar…": "Importing…",
    "Återställer…": "Restoring…", "Sparat": "Saved", "Fel": "Error", "Visa": "Show", "Nollställ": "Reset", "Skapa": "Create",
    "Starta": "Start", "Fortsätt": "Continue", "Avsluta": "Finish", "Öppna": "Open", "Öppna ↗": "Open ↗", "Importera": "Import",
    "Exportera": "Export", "Ladda ner": "Download", "Återställ": "Restore", "Ångra": "Undo", "På": "On", "Av": "Off", "på": "on",
    "Tom": "Empty", "Allt": "Everything", "Status": "Status", "Typ": "Type", "Data": "Data", "Inget här.": "Nothing here.",
    "Kunde inte ladda samlingen:": "Could not load the collection:", "Finns inte": "Not found",
    "Offline – du ser en sparad kopia av samlingen": "Offline – you are seeing a saved copy of the collection",
    "Vibecodat – byggt av Claude (AI), inte av en proffsutvecklare.": "Vibe-coded – built by Claude (AI), not by a professional developer.",
    // Huvudet och sökning
    "Sök titel…": "Search title…", "Sök skådespelare…": "Search actor…", "Sök regissör…": "Search director…",
    "Sök titel, skådespelare, regissör…": "Search title, actor, director…", "Sök album eller artist…": "Search album or artist…",
    "Titel": "Title", "Skådespelare": "Actors", "Regissör": "Director", "Byt samling": "Switch collection", "Slumpa en film": "Pick a random movie",
    "Visning och tema": "View and theme", "Skanna streckkod": "Scan barcode", "Hoppa till bokstav": "Jump to letter",
    "Diskoteket – till början": "Diskoteket – back to top",
    "Nyligen tillagt": "Recently added", "★ Önskat": "★ Wanted", "⬆ Uppgradera": "⬆ Upgrade", "Markera alla": "Select all", "Ändra…": "Change…",
    "Inget att uppgradera. Öppna en titel → Redigera → ”Vill uppgradera till”.": "Nothing to upgrade. Open a title → Edit → “Want to upgrade to”.",
    "Önskelistan är tom. Skanna eller sök en titel och välj ”Önskelista”.": "The wish list is empty. Scan or search for a title and choose “Wish list”.",
    "Inget matchade. Prova att ändra filtren.": "Nothing matched. Try changing the filters.",
    "Ingen musik än. Öppna menyn och importera en export från CLZ Music, eller skanna din första skiva.": "No music yet. Open the menu and import an export from CLZ Music, or scan your first disc.",
    "Samlingen är tom. Öppna menyn och importera en CLZ-export, eller skanna din första film.": "The collection is empty. Open the menu and import a CLZ export, or scan your first movie.",
    "Ute på skiva": "Out on disc", "Till salu": "For sale", "Utlånad": "Loaned out", "Utan omslag": "No cover",
    "Sedda": "Watched", "Osedda": "Unwatched", "Finns digitalt": "Available digitally", "Bara fysiskt": "Physical only", "Utlånade": "Loaned out",
    // Visning
    "Visning": "View", "Små": "Small", "Mellan": "Medium", "Stora": "Large", "Lista": "List", "Kompakt": "Compact", "Tema": "Theme",
    "Auto": "Auto", "Ljust": "Light", "Mörkt": "Dark",
    "Auto följer inställningen i mobilen eller datorn. Valen sparas på den här enheten.": "Auto follows your phone or computer setting. Your choices are saved on this device.",
    // Filter
    "Filter och sortering": "Filter and sort", "Gäller fliken Musik": "Applies to the Music tab", "Gäller filmer och serier": "Applies to movies and series",
    "Sortera": "Sort", "Titel A–Ö": "Title A–Z", "Artist A–Ö": "Artist A–Z", "Senast tillagd": "Recently added",
    "År (nyast först)": "Year (newest first)", "År (äldst först)": "Year (oldest first)", "Mitt betyg": "My rating", "IMDb-betyg": "IMDb rating",
    "Längd (kortast först)": "Length (shortest first)", "Inköpspris": "Purchase price", "Format": "Format", "Alla format": "All formats",
    "Genre": "Genre", "Alla genrer": "All genres", "Sedd": "Watched", "Tagg": "Tag", "Alla taggar": "All tags",
    "Skådespelare eller regissör": "Actor or director", "Börja skriva, t.ex. Tom H…": "Start typing, e.g. Tom H…",
    "Visa bara utlånade": "Show only loaned out", "Bara titlar utan omslag": "Only titles without a cover", "· regi": "· director",
    // Samlingar
    "Samlingar": "Collections", "Alla samlingar": "All collections", "Hantera samlingar": "Manage collections", "Byt namn": "Rename",
    "Töm": "Empty", "Ny samling": "New collection", "T.ex. Barnens filmer": "E.g. Kids’ movies", "Nytt namn:": "New name:",
    "Importera en CLZ-export till en samling via Meny → Lägg till → Importera från CLZ.": "Import a CLZ export into a collection via Menu → Add → Import from CLZ.",
    "Töm samlingen": "Empty the collection", "Ta bort samling": "Delete collection", "Ta bort för gott": "Delete for good",
    "tas bort. Samlingen och namnet finns kvar.": "will be removed. The collection and its name are kept.",
    "Det är din enda samling, så en ny tom samling skapas i stället.": "It is your only collection, so a new empty collection is created instead.",
    "En säkerhetskopia av hela databasen sparas automatiskt precis innan, så det går att ångra.": "A backup of the whole database is saved automatically just before, so it can be undone.",
    "Skriv": "Type", "för att bekräfta": "to confirm", "Samlingen": "The collection", "Samling": "Collection", "Samling:": "Collection:",
    "Till samling": "To collection", "+ Ny samling…": "+ New collection…", "Namn på ny samling": "Name of the new collection",
    // Detaljvyn
    "▶ Trailer": "▶ Trailer", "Trailer": "Trailer", "Köpt! Flytta till samlingen": "Bought! Move to collection", "✓ Sedd": "✓ Watched",
    "Markera som sedd": "Mark as watched", "Återlämnad": "Returned", "Låna ut": "Lend", "Uppdatera metadata": "Update metadata",
    "Byt omslag": "Change cover", "Eget omslag": "Custom cover", "Fel film?": "Wrong movie?", "IMDb": "IMDb",
    "År": "Year", "År:": "Year:", "Utgåva": "Edition", "Längd": "Length", "Regi": "Director", "Regi/skapare": "Director/creator",
    "Skivor": "Discs", "Streckkod": "Barcode", "Undertext": "Subtitles", "Inköpt": "Purchased", "Digitalt:": "Digital:",
    "Filmserie:": "Collection:", "Handling": "Plot", "Anteckningar": "Notes", "Plats:": "Location:", "Skick:": "Condition:",
    "(försenad!)": "(overdue!)", "Utlånad till": "Loaned to", "sedan": "since", "åter": "due", "försenad": "overdue",
    "Flyttad till samlingen": "Moved to the collection", "Markerad som återlämnad": "Marked as returned",
    "Flyttad till papperskorgen ·": "Moved to the trash ·", "Tillbaka i samlingen": "Back in the collection",
    "Ändrat av dig (skrivs inte över):": "Changed by you (not overwritten):",
    "★ På önskelistan": "★ On the wish list", "finns på skiva": "out on disc", "· släpps på skiva": "· released on disc",
    "· köp om högst": "· buy for at most", "⬆ Vill uppgradera till": "⬆ Want to upgrade to", "för": "for",
    "👁 Sedd (inget datum)": "👁 Watched (no date)", "lägg till datum": "add date", "historik": "history",
    "Var kan jag se den?": "Where can I watch it?", "Streama": "Stream", "Hyr": "Rent", "Köp digitalt": "Buy digitally", "mer ↗": "more ↗",
    "Finns inte att streama i Sverige just nu (enligt JustWatch).": "Not available to stream in Sweden right now (according to JustWatch).",
    "Liknande i din samling": "Similar in your collection", "Liknande att skaffa": "Similar to get",
    "Serie": "Series", "Film": "Movie", "★ Lägg på önskelistan": "★ Add to wish list", "Jag har den – lägg till": "I own it – add it",
    "Hämtar från TMDB…": "Fetching from TMDB…", "Manus": "Writing", "Visa alla i samlingen": "Show all in the collection",
    "kommande": "upcoming",
    // Tittarhistorik
    "Tittarhistorik": "Viewing history", "Lägg till visning": "Add viewing", "Inga visningar sparade än.": "No viewings saved yet.",
    "Markerad i appen": "Marked in the app", "Från Letterboxd": "From Letterboxd", "Från Trakt": "From Trakt",
    // Musik
    "Låtlista": "Track list", "Okänd artist": "Unknown artist", "Skivbolag": "Label", "Katalognr": "Catalog no.", "Spår": "Tracks",
    "Speltid": "Playing time", "Låtlistan hämtas i bakgrunden…": "The track list is being fetched in the background…",
    "Hämta info igen": "Fetch info again", "Fel album?": "Wrong album?", "Info hämtad": "Info fetched", "Album": "Album", "Artist": "Artist",
    "Redigera album": "Edit album", "Katalognummer": "Catalog number", "Antal skivor": "Number of discs", "Antal spår": "Number of tracks",
    "Genre (flera med | emellan)": "Genre (separate several with |)", "Various = samlingsskiva": "Various = compilation",
    "Välj rätt album": "Choose the right album", "Inga träffar.": "No results.", "Kopplad till rätt album": "Linked to the right album",
    "Letar i dina samlingar, MusicBrainz och fler källor…": "Searching your collections, MusicBrainz and more sources…",
    "Flera utgåvor har samma streckkod – välj en annan nedan om det behövs.": "Several editions share this barcode – choose another below if needed.",
    "Inte rätt skiva? Sök nedan.": "Not the right disc? Search below.", "Sök på Discogs ↗": "Search on Discogs ↗",
    "Hittad!": "Found!", "Ny skiva": "New disc", "Lägg till den här?": "Add this one?", "Lägg till musik": "Add music",
    "Vald titel": "Selected title", "Valfritt": "Optional",
    "★ Lägg på önskelistan i stället": "★ Add to the wish list instead", "Fortsätt lägga till fler efter den här": "Keep adding more after this one",
    "Finns inte? Lägg till skivan för hand ›": "Not listed? Add the disc by hand ›", "Inga träffar. Prova en annan stavning.": "No results. Try another spelling.",
    "Lägg till skiva för hand": "Add a disc by hand", "Lägg till": "Add", "＋ Lägg till": "＋ Add", "Lägg till ›": "Add ›",
    "För skivor som inte finns i MusicBrainz eller Discogs. Du kan lägga till ett eget omslag efteråt.": "For discs that are not in MusicBrainz or Discogs. You can add your own cover afterwards.",
    "★ Lägg på önskelistan": "★ Add to the wish list",
    // Redigera
    "I samlingen": "In collection", "Såld": "Sold", "Mitt betyg (0–10)": "My rating (0–10)", "Inköpspris (kr)": "Purchase price",
    "Plats": "Location", "Säsong": "Season", "Serienamn (grupperar säsonger)": "Series name (groups seasons)",
    "Nyskick": "Mint", "Mycket bra": "Very good", "Bra": "Good", "Okej": "OK", "Dålig": "Poor",
    "Säljpris (kr)": "Asking price", "Köp om högst (kr)": "Buy for at most", "Skick och försäljning": "Condition and sale",
    "Skick": "Condition", "Om skicket": "About the condition", "Repor, saknat häfte, fel fodral…": "Scratches, missing booklet, wrong case…",
    "Sätt status till": "Set the status to", "så hamnar titeln på Säljlistan.": "and the title appears on the sale list.",
    "Vill uppgradera till": "Want to upgrade to", "Taggar (flera med komma emellan)": "Tags (separate several with commas)",
    "T.ex. Jul, Barnvänligt": "E.g. Christmas, Kids", "–": "–",
    // Uppdatera metadata
    "Uppdatera": "Update", "Återställ allt från TMDB": "Reset everything from TMDB",
    "Skriver över även titel, år och omslag med TMDB:s uppgifter. Plats, anteckningar, betyg och utlåning påverkas inte.": "Also overwrites title, year and cover with TMDB's data. Location, notes, rating and loans are not affected.",
    "Skriva över titel, år och omslag med uppgifter från TMDB?": "Overwrite title, year and cover with data from TMDB?",
    "Metadata uppdaterad": "Metadata updated",
    "Hämtar handling, skådespelare, regi, genre och omslag på nytt för alla titlar. Det du har ändrat själv behålls.": "Fetches plot, actors, director, genre and cover again for all titles. What you have changed yourself is kept.",
    "Skriver även över titlar, år och omslag du ändrat. Plats, anteckningar, betyg och utlåning påverkas inte.": "Also overwrites titles, years and covers you have changed. Location, notes, rating and loans are not affected.",
    "Uppdatering startad – följ förloppet i menyn": "Update started – follow the progress in the menu",
    "Körs i bakgrunden – du kan fortsätta använda appen.": "Runs in the background – you can keep using the app.", "Gäller": "Applies to",
    // Låna ut
    "Till vem": "To whom", "Ska vara tillbaka": "Due back",
    // Omslag
    "Välj omslag": "Choose cover", "Titeln är inte kopplad till TMDB än. Använd ”Fel film?” först.": "The title is not linked to TMDB yet. Use “Wrong movie?” first.",
    "TMDB har inga andra omslag för den här titeln.": "TMDB has no other covers for this title.", "Omslaget bytt": "Cover changed",
    "📷 Ta foto": "📷 Take photo", "🖼 Välj bild": "🖼 Choose image", "…eller klistra in en bildadress": "…or paste an image address",
    "Bilden sparas i appdata och skrivs aldrig över av ”Uppdatera metadata”. Fotografera rakt framifrån – i rutnätet visas omslaget beskuret till omslagsformat.": "The image is saved in appdata and never overwritten by “Update metadata”. Photograph straight from the front – the grid crops it to cover format.",
    "Eget omslag sparat": "Custom cover saved", "Importera omslag": "Import covers",
    "Välj många bilder på en gång, eller en zip-fil. Döp bilderna efter": "Choose many images at once, or a zip file. Name the images after the",
    "streckkod": "barcode", "titel": "title", ") eller": ") or", ", gärna med år (": ", ideally with the year (",
    "), så kopplas de till rätt film automatiskt.": "), and they are linked to the right movie automatically.",
    "Bara titlar som saknar omslag": "Only titles without a cover", "Hittade ingen film": "No movie found",
    "Flera möjliga filmer – lägg till året i filnamnet": "Several possible movies – add the year to the file name",
    "Kopplade": "Linked", "Hade redan omslag": "Already had a cover", "Välj rätt titel": "Choose the right title", "Kopplad till rätt titel": "Linked to the right title",
    // Skanna
    "Skanna eller sök": "Scan or search", "…eller skriv streckkoden": "…or type the barcode", "Rikta kameran mot streckkoden.": "Point the camera at the barcode.",
    "Skriv streckkodens siffror.": "Type the barcode digits.", "Kameran kräver": "The camera requires",
    "(eller localhost). Skriv streckkoden – eller titeln – ovan så länge.": "(or localhost). Type the barcode – or the title – above for now.",
    "Ingen kamera hittades på den här enheten. Skriv titel eller streckkod i fältet ovan.": "No camera was found on this device. Type a title or barcode in the field above.",
    "✓ Har": "✓ Owned", "Skannar mot": "Scanning into", "(välj en samling för att byta)": "(choose a collection to switch)",
    "Streckkod, album eller artist": "Barcode, album or artist", "Streckkod eller titel, t.ex. harry potter": "Barcode or title, e.g. harry potter",
    "Streckkod eller titel": "Barcode or title", "Streckkod eller album": "Barcode or album",
    "🎬 Film & serier": "🎬 Movies & series", "🎵 Musik": "🎵 Music", "🤝 Utlåning": "🤝 Lending",
    "Skanna i serie (kameran står kvar)": "Scan in a row (camera stays on)",
    "Skanna en skiva för att låna ut den – eller skanna en utlånad skiva för att markera den som återlämnad.": "Scan a disc to lend it – or scan a loaned disc to mark it as returned.",
    "Lånas ut till": "Lend to", "Namn": "Name", "Åter om": "Due in", "✓ Har redan:": "✓ Already owned:", "★ På önskelistan:": "★ On the wish list:",
    "↩ Återlämnad:": "↩ Returned:", "Skriv vem som lånar först": "Type who is borrowing first", "Okänd – sök på titel": "Unknown – search by title",
    "★ På din önskelista": "★ On your wish list", "Du har redan den här": "You already own this", "Nästa i kön": "Next in queue", "Skanna nästa": "Scan next",
    "Letar i dina samlingar, MyMovies och fler källor…": "Searching your collections, MyMovies and more sources…",
    "Sök streckkoden på nätet ↗": "Search the barcode online ↗", "Inte rätt film? Sök nedan.": "Not the right movie? Search below.", "Ny titel": "New title",
    "Titel (gärna med år, t.ex. Alien 1979)": "Title (ideally with the year, e.g. Alien 1979)", "Säsong (serier)": "Season (series)",
    "Har du många titlar? Klistra in en lista ›": "Many titles? Paste a list ›", "Inga träffar. Prova en annan titel.": "No results. Try another title.",
    "Ingen säsong angiven. Lägga till hela serien som en post?": "No season given. Add the whole series as one item?",
    "Lägg till flera": "Add several", "En titel per rad. Skriv gärna året efter titeln för säkrare träff, t.ex.": "One title per line. Adding the year after the title gives better matches, e.g.",
    "Appen föreslår en träff per rad som du kan byta eller bocka ur innan allt läggs till.": "The app suggests a match per line that you can change or untick before everything is added.",
    "Hitta träffar": "Find matches", "Ingen träff – prova annan stavning eller lägg till året": "No match – try another spelling or add the year",
    "Finns redan – hoppades över": "Already owned – skipped", "✓ Tillagd": "✓ Added", "★ Önskad": "★ Wanted", "✓ Tillagd:": "✓ Added:",
    // Inventering
    "Inventering": "Inventory", "Pågående:": "In progress:", "Visa resultat": "Show result", "Hela samlingen": "The whole collection",
    "alla platser": "all locations",
    "Skanna allt som står i hyllan. Sedan ser du vad som saknas – utlånat, felplacerat eller borta.": "Scan everything on the shelf. Then you see what is missing – loaned, misplaced or gone.",
    "Avsluta pågående inventering och starta en ny?": "Finish the current inventory and start a new one?", "Klar – visa vad som saknas": "Done – show what is missing",
    "Redan skannad:": "Already scanned:", "okänd plats": "unknown location", "Allt hittat! 🎉": "Everything found! 🎉",
    "Finns inte i samlingen. Tryck för att lägga till.": "Not in the collection. Tap to add.", "Skanna fler": "Scan more",
    "Inget är utlånat just nu.": "Nothing is loaned out right now.",
    // Statistik
    "Statistik": "Statistics", "Film & serier": "Movies & series", "Värde & dubbletter": "Value & duplicates", "Utveckling": "Growth",
    "Så har samlingen vuxit": "How the collection has grown", "Flest album av": "Most albums by", "Genrer": "Genres", "Årtionde": "Decade",
    "Ingen musik i samlingen än.": "No music in the collection yet.", "inköpspris totalt": "total purchase price", "har inköpspris": "have a purchase price",
    "i snitt per titel": "average per title", "skivor totalt": "discs in total",
    "Värdet räknas bara på titlar där du fyllt i inköpspris (Redigera → Inköpspris, eller från CLZ).": "The value only counts titles where you have entered a purchase price (Edit → Purchase price, or from CLZ).",
    "Dyraste": "Most expensive", "Samma film, säsong eller album mer än en gång – t.ex. både DVD och Blu-ray.": "The same movie, season or album more than once – e.g. both DVD and Blu-ray.",
    "Inga dubbletter. 👌": "No duplicates. 👌", "på önskelistan": "on the wish list", "utlånade": "loaned out", "Tillagda per år": "Added per year",
    "Flest filmer av": "Most movies by", "Platser": "Locations", "sedda": "watched", "samlingsskivor": "compilations", "artister": "artists",
    "timmar musik": "hours of music", "skivbolag": "labels", "Skivbolag ": "Labels",
    // Slumpa
    "🎲 Vad ska vi se?": "🎲 What should we watch?", "Vad som helst": "Anything", "Spelar ingen roll": "Doesn't matter", "Slumpa igen": "Pick again",
    "Slumpa!": "Pick!", "Bara osedda": "Only unwatched", "Max längd": "Max length", "Inget matchade. Prova färre filter.": "Nothing matched. Try fewer filters.",
    // Filmserier
    "Filmserier": "Movie collections", "Filmserie": "Movie collection",
    "Inga filmserier hittade än. De fylls på när omslagen hämtas.": "No movie collections found yet. They fill up as covers are fetched.",
    "Filmer som hör ihop enligt TMDB, t.ex. alla Bond-filmer. Tryck för att se vilka delar du saknar.": "Movies that belong together according to TMDB, e.g. all Bond movies. Tap to see which parts you are missing.",
    // Saknar omslag, bara digitalt, export
    "Album utan omslag": "Albums without a cover", "Saknar omslag": "Missing cover",
    "Album som inte hittades i MusicBrainz/Discogs. Tryck för att välja rätt album, eller lägg in ett eget omslag.": "Albums that were not found in MusicBrainz/Discogs. Tap to choose the right album, or add your own cover.",
    "Titlar som inte kunde matchas automatiskt. Tryck för att välja rätt film.": "Titles that could not be matched automatically. Tap to choose the right movie.",
    "Försök igen automatiskt": "Try again automatically", "Välj ›": "Choose ›", "Alla har omslag! 🎉": "Everything has a cover! 🎉",
    "Försöker igen i bakgrunden…": "Trying again in the background…", "någon samling": "any collection", "Bara digitalt": "Digital only",
    "Inget här – allt digitalt finns också på skiva, eller så är Plex/Jellyfin inte synkat än (Meny → Inställningar).": "Nothing here – everything digital is also on disc, or Plex/Jellyfin has not synced yet (Menu → Settings).",
    "Exportera samlingen": "Export the collection", "📄 CSV (kalkylark)": "📄 CSV (spreadsheet)",
    "Öppnas i Excel, Numbers eller Google Sheets. En rad per titel/album.": "Opens in Excel, Numbers or Google Sheets. One row per title/album.",
    "🧾 JSON (allt)": "🧾 JSON (everything)", "Alla fält, även låtlistor och extra uppgifter från CLZ.": "All fields, including track lists and extra data from CLZ.",
    "Vill du ha hela databasen? Använd Säkerhetskopior – där kan du ladda ner en .db-fil.": "Want the whole database? Use Backups – you can download a .db file there.",
    // Menyn
    "Uppdaterar metadata": "Updating metadata", "Hämtar omslag och filmserier": "Fetching covers and movie collections",
    "Hämtar låtlistor och skivomslag": "Fetching track lists and album covers", "Sparar omslag lokalt": "Saving covers locally",
    "Fyll i nyckeln": "Enter the key", "Film, serie, musik, lista eller import från CLZ": "Movie, series, music, list or import from CLZ",
    "Statistik, årsöversikt, filmserier, hyllkarta, inventering": "Statistics, year in review, movie collections, shelf map, inventory",
    "Lån och försäljning": "Loans and sales", "Utlånat, vänsida och säljlista": "Loaned out, friends page and sale list",
    "Säkerhetskopior, export, tittarhistorik, papperskorg": "Backups, export, viewing history, trash", "Inställningar": "Settings",
    "Språk, samlingar, TMDB, musik, Plex/Jellyfin, inloggning": "Language, collections, TMDB, music, Plex/Jellyfin, login",
    "filmer": "movies", "säsonger": "seasons", "album": "albums", "önskade": "wanted",
    "Film eller serie": "Movie or series", "Sök på titel": "Search by title", "Sök på artist och album": "Search by artist and album",
    "Skanna streckkoder": "Scan barcodes", "Med mobilkameran, en i taget eller i serie": "With the phone camera, one at a time or in a row",
    "Klistra in en lista": "Paste a list", "Många filmer på en gång": "Many movies at once", "Importera från CLZ": "Import from CLZ",
    "CLZ Movies eller CLZ Music (CSV)": "CLZ Movies or CLZ Music (CSV)", "Många bilder eller en zip på en gång": "Many images or a zip at once",
    "Värde, dubbletter och utveckling": "Value, duplicates and growth", "Årsöversikt": "Year in review", "Ditt år i Diskoteket": "Your year in Diskoteket",
    "Se vilka delar du saknar": "See which parts you are missing", "Hyllkarta": "Shelf map", "Platser med foto": "Locations with photos",
    "Skanna hyllan och se vad som saknas": "Scan the shelf and see what is missing", "Finns i Plex/Jellyfin men inte på skiva": "In Plex/Jellyfin but not on disc",
    "För filmer och serier i hela samlingen": "For movies and series in the whole collection",
    "Visar titlar utan omslag – kryssa bort filtret överst": "Showing titles without a cover – remove the filter at the top",
    "Utlånat": "Loaned out", "Vem har vad, och vad är försenat": "Who has what, and what is overdue", "Visa-sida för vänner": "Friends page",
    "Säljlista": "Sale list", "Annonstext till Tradera/Blocket": "Ad text for marketplaces", "CSV eller JSON": "CSV or JSON",
    "Importera från Letterboxd eller Trakt": "Import from Letterboxd or Trakt", "Papperskorgen": "Trash", "Säkerhetskopior": "Backups",
    "Ta en kopia eller återställ": "Make a copy or restore", "Allmänt": "General", "Språk, tema, visning, omslag och säkerhetskopior": "Language, theme, view, covers and backups",
    "TMDB": "TMDB", "Nyckel ifylld": "Key entered", "Nyckel saknas": "Key missing", "MusicBrainz och Discogs": "MusicBrainz and Discogs",
    "Streckkoder": "Barcodes", "MyMovies, UPCitemdb, EAN-DB": "MyMovies, UPCitemdb, EAN-DB", "Plex och Jellyfin": "Plex and Jellyfin",
    "Inte inställt": "Not set up", "Inloggning": "Login", "På – lösenord krävs": "On – password required",
    "Av – alla i nätverket kommer åt appen": "Off – everyone on the network can use the app", "Home Assistant": "Home Assistant",
    "Integration och kort": "Integration and card",
    // Import
    "Välj CSV-filen som du exporterat från": "Choose the CSV file you exported from", "eller": "or",
    "– appen känner själv igen vilken. Du kan importera samma fil igen: befintliga poster uppdateras, inget dubbleras och det du ändrat i Diskoteket behålls. Musik och film kan ligga i samma samling utan att krocka.": "– the app recognizes which one. You can import the same file again: existing items are updated, nothing is duplicated and what you changed in Diskoteket is kept. Music and movies can share a collection without clashing.",
    "Låtlistor och skivomslag hämtas nu i bakgrunden (några sekunder per skiva) – se menyn.": "Track lists and album covers are now fetched in the background (a few seconds per disc) – see the menu.",
    "Omslagen hämtas nu i bakgrunden – se menyn.": "The covers are now fetched in the background – see the menu.",
    // Säkerhetskopior
    "Inga kopior än.": "No copies yet.", "Ta en kopia nu": "Make a copy now", "⬆ Återställ från fil…": "⬆ Restore from file…", "Senaste": "Latest",
    "Kopia sparad": "Copy saved", "Säkerhetskopian är återställd": "The backup has been restored", "Tas automatiskt var": "Taken automatically every",
    "i appdata-mappen. Kopior som tas inför borttagning eller återställning sparas tills du själv tar bort dem.": "in the appdata folder. Copies taken before deleting or restoring are kept until you delete them yourself.",
    "Vid återställning tar appen först en kopia av nuvarande databas, så det går alltid att ångra. Kopior från äldre versioner av Diskoteket uppgraderas automatiskt. Lösenordet för inloggning påverkas inte.": "When restoring, the app first makes a copy of the current database, so it can always be undone. Copies from older versions of Diskoteket are upgraded automatically. The login password is not affected.",
    // Inställningar
    "Spara omslag lokalt i appdata": "Save covers locally in appdata", "Antal att spara": "Number to keep", "Språk i appen": "App language",
    "Standardspråk för nya enheter": "Default language for new devices",
    "Språket i appen sparas på den här enheten. Standardspråket gäller enheter som inte valt själva.": "The app language is saved on this device. The default language applies to devices that have not chosen one.",
    "Visning och tema…": "View and theme…", "Omslag": "Covers", "API Read Access Token": "API Read Access Token",
    "Klistra in din nyckel från themoviedb.org": "Paste your key from themoviedb.org", "Svenska": "Swedish", "Engelska": "English",
    "Norska": "Norwegian", "Danska": "Danish", "Finska": "Finnish", "Tyska": "German", "Testa nyckeln": "Test the key",
    "TMDB ger omslag, handling och sökning för filmer och serier. Gratis nyckel: themoviedb.org → Settings → API.": "TMDB provides covers, plots and search for movies and series. Free key: themoviedb.org → Settings → API.",
    "Språk för handling och titlar": "Language for plots and titles", "Slå upp i MusicBrainz (gratis, ingen nyckel)": "Look up in MusicBrainz (free, no key)",
    "Testa MusicBrainz": "Test MusicBrainz", "Discogs-nyckel (valfri)": "Discogs key (optional)", "Personal access token från discogs.com": "Personal access token from discogs.com",
    "Testa Discogs": "Test Discogs", "Discogs är bäst på ovanliga utgåvor och vinyl. Nyckel: logga in på discogs.com → Settings → Developers →": "Discogs is best for rare editions and vinyl. Key: log in to discogs.com → Settings → Developers →",
    "Gratis.": "Free.", "Slå upp i MyMovies (nordiska utgåvor)": "Look up in MyMovies (Nordic editions)",
    "Slå upp i UPCitemdb (amerikanska utgåvor, 100/dag)": "Look up in UPCitemdb (US editions, 100/day)", "EAN-DB-nyckel (valfri)": "EAN-DB key (optional)",
    "JWT-nyckel från ean-db.com": "JWT key from ean-db.com", "EAN-DB ger 250 gratis uppslag efter registrering. Koder du kopplar till en film kommer appen ihåg.": "EAN-DB gives 250 free lookups after registering. Codes you link to a movie are remembered.",
    "Adress": "Address", "Plex-token": "Plex token", "Testa Plex": "Test Plex",
    "Token: öppna en film i Plex webb → ⋯ → Hämta info → Visa XML. Den står sist i adressen (X-Plex-Token=…).": "Token: open a movie in Plex web → ⋯ → Get Info → View XML. It is at the end of the address (X-Plex-Token=…).",
    "API-nyckel": "API key", "Från Jellyfin": "From Jellyfin", "Testa Jellyfin": "Test Jellyfin", "Synka Plex/Jellyfin var X:e timme": "Sync Plex/Jellyfin every X hours",
    "Nyckel: Jellyfin → Kontrollpanel → API-nycklar → +.": "Key: Jellyfin → Dashboard → API Keys → +.", "Var X:e timme (0 = av)": "Every X hours (0 = off)",
    "Sparad": "Saved",
    // Inloggning
    "🔒 Inloggning är": "🔒 Login is", "Inloggning är": "Login is", "Nytt lösenord": "New password", "Välj ett lösenord": "Choose a password",
    "Byt lösenord": "Change password", "Slå på inloggning": "Turn on login", "Skriv det igen": "Type it again", "Stäng av inloggning": "Turn off login",
    "Logga ut": "Log out", "API-nyckel för Home Assistant": "API key for Home Assistant",
    "Klistra in den när du lägger till Diskoteket-integrationen i Home Assistant. Den ger bara läsrätt till sammanfattningen.": "Paste it when you add the Diskoteket integration in Home Assistant. It only gives read access to the summary.",
    "Skapa ny nyckel": "Create a new key", "Glömt lösenordet? Ta bort filen": "Forgot the password? Delete the file",
    "i appdata-mappen och starta om containern. Omslagsbilder visas utan inloggning, så att Home Assistant-kortet kan visa dem.": "in the appdata folder and restart the container. Cover images are shown without login, so the Home Assistant card can show them.",
    "i appdata-mappen och starta om containern.": "in the appdata folder and restart the container.",
    ". Den som öppnar appen måste skriva lösenordet (en gång per enhet).": ". Anyone opening the app must enter the password (once per device).",
    ". Alla som når adressen kan se och ändra samlingen. Slå på den om appen nås utanför hemmet, t.ex. via en reverse proxy för kamerans skull.": ". Anyone who can reach the address can see and change the collection. Turn it on if the app is reachable outside your home, e.g. via a reverse proxy for the camera.",
    "av": "off", "Minst 4 tecken.": "At least 4 characters.", "Lösenorden är inte lika.": "The passwords do not match.", "Lösenordet är bytt": "The password has been changed",
    "Inloggning påslagen – du är inloggad på den här enheten": "Login turned on – you are logged in on this device",
    "Stänga av inloggningen? Då kommer alla i nätverket åt appen utan lösenord.": "Turn off login? Then everyone on the network can use the app without a password.",
    "Inloggning avstängd": "Login turned off", "Skapa en ny nyckel? Den gamla slutar fungera, så du måste byta den i Home Assistant också.": "Create a new key? The old one stops working, so you must change it in Home Assistant too.",
    "Logga in – Diskoteket": "Log in – Diskoteket", "Logga in för att se samlingen.": "Log in to see the collection.", "Logga in": "Log in", "Lösenord": "Password",
    "Fel lösenord – försök igen.": "Wrong password – try again.",
    // Home Assistant
    "Integration och kort (rekommenderas)": "Integration and card (recommended)", "Anpassade arkiv": "Custom repositories", "Integration": "Integration",
    "som typ": "as type", "Sök på": "Search for", "i HACS, installera och starta om Home Assistant.": "in HACS, install it and restart Home Assistant.",
    "Inställningar → Enheter och tjänster → Lägg till integration → Diskoteket": "Settings → Devices & services → Add integration → Diskoteket",
    "· API-nyckel: se Meny → Inloggning": "· API key: see Menu → Settings → Login",
    "Starta om Home Assistant en gång till och ladda om sidan (Ctrl+F5, eller i mobilappen: Inställningar → Companion app → Felsökning → Återställ frontend-cache).": "Restart Home Assistant once more and reload the page (Ctrl+F5, or in the mobile app: Settings → Companion app → Troubleshooting → Reset frontend cache).",
    "Lägg till kortet": "Add the card", "på en instrumentpanel. Välj detaljnivå i kortets inställningar: kompakt, standard eller detaljerad. Hittar du det inte: lägg till ett manuellt kort med": "to a dashboard. Choose the level of detail in the card settings: compact, standard or detailed. Can't find it? Add a manual card with",
    "Integrationen ger sensorer för filmer, serier, album, osedda, önskelista, utlånat och försenade lån – som du kan använda i egna automationer.": "The integration provides sensors for movies, series, albums, unwatched, wish list, loaned out and overdue loans – which you can use in your own automations.",
    "Utan integration (REST-sensor)": "Without the integration (REST sensor)", "Lägg in i": "Add to", "och starta om Home Assistant.": "and restart Home Assistant.",
    "Adress:": "Address:",
    // Massredigering
    "– oförändrat –": "– unchanged –", "Flytta till samling": "Move to collection", "Inte sedd": "Not watched", "– ingen –": "– none –",
    "Lägg till taggar": "Add tags", "Ta bort taggar": "Remove tags", "Spara ändringar": "Save changes", "Flytta till papperskorgen": "Move to trash",
    "Bara det du ändrar här sparas. Ändringarna skrivs inte över av en ny CLZ-import.": "Only what you change here is saved. The changes are not overwritten by a new CLZ import.",
    // Papperskorg, sälj, platser
    "Papperskorgen är tom.": "The trash is empty.", "Töm papperskorgen nu": "Empty the trash now", "Borttagna titlar sparas i 30 dagar. Sedan töms de automatiskt.": "Deleted titles are kept for 30 days. Then they are removed automatically.",
    "Ta bort allt i papperskorgen för gott? Det går inte att ångra.": "Delete everything in the trash for good? This cannot be undone.",
    "Kopierad – klistra in i annonsen": "Copied – paste it into the ad", "Kopiera texten:": "Copy the text:", "Totalt begärt:": "Total asked:",
    "📋 Kopiera annonstext för allt": "📋 Copy ad text for everything", "Inget till salu just nu.": "Nothing for sale right now.",
    "Annonstexten passar Tradera, Blocket och Facebook Marketplace.": "The ad text works for eBay, Facebook Marketplace and similar sites.",
    "Titlar med status": "Titles with the status", "Markerad som såld": "Marked as sold", "skick ej angivet": "condition not given",
    "Kopiera annonstext": "Copy ad text",
    "Inga platser än.": "No locations yet.", "Ny plats": "New location", "T.ex. Hylla A, rad 3": "E.g. Shelf A, row 3", "Byt foto": "Change photo",
    "Lägg till foto": "Add photo", "Beskrivning": "Description", "T.ex. Vardagsrummet, vänstra hyllan": "E.g. Living room, left shelf",
    "Inget registrerat här.": "Nothing registered here.", "Nytt namn på platsen (alla titlar flyttas med):": "New name for the location (all titles move with it):",
    "Foto sparat": "Photo saved",
    "Dina platser med foto och beskrivning, så du hittar skivan fort. Platsen sätts under Redigera (eller för många på en gång med": "Your locations with a photo and description, so you find the disc fast. The location is set under Edit (or for many at once with",
    // Årsöversikt
    "Ditt år i": "Your year in", "nya i samlingen": "new in the collection", "inköpt för": "spent", "visningar": "viewings",
    "Sett per månad": "Watched per month", "Mest sedda genrer": "Most watched genres", "Mest sedda": "Most watched", "Nytt i samlingen": "New in the collection",
    "Dyraste köpen": "Most expensive purchases", "Flest nya album av": "Most new albums by",
    "Inga titlar med datum för när de lades till.": "No titles with a date for when they were added.",
    "nya per år ·": "new per year ·",
    // Vänsidan
    "📋 Kopiera länken": "📋 Copy the link", "Skapa ny länk": "Create a new link", "Stäng av": "Turn off", "Slå på vänsidan": "Turn on the friends page",
    "(borttagen)": "(deleted)", "Avböj": "Decline", "Inga förfrågningar.": "No requests.",
    "En hemlig länk där vänner kan bläddra i samlingen och be om att få låna – utan att kunna ändra något. De ser inte priser, anteckningar eller vem som lånat vad.": "A secret link where friends can browse the collection and ask to borrow – without being able to change anything. They don't see prices, notes or who has borrowed what.",
    "Ny länk = den gamla slutar fungera. Vänner utanför hemmet når bara sidan om appen går att nå utifrån.": "New link = the old one stops working. Friends outside your home only reach the page if the app is reachable from outside.",
    "Skapa en ny länk? Den gamla slutar fungera.": "Create a new link? The old one stops working.", "Utlånad – åter om 30 dagar": "Loaned – due back in 30 days", "Avböjd": "Declined",
    "Bläddra i samlingen och be om att få låna något.": "Browse the collection and ask to borrow something.", "Sök titel eller artist…": "Search title or artist…",
    "Länken fungerar inte längre.": "The link no longer works.", "★ Står på önskelistan – en present kanske?": "★ On the wish list – a present, maybe?",
    "Utlånad just nu – du kan ändå be om att få låna den sedan.": "Loaned out right now – you can still ask to borrow it later.",
    "Be om att få låna": "Ask to borrow", "Ditt namn": "Your name", "Meddelande (valfritt)": "Message (optional)", "T.ex. till helgen?": "E.g. for the weekend?",
    "Skicka förfrågan": "Send request", "Skickat! Ägaren ser din förfrågan i appen.": "Sent! The owner sees your request in the app.",
    "Det gick inte att skicka just nu.": "It could not be sent right now.",
    // Tittarhistorik-import
    "Hämta in när du sett filmerna. Bara filmer som finns i samlingen räknas.": "Bring in when you watched the movies. Only movies in the collection count.",
    "Exportera din historik som JSON (t.ex. med en exporttjänst för Trakt) och välj filen.": "Export your history as JSON (e.g. with an export service for Trakt) and choose the file.",
    "(eller": "(or", "Packa upp zip-filen och välj": "Unzip the file and choose",
    // Serverns meddelanden
    "Ange ett namn": "Enter a name", "Ogiltigt namn eller samling": "Invalid name or collection", "Samlingen finns inte": "The collection does not exist",
    "Namnet stämmer inte – inget togs bort": "The name does not match – nothing was deleted", "Okänd samling": "Unknown collection",
    "Inga titlar valda": "No titles selected", "Finns inte i papperskorgen": "Not in the trash", "Ogiltigt datum": "Invalid date",
    "Ingen fil vald": "No file selected", "Ange en plats": "Enter a location", "Välj plats och bild": "Choose location and image",
    "Titeln är inte kopplad till TMDB": "The title is not linked to TMDB", "Ingen trailer hittades": "No trailer found",
    "Hittade ingen med det namnet på TMDB": "Found nobody with that name on TMDB", "Länken fungerar inte längre": "The link no longer works",
    "Skriv ditt namn": "Type your name", "Hittade inte albumet": "Album not found",
    "Hittade inte albumet i MusicBrainz/Discogs – använd 'Fel album?' och välj rätt": "Album not found in MusicBrainz/Discogs – use 'Wrong album?' and choose the right one",
    "Hittade ingen matchning på TMDB – använd 'Fel film?' och välj rätt": "No match found on TMDB – use 'Wrong movie?' and choose the right one",
    "Ingen bild vald": "No image selected", "Inga filer valda": "No files selected",
    "Slå på MusicBrainz eller fyll i en Discogs-nyckel under Meny → Inställningar": "Turn on MusicBrainz or enter a Discogs key under Menu → Settings",
    "Välj ett album": "Choose an album", "Ange en titel": "Enter a title", "En hämtning pågår redan – vänta tills den är klar": "A fetch is already running – wait until it is done",
    "Inget matchade filtren": "Nothing matched the filters", "Okänd filmserie": "Unknown movie collection",
    "Ingen Plex- eller Jellyfin-server inställd – se Meny → Inställningar": "No Plex or Jellyfin server set up – see Menu → Settings",
    "Ogiltigt namn": "Invalid name", "En hämtning pågår i bakgrunden – vänta tills den är klar och försök igen": "A fetch is running in the background – wait until it is done and try again",
    "Fel lösenord": "Wrong password", "Okänt test": "Unknown test", "Omslaget finns inte": "The cover does not exist",
    "Adress eller nyckel saknas": "Address or key missing", "Fick inget svar – kontrollera nyckeln": "No answer – check the key", "Nyckel saknas ": "Key missing",
    "Du behöver logga in": "You need to log in", "Nyckeln fungerar": "The key works", "TMDB svarade: fel nyckel": "TMDB answered: wrong key",
    "Säkerhetskopian finns inte": "The backup does not exist", "Välj en säkerhetskopia eller en fil": "Choose a backup or a file",
    "Filen är ingen databas (välj en .db-fil från Diskoteket)": "The file is not a database (choose a .db file from Diskoteket)",
    "Filen är ingen databas som går att läsa": "The file is not a readable database", "Filen är en databas, men inte från Diskoteket": "The file is a database, but not from Diskoteket",
    "Databasen är skadad (integritetskontrollen misslyckades)": "The database is damaged (the integrity check failed)",
    "Lösenordet måste ha minst 4 tecken": "The password must be at least 4 characters",
    "TMDB-nyckel saknas – fyll i den under Meny → Inställningar": "TMDB key missing – enter it under Menu → Settings",
    "Det här ser inte ut som en export från Letterboxd (diary.csv eller watched.csv)": "This does not look like an export from Letterboxd (diary.csv or watched.csv)",
    "Filen är ingen JSON-export från Trakt": "The file is not a JSON export from Trakt", "Bilden är för stor (max 25 MB)": "The image is too large (max 25 MB)",
    "Filen är ingen bild som går att läsa (JPG, PNG eller WebP fungerar)": "The file is not a readable image (JPG, PNG or WebP work)",
    "Ange en adress som börjar med http:// eller https://": "Enter an address starting with http:// or https://",
    "Servern svarar inte – du är offline": "The server is not responding – you are offline",
    "Ingen kamera": "No camera",
    "IMDb-betyg – öppna på IMDb": "IMDb rating – open on IMDb", "IMDb-betyg": "IMDb rating",
    "TMDB-nyckel saknas – omslag och sökning för film fungerar inte.": "TMDB key missing – covers and movie search don't work.",
    "Sök i": "Search in", "Stäng": "Close", "Tillbaka": "Back", "Meny": "Menu", "hela samlingen": "the whole collection",
    "alla samlingar": "all collections",
    ". Alla som når adressen kan se och ändra samlingen. Slå på den om appen nås utanför hemmet, t.ex. via en reverse proxy för kamerans skull.": ". Anyone who can reach the address can see and change the collection. Turn it on if the app is reachable outside your home, e.g. via a reverse proxy for the camera.",
    ". Lägg till": ". Add",
    "Dina platser med foto och beskrivning, så du hittar skivan fort. Platsen sätts under Redigera (eller för många på en gång med": "Your locations with a photo and description, so you find the disc fast. The location is set under Edit (or for many at once with",
    ". Sätt pris och skick under Redigera, eller markera många med": ". Set price and condition under Edit, or select many with",
    "En hemlig länk där vänner kan bläddra i samlingen och be om att få låna – utan att kunna ändra något. De ser inte priser, anteckningar eller vem som lånat vad.": "A secret link where friends can browse the collection and ask to borrow – without being able to change anything. They don't see prices, notes or who has borrowed what.",
    ". Packa upp zip-filen och välj": ". Unzip the file and choose", "letterboxd.com → Settings → Import & Export →": "letterboxd.com → Settings → Import & Export →",
    "), så kopplas de till rätt film automatiskt.": "), and they are linked to the right movie automatically.",
    ". Appen föreslår en träff per rad som du kan byta eller bocka ur innan allt läggs till.": ". The app suggests a match per line that you can change or untick before everything is added.",
    ". Körs i bakgrunden – du kan fortsätta använda appen.": ". Runs in the background – you can keep using the app.",
    "Det du ändrat själv behålls.": "What you changed yourself is kept.",
    "Det du har ändrat själv behålls.": "What you have changed yourself is kept.",
    "Hämtar handling, skådespelare, regi, genre och omslag på nytt.": "Fetches plot, actors, director, genre and cover again.",
    "Plats, anteckningar, betyg och utlåning påverkas inte.": "Location, notes, rating and loans are not affected.",
    "(eller för många på en gång med": "(or for many at once with", ").": ").",
    "Alien 1979 Den enda vägen Heat (1995)": "Alien 1979\nThe Matrix\nHeat (1995)",
  },
  // Text med siffror, namn eller datum. $1, $2 … är det som matchade (översätts inte).
  patterns: [
    [/^(\d[\d\s]*) (titel|titlar)( · (\d[\d\s]*) kort)?$/, (m, n, w, rest, k) => `${n} ${w === "titel" ? "title" : "titles"}${rest ? ` · ${k} cards` : ""}`],
    [/^(\d[\d\s]*) album$/, "$1 albums"],
    [/^(\d+) (säsong|säsonger)$/, (m, n, w) => `${n} ${w === "säsong" ? "season" : "seasons"}`],
    [/^Säsong (\d+)$/, "Season $1"], [/^Skiva (\d+)$/, "Disc $1"],
    [/^Filter \((\d+)\)$/, "Filter ($1)"],
    [/^(\d+) (vald|valda)$/, "$1 selected"],
    [/^Du har (\d+) av (\d+)$/, "You own $1 of $2"],
    [/^Du har alla (\d+) säsonger\. 🎉$/, "You own all $1 seasons. 🎉"],
    [/^Saknade säsonger \((\d+) av (\d+)\)$/, "Missing seasons ($1 of $2)"],
    [/^(\d+) titlar(?: · (\d+) önskade)?$/, (m, a, b) => `${a} titles${b ? ` · ${b} wanted` : ""}`],
    [/^(\d+) st – skapa, byt namn, töm, ta bort$/, "$1 – create, rename, empty, delete"],
    [/^Samlingen ”(.+)” skapad$/, "Collection “$1” created"],
    [/^Sista chansen: (tömma|ta bort) ”(.+)”\?$/, (m, w, n) => `Last chance: ${w === "tömma" ? "empty" : "delete"} “${n}”?`],
    [/^(Tömd|Borttagen) – en säkerhetskopia sparades först$/, (m, w) => `${w === "Tömd" ? "Emptied" : "Deleted"} – a backup was saved first`],
    [/^Alla (\d+) titlar och album$/, "All $1 titles and albums"], [/^(\d+) titlar och album$/, "$1 titles and albums"],
    [/^Flytta "(.+)" till papperskorgen\?$/, "Move \"$1\" to the trash?"],
    [/^Flytta (\d+) titlar till papperskorgen\? Det går att ångra i 30 dagar\.$/, "Move $1 titles to the trash? It can be undone for 30 days."],
    [/^(\d+) flyttade till papperskorgen$/, "$1 moved to the trash"], [/^✓ (\d+) ändrade$/, "✓ $1 changed"],
    [/^Ändra (\d+) (titel|titlar)$/, (m, n, w) => `Change ${n} ${w === "titel" ? "title" : "titles"}`],
    [/^Papperskorgen \((\d+)\)$/, "Trash ($1)"], [/^(\d+) st – går att ångra$/, "$1 – can be undone"],
    [/^· borttagen (.+)$/, "· deleted $1"],
    [/^Säljlista \((\d+)\)$/, "Sale list ($1)"], [/^Pris: (\d+) kr$/, "Price: $1 kr"], [/^Skick: (.+)$/, "Condition: $1"],
    [/^Utlånat \((\d+)\)$/, "Loaned out ($1)"], [/^Utlånad till (.+)$/, "Loaned to $1"], [/^· utlånad till (.+)$/, "· loaned to $1"],
    [/^· utlånad till (.+) nu$/, "· loaned to $1 now"], [/^utlånad till (.+)$/, "loaned to $1"],
    [/^(försenad|åter) (\d{4}-\d\d-\d\d)$/, (m, w, d) => `${w === "åter" ? "due" : "overdue"} ${d}`],
    [/^sedan (.+)$/, "since $1"], [/^· åter (.+)$/, "· due $1"],
    [/^Låneförfrågningar \((\d+)\)$/, "Loan requests ($1)"], [/^(\d+) låneförfrågan$/, "$1 loan request"], [/^(\d+) låneförfrågningar$/, "$1 loan requests"],
    [/^(.+) vill låna (.+)$/, "$1 wants to borrow $2"],
    [/^Här står \((\d+)\)$/, "Here ($1)"], [/^(\d+) (titel|titlar)$/, (m, n, w) => `${n} ${w === "titel" ? "title" : "titles"}`],
    [/^Dubbletter \((\d+)\)$/, "Duplicates ($1)"], [/^Bara digitalt \((\d+)\)$/, "Digital only ($1)"],
    [/^Saknar omslag \((\d+)\)$/, "Missing cover ($1)"], [/^Album utan omslag \((\d+)\)$/, "Albums without a cover ($1)"],
    [/^(\d+) filmer\/serier$/, "$1 movies/series"], [/^(\d+) filmer\/serier · (\d+) album$/, "$1 movies/series · $2 albums"],
    [/^Senast (.+) · återställ$/, "Last $1 · restore"], [/^Diskoteket (\S+) · data i (.+)$/, "Diskoteket $1 · data in $2"],
    [/^(.+): (\d+) av (\d+)$/, (m, what, a, b) => `${tr(what)}: ${a} of ${b}`],
    [/^(\d+) (serier) \((\d+) säsonger\)$/, "$1 series ($3 seasons)"], [/^serier · (\d+) säsonger$/, "series · $1 seasons"],
    [/^(\d[\d\s]*) timmar \((\d+) dygn\)$/, "$1 hours ($2 days)"], [/^(\d+) av (\d+)$/, "$1 of $2"],
    [/^(\d+) h (\d+) min$/, "$1 h $2 min"], [/^(\d+) min$/, "$1 min"],
    [/^👁 Sedd (\d+) (gång|gånger) · senast (.+)$/, (m, n, w, d) => `👁 Watched ${n} ${n === "1" ? "time" : "times"} · last ${d}`],
    [/^✓ (\d+) tillagda (.*)$/, (m, n, rest) => `✓ ${n} added ${rest.replace(/· (\d+) kvar i kön/, "· $1 left in queue")}`],
    [/^✓ (\d+) (titel|titlar) tillagda$/, "✓ $1 added"], [/^Lägg till (\d+) (titel|titlar)$/, (m, n, w) => `Add ${n} ${w === "titel" ? "title" : "titles"}`],
    [/^Läser in (\d+) (fil|filer)…$/, "Reading $1 file(s)…"], [/^(\d+) omslag kopplade\.$/, "$1 covers linked."],
    [/^(\d+) omslag sparade \((.+) MB\)\. Lokala omslag gör att appen fungerar även om TMDB ligger nere\.$/, "$1 covers saved ($2 MB). Local covers keep the app working even if TMDB is down."],
    [/^(\d+) nya, (\d+) uppdaterade\.$/, "$1 new, $2 updated."],
    [/^(\d+) titlar hittade i samlingen, (\d+) nya visningar\.$/, "$1 titles found in the collection, $2 new viewings."],
    [/^(\d+) finns inte i samlingen, t\.ex\. (.+)\.$/, "$1 are not in the collection, e.g. $2."],
    [/^Återställd: (\d+) titlar\. Den gamla databasen sparades som$/, "Restored: $1 titles. The old database was saved as"],
    [/^Ersätta hela samlingen med kopian från (.+)\?([\s\S]*)$/, "Replace the whole collection with the copy from $1?\n\nThe current database is saved as a separate backup first."],
    [/^Ersätta hela samlingen med filen ”(.+)”\?([\s\S]*)$/, "Replace the whole collection with the file “$1”?\n\nThe current database is saved as a separate backup first."],
    [/^Finns redan i samlingen:\n([\s\S]*)\n\nLägga till ändå( \(t\.ex\. i ett annat format\))?\?$/, (m, list, f) => `Already in the collection:\n${list}\n\nAdd anyway${f ? " (e.g. in another format)" : ""}?`],
    [/^Streckkod (\d+)$/, "Barcode $1"], [/^Streckkod (\d+) · (.+)$/, "Barcode $1 · $2"],
    [/^Streckkod (\d+) · hittad via (.+)$/, "Barcode $1 · found via $2"], [/^Vald skiva · (.+)$/, "Selected disc · $1"],
    [/^Hittade: (.+)$/, "Found: $1"], [/^Okänd streckkod \(letade i (.+)\) – sök på titeln nedan\.$/, "Unknown barcode (searched $1) – search by title below."],
    [/^Okänd streckkod – sök på titeln nedan\.$/, "Unknown barcode – search by title below."],
    [/^Okänd streckkod \(letade i (.+)\) – sök på artist och album nedan\.$/, "Unknown barcode (searched $1) – search by artist and album below."],
    [/^Okänd streckkod (\d+) – finns inte i samlingen$/, "Unknown barcode $1 – not in the collection"], [/^Okänd streckkod (\d+)$/, "Unknown barcode $1"],
    [/^Ny: (\d+) – lagd i kön$/, "New: $1 – added to the queue"], [/^Att lägga till \((\d+)\)$/, "To add ($1)"],
    [/^En streckkod har 8–13 siffror – du skrev (\d+)\.$/, "A barcode has 8–13 digits – you typed $1."],
    [/^Kunde inte slå upp streckkoden: (.+)$/, "Could not look up the barcode: $1"],
    [/^Kunde inte starta kameran \((.+)\)\. Skriv titel eller streckkod i fältet ovan\.$/, "Could not start the camera ($1). Type a title or barcode in the field above."],
    [/^Inga träffar på ”(.+)”\. Prova en annan stavning\.$/, "No results for “$1”. Try another spelling."],
    [/^🤝 (.+) utlånad till (.+)$/, "🤝 $1 loaned to $2"], [/^⚠ står i (.+)$/, "⚠ located in $1"],
    [/^Inventering: (.+)$/, "Inventory: $1"], [/^Ny inventering i (.+)$/, "New inventory in $1"], [/^Resultat: (.+)$/, "Result: $1"],
    [/^(\d+) av (\d+) hittade · (\d+) saknas · (\d+) utlånade$/, "$1 of $2 found · $3 missing · $4 loaned out"],
    [/^av (\d+) hittade$/, "of $1 found"], [/^· (\d+) okända$/, "· $1 unknown"], [/^Saknas \((\d+)\)$/, "Missing ($1)"],
    [/^Utlånade \((\d+)\)$/, "Loaned out ($1)"], [/^Okända streckkoder \((\d+)\)$/, "Unknown barcodes ($1)"],
    [/^Skriva över titlar, år och omslag för ALLA titlar i (.+)\?$/, "Overwrite titles, years and covers for ALL titles in $1?"],
    [/^Tas automatiskt var (.+):e timme och sparas i$/, "Taken automatically every $1 hours and saved in"],
    [/^Sparad \((.+)\) – lämna tomt för att behålla$/, "Saved ($1) – leave empty to keep"],
    [/^Hittade (\d+) titlar$/, "Found $1 titles"], [/^Fungerar \((.+)\)$/, "Works ($1)"], [/^TMDB svarade (\d+)$/, "TMDB answered $1"],
    [/^Kunde inte nå TMDB: (.+)$/, "Could not reach TMDB: $1"], [/^Serverfel: (.+)$/, "Server error: $1"],
    [/^Rad (\d+): (.+)$/, "Row $1: $2"],
    [/^Finns i Plex\/Jellyfin men inte på skiva i (.+)\. Tryck ★ för att lägga den på önskelistan\.$/, "In Plex/Jellyfin but not on disc in $1. Tap ★ to add it to the wish list."],
    [/^Din data är din\. Ladda ner (.+) som fil – till ett kalkylark, en annan app eller bara för att ha en kopia\.$/, "Your data is yours. Download $1 as a file – to a spreadsheet, another app or just to have a copy."],
    [/^I Sverige, enligt JustWatch(.*)$/, "In Sweden, according to JustWatch$1"],
    [/^★ (.+) på önskelistan$/, "★ $1 on the wish list"], [/^★ Säsong (\d+) på önskelistan$/, "★ Season $1 on the wish list"],
    [/^Utlånad till (.+) · åter (.+)$/, "Loaned to $1 · due $2"], [/^Släpps (.+)$/, "Released $1"],
    [/^Totalt begärt: (.+)$/, "Total asked: $1"], [/^(\d+) totalt$/, "$1 total"], [/^Det du ändrat själv(.*) behålls\.$/, "What you changed yourself$1 is kept."],
    [/^Hämtar handling, skådespelare, regi, genre och omslag på nytt\. Det du ändrat själv(.*) behålls\.$/, "Fetches plot, actors, director, genre and cover again. What you changed yourself$1 is kept."],
    [/^· första: (.+) \((.+)\)$/, "· first: $1 ($2)"], [/^(\d+) olika titlar · (\d+) timmar(.*)$/, (m, a, b, rest) => `${a} different titles · ${b} hours${rest.replace(/· första: (.+) \((.+)\)/, "· first: $1 ($2)")}`],
    [/^Inga visningar sparade för (\d+)\. Markera filmer som sedda, eller importera från Letterboxd\/Trakt \(Meny → Tittarhistorik\)\.$/, "No viewings saved for $1. Mark movies as watched, or import from Letterboxd/Trakt (Menu → Data → Viewing history)."],
    [/^(\d+) titlar saknar datum och räknas inte$/, "$1 titles have no date and are not counted"], [/^· (\d+) titlar saknar datum och räknas inte$/, "· $1 titles have no date and are not counted"],
    [/^Släpps på skiva (.+)$/, "Released on disc $1"],
    [/^(\d+) på önskelistan$/, "$1 on the wish list"],
    [/^Regi: (.+)$/, "Director: $1"],
    [/^Ändrat av dig \(skrivs inte över\): (.+)$/, (m, list) => `Changed by you (not overwritten): ${list.split(", ").map((w) => EN.fields[w] || w).join(", ")}`],
    [/^Din data är din\. Ladda ner (.+) som fil – till ett kalkylark, en annan app eller bara för att ha en kopia\.$/, "Your data is yours. Download $1 as a file – to a spreadsheet, another app or just to have a copy."],
    [/^Gäller (.+)\.$/, "Applies to $1."],
  ],
  // Fältnamn i "Ändrat av dig"
  fields: { titel: "title", "år": "year", omslag: "cover", handling: "plot", serienamn: "series name", "säsong": "season", plats: "location",
    format: "format", "utgåva": "edition", anteckningar: "notes", betyg: "rating", sedd: "watched", streckkod: "barcode", pris: "price",
    status: "status", genre: "genre", "skådespelare": "actors", regi: "director", "längd": "length", originaltitel: "original title",
    "utlåning": "loan", tillagd: "added", artist: "artist", skivbolag: "label", katalognummer: "catalog number", "antal spår": "tracks",
    "antal skivor": "discs", skick: "condition", "om skicket": "condition notes", taggar: "tags", "säljpris": "asking price",
    maxpris: "max price", uppgradering: "upgrade" },
  // Ord för ord – används bara när ALLA ord i en text finns här (t.ex. ”3 filmer · 2 säsonger”)
  words: {
    titlar: "titles", titel: "title", filmer: "movies", film: "movie", serier: "series", serie: "series", "säsong": "season",
    "säsonger": "seasons", album: "albums", skivor: "discs", skiva: "disc", "spår": "tracks", kort: "cards", timmar: "hours", dygn: "days",
    min: "min", kr: "kr", st: "", sedda: "watched", osedda: "unwatched", "önskade": "wanted", "utlånade": "loaned out", "utlånad": "loaned out",
    tillagda: "added", nya: "new", uppdaterade: "updated", av: "of", och: "and", i: "in", artister: "artists", samlingsskivor: "compilations",
    visningar: "viewings", "gång": "time", "gånger": "times", dagar: "days", h: "h", senast: "last", totalt: "total", "ändrade": "changed",
    valda: "selected", vald: "selected", kvar: "left", "kön": "queue", hittade: "found", saknas: "missing", regi: "director",
    sedd: "watched", omslag: "covers", sparade: "saved", mb: "MB", "önskelistan": "the wish list", "på": "on", "inköpsvärde": "purchase value",
    skivbolag: "labels", "årtionde": "decade", "dubbletter": "duplicates", digital: "digital", cd: "CD", vinyl: "vinyl", dvd: "DVD",
    kassett: "cassette", "blu": "Blu", ray: "ray", uhd: "UHD", k: "K", vhs: "VHS", okänd: "unknown",
  },
};

const DICT = { en: EN }[I18N.lang] || null;
const WORD = /[A-Za-zÅÄÖåäöéÉ]+/g;

function byWords(core) {
  const words = core.match(WORD) || [];
  if (!words.length || !words.every((w) => w.toLowerCase() in DICT.words)) return undefined;
  return core.replace(WORD, (w) => {
    const t = DICT.words[w.toLowerCase()];
    return t && w[0] !== w[0].toLowerCase() ? t[0].toUpperCase() + t.slice(1) : t;
  }).replace(/\s{2,}/g, " ");
}

// Översätt en text (behåller mellanslag runt omkring)
function tr(text) {
  if (!DICT || !text || !/[A-Za-zÅÄÖåäö]/.test(text)) return text;
  const m = /^(\s*)([\s\S]*?)(\s*)$/.exec(text);
  const core = m[2].includes("\n") ? m[2].replace(/\s+/g, " ") : m[2]; // radbrytningar från koden räknas som mellanslag
  let out = DICT.exact[core];
  if (out === undefined) {
    for (const [re, rep] of DICT.patterns) {
      if (re.test(core)) { out = core.replace(re, rep); break; }
    }
  }
  if (out === undefined && core.endsWith(":") && DICT.exact[core.slice(0, -1)] !== undefined) out = DICT.exact[core.slice(0, -1)] + ":";
  if (out === undefined) out = byWords(core);
  return out === undefined ? text : m[1] + out + m[3];
}

// Sådant som aldrig översätts: titlar, handling, namn, låtar, egna anteckningar, sökfält
const SKIP = ".t, .s, .li-title, .hero h2, .plot, .tracklist, a.person, .chip.tag, .ct, .cs, .key, pre, code, textarea, [data-nt], #lib-name";

function translateNode(node) {
  const p = node.parentElement;
  if (!p || p.closest(SKIP) || p.closest("script, style")) return;
  const t = tr(node.nodeValue);
  if (t !== node.nodeValue) node.nodeValue = t;
}

function translateTree(root) {
  if (!DICT) return;
  if (root.nodeType === 3) return translateNode(root);
  if (root.nodeType !== 1 || root.closest?.(SKIP)) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) translateNode(n);
  const els = root.matches?.("[placeholder],[title],[aria-label]") ? [root] : [];
  for (const el of [...els, ...root.querySelectorAll("[placeholder],[title],[aria-label]")]) {
    for (const a of ["placeholder", "title", "aria-label"]) {
      const v = el.getAttribute(a);
      if (v) { const t = tr(v); if (t !== v) el.setAttribute(a, t); }
    }
  }
}

if (DICT) {
  const native = { confirm: window.confirm.bind(window), alert: window.alert.bind(window), prompt: window.prompt.bind(window) };
  window.confirm = (msg) => native.confirm(tr(String(msg)));
  window.alert = (msg) => native.alert(tr(String(msg)));
  window.prompt = (msg, def) => native.prompt(tr(String(msg)), def);
  document.title = tr(document.title);
  const start = () => {
    translateTree(document.body);
    new MutationObserver((muts) => {
      for (const m of muts) {
        if (m.type === "characterData") translateNode(m.target);
        else if (m.type === "attributes") translateTree(m.target);
        else m.addedNodes.forEach(translateTree);
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ["placeholder", "title", "aria-label"] });
  };
  if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);
}
