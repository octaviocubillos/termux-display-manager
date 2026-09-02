#!/usr/bin/env bash
# ==============================================================================
# 🪟 [TDM] Instalador específico para i3 Window Manager
# ==============================================================================
set -e
export DEBIAN_FRONTEND=noninteractive
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:10:Preparando paquetes de i3]"
echo "🪟 [TDM] Instalando i3 Window Manager..."

SUDO=""
if [ "$(id -u)" -ne 0 ] && [ ! -d "/data/data/com.termux" ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; elif command -v doas >/dev/null 2>&1; then SUDO="doas"; fi
fi

if command -v pkg >/dev/null 2>&1; then
    pkg install -y x11-repo || true
    pkg update -y || true
    echo "[TDM_PROGRESS:60:Instalando paquetes de i3]"
    pkg install -y i3 i3status dmenu aterm || true
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    $SUDO apk update || true
    $SUDO apk add i3wm i3status dmenu xterm || true
elif command -v apt-get >/dev/null 2>&1; then
    $SUDO apt-get update -y || true
    $SUDO apt-get install -y i3 i3status dmenu xterm || true
elif command -v pacman >/dev/null 2>&1; then
    $SUDO pacman -Sy --noconfirm i3-wm i3status dmenu xterm || true
elif command -v dnf >/dev/null 2>&1; then
    $SUDO dnf install -y i3 i3status dmenu xterm || true
fi

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$DIR/configure.sh" ]; then
    bash "$DIR/configure.sh" || true
fi

echo "[TDM_PROGRESS:100:i3 instalado con éxito]"
echo "✅ [TDM] Instalación de i3 Window Manager completada."
