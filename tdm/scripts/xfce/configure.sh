#!/usr/bin/env bash
# ==============================================================================
# 🐭 [TDM] Configuración y optimización de DPI/Escalado para XFCE4
# ==============================================================================
DPI="${1:-96}"
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"

LOGO_PATH="$PREFIX_PATH/opt/termux-display-manager/tdm/web/assets/logos/xfce.svg"
if [ ! -f "$LOGO_PATH" ]; then LOG_PATH="$HOME_DIR/.tdm/assets/xfce.svg"; fi

if [ "$DPI" -gt 120 ]; then
    SCALE_VAL=2
    PANEL_SZ=48
    CURSOR_SZ=36
else
    SCALE_VAL=1
    PANEL_SZ=26
    CURSOR_SZ=24
fi

if command -v xfconf-query >/dev/null 2>&1; then
    (sleep 1 && \
     xfconf-query -c xsettings -p /Gdk/WindowScalingFactor -s $SCALE_VAL --create -t int >/dev/null 2>&1 || true; \
     xfconf-query -c xfce4-panel -p /panels/panel-1/size -s $PANEL_SZ --create -t int >/dev/null 2>&1 || true; \
     xfconf-query -c xsettings -p /Gtk/CursorThemeSize -s $CURSOR_SZ --create -t int >/dev/null 2>&1 || true; \
     if [ -f "$LOGO_PATH" ]; then xfconf-query -c xfce4-panel -p /plugins/plugin-1/button-icon -s "$LOGO_PATH" --create -t string >/dev/null 2>&1; fi) &
fi
