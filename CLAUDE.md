# Diskoteket – anteckningar för Claude

- Ägaren skriver på svenska. All text i appen, koden (kommentarer) och dokumentationen är på svenska.
- **Bygg inte en ny version utan att fråga.** Samla önskemål i en numrerad lista och bekräfta tolkningen; bygg först när ägaren säger till.
- Önskemål, status och saker att följa upp står i `ONSKELISTA.md` – läs den först och håll den uppdaterad.
- Appen körs i Docker på Unraid via mallen i `unraid/diskoteket.xml` (`ghcr.io/claudemicro222-cmd/diskoteket:latest`).
  Varje push till `main` bygger en ny avbild via `.github/workflows/docker.yml`.
- All data ligger i `/config` (= `/mnt/user/appdata/diskoteket`). Databasen uppgraderas automatiskt i `app/db.py` –
  ändringar i schemat måste fungera på en befintlig databas utan dataförlust.
- Inställningar sparas i databasen (inställningssidan), inte i `.env`.
- Fält som ägaren ändrar i appen låses (`locked`) och får aldrig skrivas över av CLZ-import eller ”Uppdatera metadata”.
- Ingen byggprocess för webbsidan: `app/static/app.js`, `style.css`, `index.html` är vanliga filer.
- Testa före push: starta servern lokalt mot en kopia av en gammal databas, kör API-anrop och klicka igenom i en headless-webbläsare.
