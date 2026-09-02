#!/usr/bin/env bash
# ==============================================================================
# ❄️ [TDM] Lanzador para KDE Plasma
# ==============================================================================
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DPI="${1:-96}"

# 1. Ejecutar script de configuración previo
if [ -f "$DIR/configure.sh" ]; then
    bash "$DIR/configure.sh" "$DPI"
fi

# 2. Variables de entorno globales para KDE Plasma 6 en Termux
export KDE_FULL_SESSION=true
export XDG_CURRENT_DESKTOP=KDE
export DESKTOP_SESSION=plasma
export KDE_SESSION_VERSION=6
export QT_QPA_PLATFORM=xcb
export QT_AUTO_SCREEN_SCALE_FACTOR=0
export BALOO_FILE_INDEXING_DISABLED=1

# 3. Lanzar sesión de KDE Plasma
if command -v startplasma-x11 >/dev/null 2>&1; then
    exec startplasma-x11
elif command -v plasma_session >/dev/null 2>&1; then
    exec plasma_session
elif command -v plasma-session >/dev/null 2>&1; then
    exec plasma-session
else
    kwin_x11 --replace &
    exec plasmashell
fi
