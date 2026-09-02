#!/usr/bin/env bash
# ==============================================================================
# 💻 [TDM] Lanzador para Modo Terminal X11
# ==============================================================================
USER_SHELL="${SHELL:-/data/data/com.termux/files/usr/bin/bash}"
if [ ! -x "$USER_SHELL" ]; then USER_SHELL="sh"; fi

exec aterm -e "$USER_SHELL" || exec xfce4-terminal -e "$USER_SHELL" || exec mate-terminal -e "$USER_SHELL" || exec qterminal -e "$USER_SHELL" || exec konsole -e "$USER_SHELL" || exec xterm -e "$USER_SHELL" || exec st -e "$USER_SHELL" || exec "$USER_SHELL"
