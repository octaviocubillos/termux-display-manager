#!/usr/bin/env bash
# ==============================================================================
# 💻 [TDM] Instalador específico para Modo Terminal X11
# ==============================================================================
set -e
export DEBIAN_FRONTEND=noninteractive
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:10:Preparando Terminal X11]"
if command -v pkg >/dev/null 2>&1; then
    pkg install -y x11-repo || true
    pkg install -y aterm || true
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    apk add xterm || true
elif command -v apt-get >/dev/null 2>&1; then
    apt-get install -y xterm || true
elif command -v pacman >/dev/null 2>&1; then
    pacman -Sy --noconfirm xterm || true
elif command -v dnf >/dev/null 2>&1; then
    dnf install -y xterm || true
fi

echo "[TDM_PROGRESS:100:Modo Terminal X11 listo]"
echo "✅ [TDM] Instalación de Terminal X11 completada."
