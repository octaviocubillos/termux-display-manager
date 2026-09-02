#!/usr/bin/env bash
# ==============================================================================
# 🪟 [TDM] Lanzador para i3 Window Manager
# ==============================================================================
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$DIR/configure.sh" ]; then
    bash "$DIR/configure.sh" || true
fi

# Autoiniciar terminal inicial para interacción inmediata
(sleep 1 && (aterm -geometry 90x30 || xfce4-terminal || mate-terminal || qterminal || konsole || xterm || st)) &

exec i3
