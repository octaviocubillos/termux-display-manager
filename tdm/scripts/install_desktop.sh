#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Instalador de Entorno de Escritorio Nativo
# ==============================================================================
# Uso: ./scripts/install_desktop.sh [kde|mate|xfce|lxqt|i3|openbox]
# Registra los paquetes instalados en el SQLite Manifest para desinstalación limpia.
# ==============================================================================

set -e

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

pkg update -y || true
pkg install -y x11-repo || true

PKGS=""
case "$DESKTOP" in
    kde)
        echo "====================================================="
        echo "❄️ [TDM] Instalando KDE Plasma Desktop (Nativo)..."
        echo "====================================================="
        PKGS="plasma-desktop plasma-workspace breeze konsole dolphin kwrite"
        ;;
    mate)
        echo "====================================================="
        echo "🧉 [TDM] Instalando MATE Desktop Environment..."
        echo "====================================================="
        PKGS="mate-desktop mate-panel mate-session-manager mate-terminal marco caja"
        ;;
    xfce|xfce4)
        echo "====================================================="
        echo "🐭 [TDM] Instalando XFCE4..."
        echo "====================================================="
        PKGS="xfce4 xfce4-terminal thunar"
        ;;
    lxqt)
        echo "====================================================="
        echo "🚀 [TDM] Instalando LXQt..."
        echo "====================================================="
        PKGS="lxqt lxqt-session qterminal pcmanfm-qt"
        ;;
    i3)
        echo "====================================================="
        echo "🪟 [TDM] Instalando i3 Window Manager..."
        echo "====================================================="
        PKGS="i3 i3status dmenu xterm"
        ;;
    openbox)
        echo "====================================================="
        echo "📦 [TDM] Instalando Openbox..."
        echo "====================================================="
        PKGS="openbox tint2 xterm"
        ;;
    *)
        echo "❌ Entorno desconocido: $DESKTOP"
        echo "Opciones válidas: kde, mate, xfce, lxqt, i3, openbox"
        exit 1
        ;;
esac

# Registrar en SQLite los paquetes que no existían previamente
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
from tdm.core.manifest import manifest_ledger
manifest_ledger.record_packages_if_new('$PKGS'.split(), component='desktop:$DESKTOP')
" 2>/dev/null || true
fi

pkg install -y $PKGS || true

echo "====================================================="
echo "✅ [TDM] Instalación de $DESKTOP finalizada."
echo "====================================================="
