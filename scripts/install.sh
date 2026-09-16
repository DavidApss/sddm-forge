#!/bin/bash
# Full (re)install: theme + PopGreeterActions plugin + revert script +
# sudoers rule. Run once, or after `git clone` on a fresh machine.
# The plugin must already be built (qmake && make in plugin/PopGreeterActions).
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_DIR/theme/pop-cosmic-reveal"
PLUGIN_SRC="$REPO_DIR/plugin/PopGreeterActions"
THEME_DEST=/usr/share/sddm/themes/pop-cosmic-reveal
QML_DEST="$(qmake -query QT_INSTALL_QML)/PopGreeterActions"

# --- theme ---------------------------------------------------------
rm -rf "$THEME_DEST"
mkdir -p "$THEME_DEST"
cp "$SRC/Main.qml" "$SRC/theme.conf" "$SRC/metadata.desktop" "$THEME_DEST/"
cp -r "$SRC/assets" "$THEME_DEST/"
chown -R root:root "$THEME_DEST"
chmod -R go+rX "$THEME_DEST"

mkdir -p /etc/sddm.conf.d
cat > /etc/sddm.conf.d/10-pop-cosmic-reveal.conf <<'EOF'
[Theme]
Current=pop-cosmic-reveal
EOF

# --- QML plugin ------------------------------------------------------
mkdir -p "$QML_DEST"
cp "$PLUGIN_SRC/libpopgreeteractionsplugin.so" "$PLUGIN_SRC/qmldir" "$QML_DEST/"
chown -R root:root "$QML_DEST"
chmod -R go+rX "$QML_DEST"

# --- revert script -----------------------------------------------------
install -o root -g root -m 0700 "$REPO_DIR/scripts/pop-revert-to-cosmic.sh" /usr/local/sbin/pop-revert-to-cosmic.sh

# --- sudoers rule, scoped to that one script for the sddm user only ----
cat > /tmp/pop-sddm-revert.sudoers <<'EOF'
sddm ALL=(root) NOPASSWD: /usr/local/sbin/pop-revert-to-cosmic.sh
EOF
visudo -c -f /tmp/pop-sddm-revert.sudoers
install -o root -g root -m 0440 /tmp/pop-sddm-revert.sudoers /etc/sudoers.d/pop-sddm-revert
rm -f /tmp/pop-sddm-revert.sudoers
visudo -c

echo "OK - tema instalado em $THEME_DEST"
echo "OK - plugin instalado em $QML_DEST"
echo "OK - script de revert em /usr/local/sbin/pop-revert-to-cosmic.sh"
echo "OK - regra sudoers validada e instalada"
echo "O cosmic-greeter continua sendo o login ativo. Nada muda no boot ate voce trocar com dpkg-reconfigure sddm."
