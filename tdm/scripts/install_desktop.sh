#!/usr/bin/env bash
# ==============================================================================
# Termux Display Manager (TDM) - Despachador Modular de Instalación de Entorno
# ==============================================================================
# Uso: ./install_desktop.sh [kde|mate|xfce|lxqt|i3|openbox|terminal]
# ==============================================================================
set -e
export DEBIAN_FRONTEND=noninteractive
export APT_LISTCHANGES_FRONTEND=none

DESKTOP="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

if [ -z "$DESKTOP" ]; then
    echo "Uso: $0 [kde|mate|xfce|lxqt|i3|openbox|terminal]"
    exit 1
fi

# Normalizar alias
case "$DESKTOP" in
    xfce4) DESKTOP="xfce" ;;
    i3wm) DESKTOP="i3" ;;
esac

echo "====================================================="
echo "🛠️ [TDM] Iniciando instalación modular de: $DESKTOP"
echo "====================================================="
echo "[TDM_PROGRESS:10:Preparando entorno para $DESKTOP]"

# 1. Apagar procesos gráficos activos (manteniendo servicio TDM)
for proc in xfce4-session xfwm4 xfdesktop mate-session marco caja plasma-desktop kwin startlxqt lxqt-session openbox i3 i3status termux-x11 Xwayland Xvnc websockify virgl_test_server; do
    pkill -9 -x "$proc" 2>/dev/null || true
done
rm -f /tmp/.X*-lock /tmp/.X11-unix/X* "$PREFIX_PATH/tmp/.X*-lock" "$PREFIX_PATH/tmp/.X11-unix/X*" 2>/dev/null || true

# 2. Desinstalar otros entornos previos si existen para liberar espacio
echo "[TDM_PROGRESS:25:Limpiando entornos previos]"
for de in xfce kde mate lxqt i3 openbox terminal; do
    if [ "$de" != "$DESKTOP" ] && [ -f "$SCRIPT_DIR/$de/uninstall.sh" ]; then
        # Solo desinstalar si detectamos binarios del otro entorno
        bash "$SCRIPT_DIR/$de/uninstall.sh" >/dev/null 2>&1 || true
    fi
done

# 3. Ejecutar el script instalador específico del entorno
ENV_INSTALL_SCRIPT="$SCRIPT_DIR/$DESKTOP/install.sh"
if [ -f "$ENV_INSTALL_SCRIPT" ]; then
    bash "$ENV_INSTALL_SCRIPT"
else
    echo "❌ Error: No se encontró script de instalación para '$DESKTOP' en $ENV_INSTALL_SCRIPT"
    exit 1
fi

# 4. Registrar en SQLite Manifest
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
try:
    from tdm.core.manifest import manifest_ledger
    from tdm.core.registry import get_desktop_entry
    de_info = get_desktop_entry('$DESKTOP') or {}
    pkgs = de_info.get('packages', ['$DESKTOP'])
    manifest_ledger.record_packages_if_new(pkgs, component='desktop:$DESKTOP')
except Exception:
    pass
" 2>/dev/null || true
fi

echo "====================================================="
echo "🎉 [TDM] ¡Entorno $DESKTOP instalado y configurado con éxito!"
echo "====================================================="
