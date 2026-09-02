#!/usr/bin/env bash
# ==============================================================================
# ❄️ [TDM] Instalador específico para KDE Plasma Desktop
# ==============================================================================
set -e
export DEBIAN_FRONTEND=noninteractive
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:10:Preparando paquetes de KDE Plasma]"
echo "❄️ [TDM] Instalando KDE Plasma Desktop..."

SUDO=""
if [ "$(id -u)" -ne 0 ] && [ ! -d "/data/data/com.termux" ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; elif command -v doas >/dev/null 2>&1; then SUDO="doas"; fi
fi

if command -v pkg >/dev/null 2>&1; then
    pkg install -y x11-repo || true
    pkg update -y || true
    echo "[TDM_PROGRESS:60:Instalando plasma-desktop, konsole, dolphin]"
    pkg install -y plasma-desktop plasma-workspace breeze konsole dolphin || true
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    $SUDO apk update || true
    $SUDO apk add plasma-desktop plasma-workspace konsole dolphin || true
elif command -v apt-get >/dev/null 2>&1; then
    $SUDO apt-get update -y || true
    $SUDO apt-get install -y plasma-desktop plasma-workspace breeze konsole dolphin || true
elif command -v pacman >/dev/null 2>&1; then
    $SUDO pacman -Sy --noconfirm plasma-desktop plasma-workspace konsole dolphin breeze || true
elif command -v dnf >/dev/null 2>&1; then
    $SUDO dnf install -y @kde-desktop-environment || true
fi

echo "[TDM_PROGRESS:100:KDE Plasma instalado con éxito]"
echo "✅ [TDM] Instalación de KDE Plasma completada."
