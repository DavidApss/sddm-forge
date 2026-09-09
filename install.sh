#!/usr/bin/env bash
# Instala o sddm-forge para o usuário atual (sem root).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/sddm-forge"
BIN_DIR="$HOME/.local/bin"
APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

echo ":: Instalando pacote em $DATA_DIR"
mkdir -p "$DATA_DIR"
rm -rf "$DATA_DIR/sddmforge" "$DATA_DIR/theme"
cp -a "$REPO_DIR/sddmforge" "$DATA_DIR/"
cp -a "$REPO_DIR/theme" "$DATA_DIR/"

echo ":: Instalando launcher em $BIN_DIR/sddm-forge"
mkdir -p "$BIN_DIR"
install -m755 "$REPO_DIR/bin/sddm-forge" "$BIN_DIR/sddm-forge"

echo ":: Instalando lançador .desktop"
mkdir -p "$APP_DIR"
install -m644 "$REPO_DIR/data/br.com.maia.SddmForge.desktop" \
    "$APP_DIR/br.com.maia.SddmForge.desktop"
update-desktop-database "$APP_DIR" 2>/dev/null || true

echo
echo ":: Pronto."
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) echo "   Aviso: $BIN_DIR não está no PATH." ;;
esac

MISSING=()
for pkg in gtk4 libadwaita python3-gobject python3-pyside6 sddm polkit; do
    rpm -q "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
done
rpm -q ffmpeg ffmpeg-free >/dev/null 2>&1 || MISSING+=("ffmpeg")
if ((${#MISSING[@]})); then
    echo "   Dependências faltando: ${MISSING[*]}"
    echo "   sudo dnf install ${MISSING[*]}"
    echo "   (python3-pyside6 = prévia embutida; ffmpeg = frame do vídeo na prévia)"
fi
