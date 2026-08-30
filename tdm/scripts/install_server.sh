#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Instalador de Servidor Gráfico Bajo Demanda
# ==============================================================================
# Uso: ./tdm/scripts/install_server.sh [termux-x11|novnc|vnc|rdp|audio]
# Registra los paquetes instalados en el SQLite Manifest para desinstalación limpia.
# ==============================================================================

set -e

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

pkg update -y || true
pkg install -y x11-repo || true

PKGS=""
case "$SERVER" in
    termux-x11|x11)
        echo "====================================================="
        echo "⚡ [TDM] Instalando Servidor Termux:X11 (Nativo)..."
        echo "====================================================="
        PKGS="termux-x11-nightly"
        ;;
    novnc)
        echo "====================================================="
        echo "🌐 [TDM] Instalando noVNC Web Server (HTML5)..."
        echo "====================================================="
        PKGS="tigervnc novnc python-numpy xorg-xauth xorg-xsetroot"
        ;;
    vnc|tigervnc)
        echo "====================================================="
        echo "🖥️ [TDM] Instalando TigerVNC Server..."
        echo "====================================================="
        PKGS="tigervnc xorg-xauth xorg-xrdb xorg-xsetroot xorg-xdpyinfo"
        ;;
    rdp|xrdp)
        echo "====================================================="
        echo "📡 [TDM] Instalando Servidor Remote Desktop (xrdp)..."
        echo "====================================================="
        PKGS="xrdp pulseaudio"
        ;;
    audio|pulseaudio)
        echo "====================================================="
        echo "🔊 [TDM] Instalando Soporte de Audio (PulseAudio)..."
        echo "====================================================="
        PKGS="pulseaudio"
        ;;
    *)
        echo "❌ Servidor desconocido: $SERVER"
        echo "Opciones válidas: termux-x11, novnc, vnc, rdp, audio"
        exit 1
        ;;
esac

# Registrar en SQLite los paquetes que no existían previamente
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
from tdm.core.manifest import manifest_ledger
manifest_ledger.record_packages_if_new('$PKGS'.split(), component='server:$SERVER')
" 2>/dev/null || true
fi

pkg install -y $PKGS || true

if [ "$SERVER" = "novnc" ]; then
    pip install --no-deps websockify || true
fi

echo "====================================================="
echo "✅ [TDM] Instalación del servidor '$SERVER' finalizada."
echo "====================================================="
