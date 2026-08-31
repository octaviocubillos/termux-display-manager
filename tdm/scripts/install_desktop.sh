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
            PKGS="plasma-desktop plasma-workspace breeze konsole dolphin kwrite"
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

rm -f /tmp/.X*-lock /tmp/.X11-unix/X* /data/data/com.termux/files/usr/tmp/.X*-lock /data/data/com.termux/files/usr/tmp/.X11-unix/X* 2>/dev/null || true

# ==============================================================================
# LIMPIEZA DE ENTORNOS ANTERIORES (Liberación de espacio y eliminación de conflictos)
# ==============================================================================
echo "====================================================="
echo "🧹 [TDM] Limpiando entornos anteriores para evitar conflictos y liberar espacio..."
echo "====================================================="

ALL_DESKTOPS="kde mate xfce lxqt i3 openbox"
PKGS_TO_PURGE=""

for d in $ALL_DESKTOPS; do
    if [ "$d" != "$DESKTOP" ] && { [ "$d" != "xfce" ] || [ "$DESKTOP" != "xfce4" ]; }; then
        case "$d" in
            kde)
                PKGS_TO_PURGE="$PKGS_TO_PURGE plasma-desktop plasma-workspace breeze konsole dolphin kwrite kded5 kded6 kwin"
                ;;
            mate)
                PKGS_TO_PURGE="$PKGS_TO_PURGE mate-desktop mate-panel mate-session-manager mate-terminal marco caja mate-settings-daemon"
                ;;
            xfce)
                PKGS_TO_PURGE="$PKGS_TO_PURGE xfce4 xfce4-session xfce4-panel xfwm4 xfdesktop xfce4-terminal thunar xfconf"
                ;;
            lxqt)
                PKGS_TO_PURGE="$PKGS_TO_PURGE lxqt lxqt-session lxqt-panel qterminal pcmanfm-qt lxqt-globalkeys"
                ;;
            i3)
                PKGS_TO_PURGE="$PKGS_TO_PURGE i3 i3wm i3status dmenu"
                ;;
            openbox)
                PKGS_TO_PURGE="$PKGS_TO_PURGE openbox tint2 obconf"
                ;;
        esac
    fi
done

case "$PKG_MGR" in
    pkg|apt)
        PURGED_ANY=0
        for p in $PKGS_TO_PURGE; do
            if dpkg -s "$p" >/dev/null 2>&1; then
                echo "🗑️ Desinstalando entorno anterior ($p)..."
                apt-get purge -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" "$p" >/dev/null 2>&1 || true
                PURGED_ANY=1
            fi
        done
        if [ "$PURGED_ANY" -eq 1 ]; then
            echo "🧹 Liberando dependencias huérfanas y caché de paquetes..."
            apt-get autoremove -y --purge >/dev/null 2>&1 || true
            apt-get clean >/dev/null 2>&1 || true
        fi
        ;;
    apk)
        for p in $PKGS_TO_PURGE; do
            $SUDO apk del "$p" >/dev/null 2>&1 || true
        done
        ;;
    pacman)
        for p in $PKGS_TO_PURGE; do
            $SUDO pacman -Rns --noconfirm "$p" >/dev/null 2>&1 || true
        done
        ;;
    dnf)
        for p in $PKGS_TO_PURGE; do
            $SUDO dnf remove -y "$p" >/dev/null 2>&1 || true
        done
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

echo "====================================================="
echo "✅ [TDM] Instalación de $DESKTOP finalizada correctamente."
echo "====================================================="
