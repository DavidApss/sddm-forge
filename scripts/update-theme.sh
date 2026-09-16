#!/bin/bash
# Re-syncs the installed theme from the repo after editing Main.qml or assets.
set -e
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_DIR/theme/pop-cosmic-reveal"
DEST=/usr/share/sddm/themes/pop-cosmic-reveal

cp "$SRC/Main.qml" "$DEST/Main.qml"
cp "$SRC/assets/"*.png "$SRC/assets/"*.mp4 "$DEST/assets/"
chown -R root:root "$DEST"
chmod -R go+rX "$DEST"
echo "OK"
