#!/usr/bin/env bash
# ==============================================================================
# 🪟 [TDM] Configuración de i3 Window Manager
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"

mkdir -p "$HOME_DIR/.config/i3"
if [ ! -f "$HOME_DIR/.config/i3/config" ]; then
    if [ -f "$PREFIX_PATH/etc/i3/config" ]; then
        cp "$PREFIX_PATH/etc/i3/config" "$HOME_DIR/.config/i3/config" 2>/dev/null || true
    elif [ -f "/etc/i3/config" ]; then
        cp "/etc/i3/config" "$HOME_DIR/.config/i3/config" 2>/dev/null || true
    fi
fi
