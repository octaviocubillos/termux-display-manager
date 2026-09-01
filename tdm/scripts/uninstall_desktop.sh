#!/usr/bin/env bash
# ==============================================================================
# Termux Display Manager (TDM) - Desinstalador Completo de Entornos de Escritorio
# ==============================================================================
# Uso: ./uninstall_desktop.sh [all|kde|mate|xfce|lxqt|i3|openbox]
# ==============================================================================

set -e
export DEBIAN_FRONTEND=noninteractive
export APT_LISTCHANGES_FRONTEND=none

TARGET="${1:-all}"
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "====================================================="
echo "🗑️  [TDM] Desinstalador Completo de Entorno de Escritorio"
echo "Objetivo: $TARGET"
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
for proc in xfce4-session xfwm4 xfdesktop mate-session marco caja plasma-desktop kwin startlxqt lxqt-session openbox i3 i3status termux-x11 Xwayland Xvnc websockify virgl_test_server; do
    pkill -9 -x "$proc" 2>/dev/null || true
done

# Limpiar sockets X11
rm -f /tmp/.X*-lock /tmp/.X11-unix/X* "${PREFIX_PATH}/tmp/.X*-lock" "${PREFIX_PATH}/tmp/.X11-unix/X*" 2>/dev/null || true

# 2. Búsqueda y purga dinámica de paquetes
echo "[2/4] Identificando paquetes instalados para purga completa..."

