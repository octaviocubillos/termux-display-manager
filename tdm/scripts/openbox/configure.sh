#!/usr/bin/env bash
# ==============================================================================
# 📦 [TDM] Configuración nativa de Openbox (con Batería y Audio en Tint2)
# ==============================================================================
export XDG_CURRENT_DESKTOP=OPENBOX
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"

mkdir -p "$HOME_DIR/.config/openbox"
mkdir -p "$HOME_DIR/.config/tint2"

# Iniciar tint2 panel si no está corriendo
(sleep 1 && \
 if command -v tint2 >/dev/null 2>&1 && ! pgrep -x tint2 >/dev/null 2>&1; then
     tint2 &
 fi
) &
