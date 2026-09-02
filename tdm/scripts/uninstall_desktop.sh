#!/usr/bin/env bash
# ==============================================================================
# Termux Display Manager (TDM) - Despachador Modular de Desinstalación
# ==============================================================================
# Uso: ./uninstall_desktop.sh [all|kde|mate|xfce|lxqt|i3|openbox|terminal]
# ==============================================================================
set -e
export DEBIAN_FRONTEND=noninteractive
export APT_LISTCHANGES_FRONTEND=none

TARGET="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

# Normalizar alias
case "$TARGET" in
    xfce4) TARGET="xfce" ;;
    i3wm) TARGET="i3" ;;
esac

echo "====================================================="
echo "🗑️  [TDM] Desinstalador Modular de Entornos"
echo "Objetivo: $TARGET"
echo "====================================================="
echo "[TDM_PROGRESS:15:Deteniendo pantallas y procesos activos]"

# 1. Detener procesos gráficos activos (manteniendo servicio TDM)
for proc in xfce4-session xfwm4 xfdesktop mate-session marco caja plasma-desktop kwin startlxqt lxqt-session openbox i3 i3status termux-x11 Xwayland Xvnc websockify virgl_test_server aterm xterm; do
    pkill -9 -x "$proc" 2>/dev/null || true
done
rm -f /tmp/.X*-lock /tmp/.X11-unix/X* "$PREFIX_PATH/tmp/.X*-lock" "$PREFIX_PATH/tmp/.X11-unix/X*" 2>/dev/null || true

# 2. Desinstalar según objetivo
echo "[TDM_PROGRESS:40:Ejecutando desinstalación modular]"

if [ "$TARGET" = "all" ]; then
    for de in xfce kde mate lxqt i3 openbox terminal; do
        if [ -f "$SCRIPT_DIR/$de/uninstall.sh" ]; then
            echo "[*] Desinstalando módulo: $de..."
            bash "$SCRIPT_DIR/$de/uninstall.sh" || true
        fi
    done
else
    if [ -f "$SCRIPT_DIR/$TARGET/uninstall.sh" ]; then
        bash "$SCRIPT_DIR/$TARGET/uninstall.sh"
    else
        echo "❌ Error: No se encontró script de desinstalación para '$TARGET' en $SCRIPT_DIR/$TARGET/uninstall.sh"
        exit 1
    fi
fi

# 3. Optimización y limpieza final de caché de paquetes
echo "[TDM_PROGRESS:85:Limpiando paquetes huérfanos y caché]"
if command -v pkg >/dev/null 2>&1 || command -v apt-get >/dev/null 2>&1; then
    apt-get autoremove -y --purge >/dev/null 2>&1 || true
    apt-get clean >/dev/null 2>&1 || true
elif command -v apk >/dev/null 2>&1; then
    apk cache clean >/dev/null 2>&1 || true
elif command -v pacman >/dev/null 2>&1; then
    pacman -Sc --noconfirm >/dev/null 2>&1 || true
elif command -v dnf >/dev/null 2>&1; then
    dnf autoremove -y >/dev/null 2>&1 || true
    dnf clean all >/dev/null 2>&1 || true
fi

echo "[TDM_PROGRESS:100:Desinstalación completada con éxito]"
echo "====================================================="
echo "✅ [TDM] Desinstalación de $TARGET completada correctamente."
echo "====================================================="
