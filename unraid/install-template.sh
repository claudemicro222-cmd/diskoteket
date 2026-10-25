#!/bin/bash
# Lägger in Diskotekets mall i Unraid så att den syns under Docker → Add Container → Template.
# Kör i Unraids terminal:
#   curl -fsSL https://raw.githubusercontent.com/claudemicro222-cmd/diskoteket/main/unraid/install-template.sh | bash
set -e
DEST=/boot/config/plugins/dockerMan/templates-user/my-Diskoteket.xml
curl -fsSL https://raw.githubusercontent.com/claudemicro222-cmd/diskoteket/main/unraid/diskoteket.xml -o "$DEST"
mkdir -p /mnt/user/appdata/diskoteket
echo "Klart! Gå till Docker → Add Container → Template → välj 'Diskoteket' → Apply."
