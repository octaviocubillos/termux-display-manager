#!/usr/bin/env bash
# ==============================================================================
# Termux Display Manager (TDM) - Instalador de Servidor Gráfico Bajo Demanda
# ==============================================================================
# Uso: ./install_server.sh [termux-x11|novnc|vnc|rdp|audio]
# Soporta: Termux (pkg/apt), Alpine/postmarketOS (apk), Debian/Ubuntu (apt), Arch (pacman), Fedora (dnf)
# ==============================================================================

set -e
export DEBIAN_FRONTEND=noninteractive
export APT_LISTCHANGES_FRONTEND=none

SERVER="$1"

if [ -z "$SERVER" ]; then
    echo "Uso: $0 [termux-x11|novnc|vnc|rdp|audio]"
    echo ""
    echo "Servidores disponibles:"
    echo "  • termux-x11 -> Servidor gráfico nativo de alto rendimiento para Android"
    echo "  • novnc      -> Visor Web HTML5 embebido (WebSockets + TigerVNC + noVNC)"
    echo "  • vnc        -> Servidor TigerVNC estándar en puerto 5900 (para bVNC)"
    echo "  • rdp        -> Servidor Microsoft Remote Desktop (xrdp)"
    echo "  • audio      -> Servidor de sonido en red PulseAudio"
    exit 1
fi

# Detectar elevación de privilegios
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
case "$SERVER" in
    termux-x11|x11)
        echo "⚡ [TDM] Instalando Servidor Termux:X11 (Nativo)..."
        PKGS="termux-x11-nightly"
        ;;
    novnc)
        echo "🌐 [TDM] Instalando noVNC Web Server (HTML5)..."
        if [ "$PKG_MGR" = "apk" ]; then
            PKGS="tigervnc xauth xsetroot"
        else
            PKGS="tigervnc xorg-xauth xorg-xsetroot"
        fi
        ;;
    vnc|tigervnc)
        echo "🖥️ [TDM] Instalando TigerVNC Server..."
        if [ "$PKG_MGR" = "apk" ]; then
            PKGS="tigervnc xauth xrdb xsetroot xdpyinfo"
        else
            PKGS="tigervnc xorg-xauth xorg-xsetroot"
        fi
        ;;
    rdp|xrdp)
        echo "📡 [TDM] Instalando Servidor Remote Desktop (xrdp)..."
        PKGS="xrdp pulseaudio"
        ;;
    audio|pulseaudio)
        echo "🔊 [TDM] Instalando Soporte de Audio (PulseAudio)..."
        PKGS="pulseaudio"
        ;;
    *)
        echo "❌ Servidor desconocido: $SERVER"
        echo "Opciones válidas: termux-x11, novnc, vnc, rdp, audio"
        exit 1
        ;;
esac

# Registrar en SQLite Manifest
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
try:
    from tdm.core.manifest import manifest_ledger
    manifest_ledger.record_packages_if_new('$PKGS'.split(), component='server:$SERVER')
except Exception:
    pass
" 2>/dev/null || true
fi

case "$PKG_MGR" in
    pkg)
        echo "[*] Asegurando repositorio x11-repo en Termux..."
        pkg install -y x11-repo || true
        pkg update -y || true
        echo "[*] Instalando paquetes: $PKGS..."
        pkg install -y $PKGS || {
            for p in $PKGS; do
                pkg install -y "$p" || echo "[!] Advertencia: no se pudo instalar $p"
            done
        }
        ;;
    apk)
        echo "[*] Actualizando e instalando con apk..."
        $SUDO apk update || true
        $SUDO apk add $PKGS || {
            for p in $PKGS; do
                $SUDO apk add "$p" || echo "[!] Advertencia: no se pudo instalar $p"
            done
        }
        ;;
    apt)
        echo "[*] Actualizando e instalando con apt..."
        $SUDO apt-get update -y || true
        if [ -d "/data/data/com.termux" ]; then
            $SUDO apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" x11-repo || true
            $SUDO apt-get update -y || true
        fi
        $SUDO apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" $PKGS || {
            for p in $PKGS; do
                $SUDO apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" "$p" || true
            done
        }
        ;;
    pacman)
        $SUDO pacman -Sy --noconfirm $PKGS || true
        ;;
    dnf)
        $SUDO dnf install -y $PKGS || true
        ;;
    *)
        echo "❌ No se encontró un gestor de paquetes compatible."
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

if [ "$SERVER" = "novnc" ]; then
    if command -v pip >/dev/null 2>&1; then
        pip install --no-deps websockify || true
    elif command -v pip3 >/dev/null 2>&1; then
        pip3 install --no-deps websockify || true
    fi
fi

if [ "$SERVER" = "termux-x11" ] || [ "$SERVER" = "x11" ]; then
    if [ -d "/data/data/com.termux" ]; then
        echo "====================================================="
        echo "📱 [Permisos de Android] Configuración de inicio automático de X11"
        echo "====================================================="
        echo "ℹ️  Para que la app gráfica Termux:X11 se abra automáticamente al iniciar,"
        echo "   Android necesita el permiso 'Mostrar sobre otras aplicaciones'."
        echo "🚀 Abriendo pantalla de permisos de Android en tu móvil..."
        am start -a android.settings.action.MANAGE_OVERLAY_PERMISSION -d "package:com.termux" 2>/dev/null || \
        am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d "package:com.termux" 2>/dev/null || \
        termux-am start -a android.settings.action.MANAGE_OVERLAY_PERMISSION -d "package:com.termux" 2>/dev/null || true

        if pm list packages 2>/dev/null | grep -q "com.termux.x11"; then
            am start -a android.settings.action.MANAGE_OVERLAY_PERMISSION -d "package:com.termux.x11" 2>/dev/null || true
        fi
        echo "💡 Activa 'Permitir' en la pantalla de ajustes de tu teléfono."
    fi
fi

echo "====================================================="
echo "✅ [TDM] Instalación del servidor '$SERVER' finalizada."
echo "====================================================="
