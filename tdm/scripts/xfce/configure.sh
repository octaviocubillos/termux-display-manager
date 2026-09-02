#!/usr/bin/env bash
# ==============================================================================
# 🐭 [TDM] Configuración nativa para XFCE4
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"

LOGO_PATH="$PREFIX_PATH/opt/termux-display-manager/tdm/web/assets/logos/xfce.svg"
if [ ! -f "$LOGO_PATH" ]; then LOGO_PATH="$HOME_DIR/.tdm/assets/xfce.svg"; fi

if command -v xfconf-query >/dev/null 2>&1; then
    (sleep 1 && \
     if [ -f "$LOGO_PATH" ]; then xfconf-query -c xfce4-panel -p /plugins/plugin-1/button-icon -s "$LOGO_PATH" --create -t string >/dev/null 2>&1 || true; fi) &
fi
