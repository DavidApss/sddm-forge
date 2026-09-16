#!/usr/bin/env bash
# Installs sddm-forge for the current user (no root).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sddm-forge"
BIN_DIR="$HOME/.local/bin"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

echo ":: Installing package to $DATA_DIR"
mkdir -p "$DATA_DIR"
rm -rf "$DATA_DIR/sddmforge" "$DATA_DIR/theme"
cp -a "$REPO_DIR/sddmforge" "$DATA_DIR/"
cp -a "$REPO_DIR/theme" "$DATA_DIR/"

echo ":: Installing launcher to $BIN_DIR/sddm-forge"
mkdir -p "$BIN_DIR"
install -m755 "$REPO_DIR/bin/sddm-forge" "$BIN_DIR/sddm-forge"

echo ":: Installing .desktop entry"
mkdir -p "$APP_DIR"
install -m644 "$REPO_DIR/data/br.com.maia.SddmForge.desktop" \
    "$APP_DIR/br.com.maia.SddmForge.desktop"
update-desktop-database "$APP_DIR" 2>/dev/null || true

echo
echo ":: Done."
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "   Warning: $BIN_DIR is not on PATH." ;;
esac

if command -v dpkg >/dev/null 2>&1; then
    # Debian/Ubuntu/Pop!_OS
    MISSING=()
    for pkg in gir1.2-gtk-4.0 gir1.2-adw-1 python3-gi sddm policykit-1 ffmpeg; do
        dpkg -s "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
    done
    if ((${#MISSING[@]})); then
        echo "   Missing dependencies: ${MISSING[*]}"
        echo "   sudo apt install ${MISSING[*]}"
        echo "   (PySide6 for the embedded preview isn't packaged for apt; install it"
        echo "   with 'pip install --user PySide6' if you want it, or just use the"
        echo "   Full screen button, which doesn't need it. ffmpeg = video frame in"
        echo "   the preview.)"
    fi
elif command -v rpm >/dev/null 2>&1; then
    # Fedora and friends
    MISSING=()
    for pkg in gtk4 libadwaita python3-gobject python3-pyside6 sddm polkit; do
        rpm -q "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
    done
    rpm -q ffmpeg ffmpeg-free >/dev/null 2>&1 || MISSING+=("ffmpeg")
    if ((${#MISSING[@]})); then
        echo "   Missing dependencies: ${MISSING[*]}"
        echo "   sudo dnf install ${MISSING[*]}"
        echo "   (python3-pyside6 = embedded preview; ffmpeg = video frame in the preview)"
    fi
else
    echo "   Unrecognized package manager: install gtk4, libadwaita, the GObject"
    echo "   introspection bindings for both, python3-gi, sddm, polkit and ffmpeg"
    echo "   with your distro's tools."
fi
