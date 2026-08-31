#!/usr/bin/env bash
# ==============================================================================
# Termux Display Manager (TDM) - Desinstalador de Entornos de Escritorio
# ==============================================================================
# Uso: ./uninstall_desktop.sh [all|kde|mate|xfce|lxqt|i3|openbox]
# ==============================================================================

set -e
export DEBIAN_FRONTEND=noninteractive
export APT_LISTCHANGES_FRONTEND=none

TARGET="${1:-all}"

echo "====================================================="
echo "🗑️  [TDM] Desinstalador Completo de Entorno de Escritorio"
echo "Target: $TARGET"
echo "====================================================="

# Detectar gestor de paquetes
PKG_MGR=""
if command -v pkg >/dev/null 2>&1; then
    PKG_MGR="pkg"
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    PKG_MGR="apk"
elif command -v apt-get >/dev/null 2>&1; then
    PKG_MGR="apt"
elif command -v pacman >/dev/null 2>&1; then
    PKG_MGR="pacman"
elif command -v dnf >/dev/null 2>&1; then
    PKG_MGR="dnf"
fi

SUDO=""
if [ "$(id -u)" -ne 0 ] && [ ! -d "/data/data/com.termux" ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    elif command -v doas >/dev/null 2>&1; then
        SUDO="doas"
    fi
fi

# 1. Detener todas las pantallas y procesos de escritorio activos (manteniendo servicio TDM)
echo "[1/4] Deteniendo pantallas y procesos gráficos..."
pkill -9 -f xfce4 2>/dev/null || true
pkill -9 -f xfwm4 2>/dev/null || true
pkill -9 -f xfdesktop 2>/dev/null || true
pkill -9 -f mate-session 2>/dev/null || true
pkill -9 -f marco 2>/dev/null || true
pkill -9 -f plasma 2>/dev/null || true
pkill -9 -f kwin 2>/dev/null || true
pkill -9 -f startlxqt 2>/dev/null || true
pkill -9 -f lxqt-session 2>/dev/null || true
pkill -9 -f openbox 2>/dev/null || true
pkill -9 -f i3 2>/dev/null || true

pkill -9 -f termux-x11 2>/dev/null || true
pkill -9 -f Xwayland 2>/dev/null || true
pkill -9 -f Xvnc 2>/dev/null || true
pkill -9 -f websockify 2>/dev/null || true
pkill -9 -f pulseaudio 2>/dev/null || true
pkill -9 -f virgl_test_server 2>/dev/null || true

# Limpiar sockets X11
rm -f /tmp/.X*-lock /tmp/.X11-unix/X* /data/data/com.termux/files/usr/tmp/.X*-lock /data/data/com.termux/files/usr/tmp/.X11-unix/X* 2>/dev/null || true

# 2. Definición de paquetes por entorno
XFCE_PKGS="xfce4 xfce4-session xfce4-panel xfwm4 xfdesktop xfce4-terminal thunar xfconf"
KDE_PKGS="plasma-desktop plasma-workspace breeze konsole dolphin kwrite kded5 kded6 kwin"
MATE_PKGS="mate-desktop mate-panel mate-session-manager mate-terminal marco caja mate-settings-daemon"
LXQT_PKGS="lxqt lxqt-session lxqt-panel qterminal pcmanfm-qt lxqt-globalkeys"
I3_PKGS="i3 i3wm i3status dmenu"
OPENBOX_PKGS="openbox tint2 obconf"

PKGS_TO_REMOVE=""
case "$TARGET" in
    xfce|xfce4)
        PKGS_TO_REMOVE="$XFCE_PKGS"
        ;;
    kde)
        PKGS_TO_REMOVE="$KDE_PKGS"
        ;;
    mate)
        PKGS_TO_REMOVE="$MATE_PKGS"
        ;;
    lxqt)
        PKGS_TO_REMOVE="$LXQT_PKGS"
        ;;
    i3)
        PKGS_TO_REMOVE="$I3_PKGS"
        ;;
    openbox)
        PKGS_TO_REMOVE="$OPENBOX_PKGS"
        ;;
    all|*)
        PKGS_TO_REMOVE="$XFCE_PKGS $KDE_PKGS $MATE_PKGS $LXQT_PKGS $I3_PKGS $OPENBOX_PKGS"
        ;;
esac

echo "[2/4] Desinstalando y purgando paquetes del entorno..."
case "$PKG_MGR" in
    pkg|apt)
        for p in $PKGS_TO_REMOVE; do
            if dpkg -s "$p" >/dev/null 2>&1; then
                echo "🗑️ Desinstalando: $p..."
                apt-get purge -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" "$p" >/dev/null 2>&1 || true
            fi
        done
        echo "[3/4] Purgando dependencias huérfanas y liberando almacenamiento..."
        apt-get autoremove -y --purge >/dev/null 2>&1 || true
        apt-get clean >/dev/null 2>&1 || true
        ;;
    apk)
        for p in $PKGS_TO_REMOVE; do
            $SUDO apk del "$p" >/dev/null 2>&1 || true
        done
        ;;
    pacman)
        for p in $PKGS_TO_REMOVE; do
            $SUDO pacman -Rns --noconfirm "$p" >/dev/null 2>&1 || true
        done
        ;;
    dnf)
        for p in $PKGS_TO_REMOVE; do
            $SUDO dnf remove -y "$p" >/dev/null 2>&1 || true
        done
        ;;
esac

# 4. Limpiar cachés de sesión en HOME
echo "[4/4] Limpiando configuraciones residuales..."
rm -rf ~/.cache/sessions ~/.cache/xfce4 ~/.cache/plasma* 2>/dev/null || true

echo "====================================================="
echo "✅ [TDM] Desinstalación de entorno finalizada con éxito."
echo "====================================================="
