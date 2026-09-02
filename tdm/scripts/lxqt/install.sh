#!/usr/bin/env bash
# ==============================================================================
# 🚀 [TDM] Instalador específico para LXQt
# ==============================================================================
set -e
export DEBIAN_FRONTEND=noninteractive
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:10:Preparando paquetes de LXQt]"
echo "🚀 [TDM] Instalando LXQt..."

SUDO=""
if [ "$(id -u)" -ne 0 ] && [ ! -d "/data/data/com.termux" ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; elif command -v doas >/dev/null 2>&1; then SUDO="doas"; fi
fi

if command -v pkg >/dev/null 2>&1; then
    pkg install -y x11-repo || true
    pkg update -y || true
    echo "[TDM_PROGRESS:60:Instalando paquetes de LXQt, audio y batería]"
    pkg install -y lxqt lxqt-session qterminal pcmanfm-qt lxqt-powermanagement pavucontrol pulseaudio || {
        for p in lxqt lxqt-session qterminal pcmanfm-qt lxqt-powermanagement pavucontrol pulseaudio; do pkg install -y "$p" || true; done
    }
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    $SUDO apk update || true
    $SUDO apk add lxqt-desktop lxqt-session qterminal pcmanfm-qt || true
elif command -v apt-get >/dev/null 2>&1; then
    $SUDO apt-get update -y || true
    $SUDO apt-get install -y lxqt lxqt-session qterminal pcmanfm-qt || true
elif command -v pacman >/dev/null 2>&1; then
    $SUDO pacman -Sy --noconfirm lxqt qterminal pcmanfm-qt || true
elif command -v dnf >/dev/null 2>&1; then
    $SUDO dnf install -y @lxqt-desktop-environment || true
fi

echo "[TDM_PROGRESS:100:LXQt instalado con éxito]"
echo "✅ [TDM] Instalación de LXQt completada."
