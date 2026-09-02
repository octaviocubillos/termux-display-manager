#!/usr/bin/env bash
# ==============================================================================
# ❄️ [TDM] Lanzador para KDE Plasma
# ==============================================================================
export KDE_FULL_SESSION=true
if command -v startplasma-x11 >/dev/null 2>&1; then
    exec startplasma-x11
elif command -v plasma-session >/dev/null 2>&1; then
    exec plasma-session
else
    kwin_x11 &
    exec plasmashell
fi
