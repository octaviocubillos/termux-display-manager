#!/usr/bin/env bash
# ==============================================================================
# 🪟 [TDM] Configuración nativa de i3 Window Manager (con Batería y Audio)
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"

mkdir -p "$HOME_DIR/.config/i3"
mkdir -p "$HOME_DIR/.config/i3status"

# 1. Configuración de barra i3status con batería, volumen y fecha
if [ ! -f "$HOME_DIR/.config/i3status/config" ]; then
    cat << 'STATUS_EOF' > "$HOME_DIR/.config/i3status/config"
general {
    colors = true
    interval = 5
    color_good = "#4ade80"
    color_degraded = "#fde047"
    color_bad = "#ef4444"
}

order += "volume master"
order += "battery all"
order += "memory"
order += "tztime local"

volume master {
    format = "🔊 %volume"
    format_muted = "🔇 muted (%volume)"
    device = "default"
    mixer = "Master"
    mixer_idx = 0
}

battery all {
    format = "%status %percentage"
    format_down = "No bat"
    status_chr = "⚡ CHR"
    status_bat = "🔋 BAT"
    status_unk = "? UNK"
    status_full = "☻ FULL"
    low_threshold = 15
}

memory {
    format = "💾 %used"
    threshold_degraded = "10%"
    format_degraded = "MEM LOW: %free"
}

tztime local {
    format = "🕒 %Y-%m-%d %H:%M"
}
STATUS_EOF
fi

# 2. Configuración de i3 si no existe
if [ ! -f "$HOME_DIR/.config/i3/config" ]; then
    if [ -f "$PREFIX_PATH/etc/i3/config" ]; then
        cp "$PREFIX_PATH/etc/i3/config" "$HOME_DIR/.config/i3/config" 2>/dev/null || true
    elif [ -f "/etc/i3/config" ]; then
        cp "/etc/i3/config" "$HOME_DIR/.config/i3/config" 2>/dev/null || true
    fi
fi
