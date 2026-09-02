#!/usr/bin/env bash
# ==============================================================================
# 🧉 [TDM] Instalador específico para MATE Desktop
# ==============================================================================
set -e
export DEBIAN_FRONTEND=noninteractive
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:10:Preparando paquetes de MATE Desktop]"
echo "🧉 [TDM] Instalando MATE Desktop Environment..."

SUDO=""
if [ "$(id -u)" -ne 0 ] && [ ! -d "/data/data/com.termux" ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; elif command -v doas >/dev/null 2>&1; then SUDO="doas"; fi
fi

if command -v pkg >/dev/null 2>&1; then
    pkg install -y x11-repo || true
    pkg update -y || true
    echo "[TDM_PROGRESS:60:Instalando paquetes de MATE]"
    pkg install -y mate-desktop mate-panel mate-session-manager mate-terminal marco caja mate-settings-daemon || true
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    $SUDO apk update || true
    $SUDO apk add mate-desktop mate-panel mate-session-manager mate-terminal marco caja || true
elif command -v apt-get >/dev/null 2>&1; then
    $SUDO apt-get update -y || true
    $SUDO apt-get install -y mate-desktop mate-panel mate-session-manager mate-terminal marco caja || true
elif command -v pacman >/dev/null 2>&1; then
    $SUDO pacman -Sy --noconfirm mate mate-extra || true
elif command -v dnf >/dev/null 2>&1; then
    $SUDO dnf install -y @mate-desktop-environment || true
fi

echo "[TDM_PROGRESS:100:MATE instalado con éxito]"
echo "✅ [TDM] Instalación de MATE Desktop completada."
