#!/bin/bash
# Bygger Diskoteket på Unraid och lägger in mallen så att den syns under Docker → Add Container.
# Kör i Unraids terminal:  bash /mnt/user/appdata/diskoteket-kod/unraid/install.sh
set -e
cd "$(dirname "$0")/.."
echo "Bygger avbilden diskoteket:latest …"
docker build -t diskoteket:latest .
mkdir -p /boot/config/plugins/dockerMan/templates-user
cp unraid/my-Diskoteket.xml /boot/config/plugins/dockerMan/templates-user/my-Diskoteket.xml
mkdir -p /mnt/user/appdata/diskoteket
echo
echo "Klart!"
echo " - Första gången: Docker → Add Container → välj mallen 'Diskoteket' → Apply."
echo " - Uppdatering: kör det här skriptet igen och välj sedan Edit → Apply på containern."
