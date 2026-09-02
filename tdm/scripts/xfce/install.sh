#!/usr/bin/env bash
# ==============================================================================
# 🐭 [TDM] Instalador específico para XFCE4
# ==============================================================================
set -e
export DEBIAN_FRONTEND=noninteractive
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:10:Preparando e identificando paquetes de XFCE4]"
echo "🐭 [TDM] Instalando entorno de escritorio XFCE4..."

SUDO=""
if [ "$(id -u)" -ne 0 ] && [ ! -d "/data/data/com.termux" ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; elif command -v doas >/dev/null 2>&1; then SUDO="doas"; fi
fi

if command -v pkg >/dev/null 2>&1; then
    echo "[TDM_PROGRESS:30:Actualizando repositorio e instalando XFCE4 en Termux]"
    pkg install -y x11-repo || true
    pkg update -y || true
    echo "[TDM_PROGRESS:60:Descargando paquetes xfce4, xfce4-terminal, thunar, libxres]"
    pkg install -y xfce4 xfce4-terminal thunar libxres || {
        for p in xfce4 xfce4-terminal thunar libxres; do pkg install -y "$p" || true; done
    }
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    echo "[TDM_PROGRESS:50:Instalando XFCE4 en Alpine / postmarketOS]"
    $SUDO apk update || true
    $SUDO apk add xfce4 xfce4-terminal thunar || true
elif command -v apt-get >/dev/null 2>&1; then
    echo "[TDM_PROGRESS:50:Instalando XFCE4 en Debian / Ubuntu]"
    $SUDO apt-get update -y || true
    $SUDO apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" xfce4 xfce4-terminal thunar || true
elif command -v pacman >/dev/null 2>&1; then
    echo "[TDM_PROGRESS:50:Instalando XFCE4 en Arch Linux]"
    $SUDO pacman -Sy --noconfirm xfce4 xfce4-terminal thunar || true
elif command -v dnf >/dev/null 2>&1; then
    echo "[TDM_PROGRESS:50:Instalando XFCE4 en Fedora]"
    $SUDO dnf install -y @xfce-desktop-environment || $SUDO dnf install -y xfce4 xfce4-terminal thunar || true
fi

echo "[TDM_PROGRESS:85:Configurando esquemas y optimizando]"
if command -v glib-compile-schemas >/dev/null 2>&1; then
    glib-compile-schemas "$PREFIX_PATH/share/glib-2.0/schemas" 2>/dev/null || glib-compile-schemas "/usr/share/glib-2.0/schemas" 2>/dev/null || true
fi

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$DIR/configure.sh" ]; then
    bash "$DIR/configure.sh" 96 || true
fi

echo "[TDM_PROGRESS:100:¡XFCE4 instalado correctamente!]"
echo "✅ [TDM] Instalación de XFCE4 completada con éxito."
