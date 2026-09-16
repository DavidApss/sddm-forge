#!/bin/bash
set -e
MARK="# pop-cosmic-reveal: force monitor arrangement"
if grep -q "$MARK" /usr/share/sddm/scripts/Xsetup; then
    echo "ja aplicado, nada a fazer"
    exit 0
fi
cat >> /usr/share/sddm/scripts/Xsetup <<EOF

$MARK
# The auto-arrange logic above tiles outputs in whatever order xrandr
# reports them, which doesn't necessarily match the layout saved in the
# user's COSMIC desktop (a separate, Wayland-only config it can't see).
# This re-applies the known-correct positions afterwards. Delete this
# block to go back to auto-arrange-only.
if [ "\$(id -u)" = '0' ]; then
    xrandr --output HDMI-A-2 --pos 0x0 --primary --output DP-3 --pos 1920x0 2>/dev/null || true
fi
EOF
echo "OK - bloco adicionado ao fim de /usr/share/sddm/scripts/Xsetup"
