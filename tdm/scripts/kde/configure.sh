#!/usr/bin/env bash
# ==============================================================================
# ❄️ [TDM] Configuración de KDE Plasma 6 para Termux
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
CONFIG_DIR="$HOME_DIR/.config"

mkdir -p "$CONFIG_DIR"

# 1. Configurar KWin para desactivar composición pesada OpenGL en Termux (evita fallos de context)
if command -v kwriteconfig6 >/dev/null 2>&1; then
    kwriteconfig6 --file kwinrc --group Compositing --key Enabled false
    kwriteconfig6 --file kwinrc --group Compositing --key WindowsBlockCompositing true
    kwriteconfig6 --file baloofilerc --group "Basic Settings" --key "Indexing-Enabled" false
    kwriteconfig6 --file startkderc --group General --key systemdBoot false
    kwriteconfig6 --file kscreenpoolrc --group General --key "AutoRotate" false
elif command -v kwriteconfig5 >/dev/null 2>&1; then
    kwriteconfig5 --file kwinrc --group Compositing --key Enabled false
    kwriteconfig5 --file kwinrc --group Compositing --key WindowsBlockCompositing true
    kwriteconfig5 --file baloofilerc --group "Basic Settings" --key "Indexing-Enabled" false
fi

export KDE_FULL_SESSION=true
export XDG_CURRENT_DESKTOP=KDE
export DESKTOP_SESSION=plasma
export KDE_SESSION_VERSION=6
export QT_QPA_PLATFORM=xcb
