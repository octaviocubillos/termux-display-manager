#!/usr/bin/env bash
# ==============================================================================
# Termux Display Manager (TDM) - Instalador de Entorno de Escritorio Nativo
# ==============================================================================
# Uso: ./install_desktop.sh [kde|mate|xfce|lxqt|i3|openbox]
# Soporta: Termux (pkg/apt), Alpine/postmarketOS (apk), Debian/Ubuntu (apt), Arch (pacman), Fedora (dnf)
# ==============================================================================

set -e
export DEBIAN_FRONTEND=noninteractive
export APT_LISTCHANGES_FRONTEND=none

DESKTOP="$1"

if [ -z "$DESKTOP" ]; then
    echo "Uso: $0 [kde|mate|xfce|lxqt|i3|openbox]"
    echo ""
    echo "Opciones disponibles:"
    echo "  • kde      -> Instala KDE Plasma Desktop completo"
    echo "  • mate     -> Instala MATE Desktop Environment"
    echo "  • xfce     -> Instala XFCE4 Desktop"
    echo "  • lxqt     -> Instala LXQt Desktop"
    echo "  • i3       -> Instala i3 Window Manager"
    echo "  • openbox  -> Instala Openbox Window Manager"
    exit 1
fi

# Detectar elevación de privilegios (solo para sistemas Linux tradicionales fuera de Termux)
SUDO=""
if [ "$(id -u)" -ne 0 ] && [ ! -d "/data/data/com.termux" ]; then
    if command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    elif command -v doas >/dev/null 2>&1; then
        SUDO="doas"
    fi
fi

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

echo "====================================================="
echo "🛠️ [TDM] Gestor de paquetes detectado: ${PKG_MGR:-desconocido}"
echo "====================================================="

PKGS=""
case "$DESKTOP" in
    kde)
        echo "❄️ [TDM] Instalando KDE Plasma Desktop..."
        if [ "$PKG_MGR" = "apk" ]; then
            PKGS="plasma-desktop plasma-workspace konsole dolphin"
        else
            PKGS="plasma-desktop plasma-workspace breeze konsole dolphin"
        fi
        ;;
    mate)
        echo "🧉 [TDM] Instalando MATE Desktop Environment..."
        PKGS="mate-desktop mate-panel mate-session-manager mate-terminal marco caja"
        ;;
    xfce|xfce4)
        echo "🐭 [TDM] Instalando XFCE4..."
        PKGS="xfce4 xfce4-terminal thunar"
        ;;
    lxqt)
        echo "🚀 [TDM] Instalando LXQt..."
        if [ "$PKG_MGR" = "apk" ]; then
            PKGS="lxqt-desktop lxqt-session qterminal pcmanfm-qt"
        else
            PKGS="lxqt lxqt-session qterminal pcmanfm-qt"
        fi
        ;;
    i3)
        echo "🪟 [TDM] Instalando i3 Window Manager..."
        if [ "$PKG_MGR" = "apk" ]; then
            PKGS="i3wm i3status dmenu xterm"
        else
            PKGS="i3 i3status dmenu xterm"
        fi
        ;;
    openbox)
        echo "📦 [TDM] Instalando Openbox..."
        PKGS="openbox tint2 xterm"
        ;;
    *)
        echo "❌ Entorno desconocido: $DESKTOP"
        echo "Opciones válidas: kde, mate, xfce, lxqt, i3, openbox"
        exit 1
        ;;
esac

# ==============================================================================
# APAGAR SESIONES GRÁFICAS Y PROCESOS ANTERIORES (EXCEPTO EL SERVICIO TDM)
# ==============================================================================
echo "====================================================="
echo "🛑 [TDM] Apagando entornos gráficos y procesos activos (manteniendo servicio TDM)..."
echo "====================================================="

for proc in xfce4-session xfwm4 xfdesktop mate-session marco caja plasma-desktop kwin startlxqt lxqt-session openbox i3 i3status termux-x11 Xwayland Xvnc websockify virgl_test_server; do
    pkill -9 -x "$proc" 2>/dev/null || true
done
rm -f /tmp/.X*-lock /tmp/.X11-unix/X* /data/data/com.termux/files/usr/tmp/.X*-lock /data/data/com.termux/files/usr/tmp/.X11-unix/X* 2>/dev/null || true

# ==============================================================================
# LIMPIEZA DE ENTORNOS ANTERIORES (Liberación de espacio y eliminación de conflictos)
# ==============================================================================
echo "====================================================="
echo "🧹 [TDM] Limpiando entornos anteriores para evitar conflictos y liberar espacio..."
echo "====================================================="

