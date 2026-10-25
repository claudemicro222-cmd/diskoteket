#!/bin/sh
# Startar Diskoteket som Unraids standardanvändare (99:100), så att filerna i appdata
# går att läsa och ändra via nätverket utan behörighetsstrul.
set -e
PUID="${PUID:-99}"
PGID="${PGID:-100}"
umask "${UMASK:-002}"
mkdir -p /config

CMD="uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips=*"

if [ "$(id -u)" = "0" ]; then
  chown -R "$PUID:$PGID" /config 2>/dev/null || echo "Varning: kunde inte ändra ägare på /config"
  if command -v setpriv >/dev/null 2>&1; then
    echo "Diskoteket startar som användare $PUID:$PGID, data i /config"
    exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups $CMD
  fi
  echo "Varning: setpriv saknas, kör som root"
fi
exec $CMD
