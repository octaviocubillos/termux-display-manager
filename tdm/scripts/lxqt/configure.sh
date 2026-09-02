#!/usr/bin/env bash
# ==============================================================================
# 🚀 [TDM] Configuración nativa de LXQt (con Batería y Audio)
# ==============================================================================
export XDG_CURRENT_DESKTOP=LXQt
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"

# Iniciar gestor de energía y bandeja en background si están disponibles
(sleep 2 && \
 if command -v lxqt-powermanagement >/dev/null 2>&1; then
     lxqt-powermanagement &
 fi
) &