case "$PKG_MGR" in
    pkg|apt)
        INSTALLED_LIST="$(dpkg -l 2>/dev/null | awk '/^ii/ {split($2, a, ":"); print a[1]}' || true)"
        PKGS_TO_REMOVE=""

        get_matching_pkgs() {
            local pattern="$1"
            echo "$INSTALLED_LIST" | grep -E "$pattern" || true
        }

        case "$TARGET" in
            xfce|xfce4)
                PKGS_TO_REMOVE="$(get_matching_pkgs '^(xfce4|xfwm4|xfdesktop4?|thunar|libxfce4|xfconf)')"
                ;;
            kde)
                PKGS_TO_REMOVE="$(get_matching_pkgs '^(plasma-|plasma-desktop|plasma-workspace|kwin|dolphin|konsole|breeze|kded[56]|libkf[56])')"
                ;;
            mate)
                PKGS_TO_REMOVE="$(get_matching_pkgs '^(mate-|marco|caja)')"
                ;;
            lxqt)
                PKGS_TO_REMOVE="$(get_matching_pkgs '^(lxqt|liblxqt|libdbusmenu-lxqt|pcmanfm-qt|libfm-qt|qterminal)')"
                ;;
            i3)
                PKGS_TO_REMOVE="$(get_matching_pkgs '^(i3|i3wm|i3status|dmenu)')"
                ;;
            openbox)
                PKGS_TO_REMOVE="$(get_matching_pkgs '^(openbox|obconf|tint2)')"
                ;;
            all|*)
                PKGS_TO_REMOVE="$(get_matching_pkgs '^(xfce4|xfwm4|xfdesktop4?|thunar|libxfce4|xfconf|plasma-|plasma-desktop|plasma-workspace|kwin|dolphin|konsole|breeze|kded[56]|libkf[56]|mate-|marco|caja|lxqt|liblxqt|libdbusmenu-lxqt|pcmanfm-qt|libfm-qt|qterminal|i3|i3wm|i3status|dmenu|openbox|obconf|tint2)')"
                ;;
        esac

        if [ -n "$PKGS_TO_REMOVE" ]; then
            echo "📦 Purgando paquetes encontrados:"
            echo "$PKGS_TO_REMOVE"
            for p in $PKGS_TO_REMOVE; do
                if command -v pkg >/dev/null 2>&1; then
                    pkg uninstall -y "$p" >/dev/null 2>&1 || apt-get purge -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" "$p" >/dev/null 2>&1 || true
                else
                    $SUDO apt-get purge -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" "$p" >/dev/null 2>&1 || true
                fi
            done
        else
            echo "ℹ️ No se detectaron paquetes instalados para el entorno: $TARGET"
        fi

        # Limpiar binarios residuales por seguridad para que la detección sea 100% inmediata
        case "$TARGET" in
            xfce|xfce4) rm -f "$PREFIX_PATH/bin/startxfce4" "$PREFIX_PATH/bin/xfce4-session" "$PREFIX_PATH/bin/xfwm4" 2>/dev/null || true ;;
            kde) rm -f "$PREFIX_PATH/bin/startplasma-x11" "$PREFIX_PATH/bin/plasma-session" "$PREFIX_PATH/bin/kwin" 2>/dev/null || true ;;
            mate) rm -f "$PREFIX_PATH/bin/mate-session" "$PREFIX_PATH/bin/marco" 2>/dev/null || true ;;
            lxqt) rm -f "$PREFIX_PATH/bin/startlxqt" "$PREFIX_PATH/bin/lxqt-session" 2>/dev/null || true ;;
            i3) rm -f "$PREFIX_PATH/bin/i3" "$PREFIX_PATH/bin/i3status" 2>/dev/null || true ;;
            openbox) rm -f "$PREFIX_PATH/bin/openbox" "$PREFIX_PATH/bin/openbox-session" 2>/dev/null || true ;;
            all|*) rm -f "$PREFIX_PATH/bin/startxfce4" "$PREFIX_PATH/bin/xfce4-session" "$PREFIX_PATH/bin/startplasma-x11" "$PREFIX_PATH/bin/mate-session" "$PREFIX_PATH/bin/startlxqt" "$PREFIX_PATH/bin/i3" "$PREFIX_PATH/bin/openbox" 2>/dev/null || true ;;
        esac
        ;;

    apk)
        case "$TARGET" in
            xfce|xfce4) $SUDO apk del xfce4 xfce4-terminal thunar 2>/dev/null || true ;;
            kde) $SUDO apk del plasma-desktop plasma-workspace konsole dolphin 2>/dev/null || true ;;
            mate) $SUDO apk del mate-desktop mate-panel mate-session-manager marco 2>/dev/null || true ;;
            lxqt) $SUDO apk del lxqt-desktop lxqt-session qterminal pcmanfm-qt 2>/dev/null || true ;;
            i3) $SUDO apk del i3wm i3status dmenu xterm 2>/dev/null || true ;;
            openbox) $SUDO apk del openbox tint2 xterm 2>/dev/null || true ;;
            all|*) $SUDO apk del xfce4 plasma-desktop mate-desktop lxqt-desktop i3wm openbox 2>/dev/null || true ;;
        esac
        ;;

    pacman)
        case "$TARGET" in
            xfce|xfce4) $SUDO pacman -Rns --noconfirm xfce4 xfce4-terminal thunar 2>/dev/null || true ;;
            kde) $SUDO pacman -Rns --noconfirm plasma-desktop plasma-workspace konsole dolphin 2>/dev/null || true ;;
            mate) $SUDO pacman -Rns --noconfirm mate mate-extra 2>/dev/null || true ;;
            lxqt) $SUDO pacman -Rns --noconfirm lxqt qterminal pcmanfm-qt 2>/dev/null || true ;;
            i3) $SUDO pacman -Rns --noconfirm i3-wm i3status dmenu 2>/dev/null || true ;;
            openbox) $SUDO pacman -Rns --noconfirm openbox tint2 2>/dev/null || true ;;
            all|*) $SUDO pacman -Rns --noconfirm xfce4 plasma-desktop mate lxqt i3-wm openbox 2>/dev/null || true ;;
        esac
        ;;

    dnf)
        case "$TARGET" in
            xfce|xfce4) $SUDO dnf remove -y @xfce-desktop-environment 2>/dev/null || true ;;
            kde) $SUDO dnf remove -y @kde-desktop-environment 2>/dev/null || true ;;
            mate) $SUDO dnf remove -y @mate-desktop-environment 2>/dev/null || true ;;
            lxqt) $SUDO dnf remove -y @lxqt-desktop-environment 2>/dev/null || true ;;
            i3) $SUDO dnf remove -y i3 i3status dmenu 2>/dev/null || true ;;
            openbox) $SUDO dnf remove -y openbox tint2 2>/dev/null || true ;;
            all|*) $SUDO dnf remove -y @xfce-desktop-environment @kde-desktop-environment @mate-desktop-environment @lxqt-desktop-environment 2>/dev/null || true ;;
        esac
        ;;
esac

# 4. Limpieza de dependencias huérfanas y caché de paquetes (autoremove & autoclean)
echo "[3/4] Purgando dependencias huérfanas y optimizando almacenamiento..."
case "$PKG_MGR" in
    pkg|apt)
        $SUDO apt-get autoremove -y --purge >/dev/null 2>&1 || true
        $SUDO apt-get autoclean -y >/dev/null 2>&1 || true
        $SUDO apt-get clean >/dev/null 2>&1 || true
        ;;
    apk)
        $SUDO apk cache clean >/dev/null 2>&1 || true
        ;;
    pacman)
        $SUDO pacman -Sc --noconfirm >/dev/null 2>&1 || true
        ;;
    dnf)
        $SUDO dnf autoremove -y >/dev/null 2>&1 || true
        $SUDO dnf clean all >/dev/null 2>&1 || true
        ;;
esac

# 5. Limpiar configuraciones residuales y cachés en HOME
echo "[4/4] Limpiando configuraciones residuales y cachés..."
rm -rf ~/.cache/sessions ~/.cache/xfce4 ~/.cache/plasma* ~/.cache/lxqt* ~/.config/xfce4 ~/.config/lxqt 2>/dev/null || true

echo "====================================================="
echo "✅ [TDM] Desinstalación de entorno finalizada con éxito."
echo "====================================================="
