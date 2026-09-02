#!/usr/bin/env bash
# ==============================================================================
# 🧉 [TDM] Configuración nativa de MATE Desktop (con Batería y Audio)
# ==============================================================================
export GSETTINGS_BACKEND=keyfile
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"

# Iniciar utilidades de bandeja para volumen y batería en background
(sleep 2 && \
 if command -v mate-volume-control-status-icon >/dev/null 2>&1; then
     mate-volume-control-status-icon &
 fi
 if command -v mate-power-manager >/dev/null 2>&1; then
     mate-power-manager &
 fi
) &
