#!/usr/bin/env bash
# ==============================================================================
# 🐭 [TDM] Lanzador para XFCE4
# ==============================================================================
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DPI="${1:-96}"

if [ -f "$DIR/configure.sh" ]; then
    bash "$DIR/configure.sh" "$DPI" &
fi

if command -v xfce4-session >/dev/null 2>&1; then
    exec xfce4-session
else
    exec startxfce4
fi