case "$PKG_MGR" in
    pkg|apt)
        INSTALLED_LIST="$(dpkg -l 2>/dev/null | awk '/^ii/ {print $2}' || true)"
        PKGS_TO_PURGE=""

        get_matching() {
            local pattern="$1"
            echo "$INSTALLED_LIST" | grep -E "$pattern" || true
        }

        # Purga de cualquier otro DE que no sea el seleccionado
        [ "$DESKTOP" != "xfce" ] && [ "$DESKTOP" != "xfce4" ] && PKGS_TO_PURGE="$PKGS_TO_PURGE $(get_matching '^(xfce4|xfwm4|xfdesktop4?|thunar|libxfce4|xfconf)')"
        [ "$DESKTOP" != "kde" ] && PKGS_TO_PURGE="$PKGS_TO_PURGE $(get_matching '^(plasma-|plasma-desktop|plasma-workspace|kwin|dolphin|konsole|breeze|kded[56]|libkf[56])')"
        [ "$DESKTOP" != "mate" ] && PKGS_TO_PURGE="$PKGS_TO_PURGE $(get_matching '^(mate-|marco|caja)')"
        [ "$DESKTOP" != "lxqt" ] && PKGS_TO_PURGE="$PKGS_TO_PURGE $(get_matching '^(lxqt|liblxqt|libdbusmenu-lxqt|pcmanfm-qt|libfm-qt|qterminal)')"
        [ "$DESKTOP" != "i3" ] && PKGS_TO_PURGE="$PKGS_TO_PURGE $(get_matching '^(i3|i3wm|i3status|dmenu)')"
        [ "$DESKTOP" != "openbox" ] && PKGS_TO_PURGE="$PKGS_TO_PURGE $(get_matching '^(openbox|obconf|tint2)')"

        # Eliminar duplicados
        CLEAN_PURGE_LIST="$(echo "$PKGS_TO_PURGE" | tr ' ' '\n' | sort -u | tr '\n' ' ' | xargs || true)"

        if [ -n "$CLEAN_PURGE_LIST" ]; then
            echo "🗑️ Desinstalando paquetes de entornos anteriores: $CLEAN_PURGE_LIST"
            for p in $CLEAN_PURGE_LIST; do
                apt-get purge -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" "$p" >/dev/null 2>&1 || true
            done
            echo "🧹 Liberando dependencias huérfanas y caché de paquetes..."
            apt-get autoremove -y --purge >/dev/null 2>&1 || true
            apt-get clean >/dev/null 2>&1 || true
        fi
        ;;
esac

# Registrar en SQLite Manifest
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
try:
    from tdm.core.manifest import manifest_ledger
    manifest_ledger.record_packages_if_new('$PKGS'.split(), component='desktop:$DESKTOP')
except Exception:
    pass
" 2>/dev/null || true
fi

case "$PKG_MGR" in
    pkg)
        echo "[*] Asegurando repositorio x11-repo en Termux..."
        pkg install -y x11-repo || true
        echo "[*] Actualizando índices de paquetes Termux..."
        pkg update -y || true
        echo "[*] Instalando paquetes: $PKGS..."
        pkg install -y $PKGS || {
            echo "[!] Reintentando instalación paquete por paquete..."
            for p in $PKGS; do
                pkg install -y "$p" || echo "[!] Advertencia: no se pudo instalar $p (continuando)"
            done
        }
        ;;
    apk)
        echo "[*] Actualizando índices de paquetes APK..."
        $SUDO apk update || true
        echo "[*] Instalando paquetes: $PKGS..."
        $SUDO apk add $PKGS || {
            echo "[!] Reintentando instalación paquete por paquete..."
            for p in $PKGS; do
                $SUDO apk add "$p" || echo "[!] Advertencia: no se pudo instalar $p (continuando)"
            done
        }
        ;;
    apt)
        echo "[*] Actualizando índices de paquetes APT..."
        $SUDO apt-get update -y || true
        if [ -d "/data/data/com.termux" ]; then
            $SUDO apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" x11-repo || true
            $SUDO apt-get update -y || true
        fi
        echo "[*] Instalando paquetes: $PKGS..."
        $SUDO apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" $PKGS || {
            echo "[!] Reintentando instalación paquete por paquete..."
            for p in $PKGS; do
                $SUDO apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" "$p" || echo "[!] Advertencia: no se pudo instalar $p"
            done
        }
        ;;
    pacman)
        echo "[*] Actualizando e instalando con pacman..."
        $SUDO pacman -Sy --noconfirm $PKGS || {
            for p in $PKGS; do
                $SUDO pacman -S --noconfirm "$p" || true
            done
        }
        ;;
    dnf)
        echo "[*] Instalando con dnf..."
        $SUDO dnf install -y $PKGS || true
        ;;
    *)
        echo "❌ No se encontró un gestor de paquetes compatible (pkg, apk, apt-get, pacman, dnf)."
        exit 1
        ;;
esac

# Optimización y limpieza automática de almacenamiento
echo "🧹 [TDM] Optimizando espacio en disco (autoremove & autoclean)..."
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

echo "====================================================="
echo "✅ [TDM] Instalación de $DESKTOP finalizada correctamente."
echo "====================================================="
