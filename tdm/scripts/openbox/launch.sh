#!/usr/bin/env bash
# ==============================================================================
# 📦 [TDM] Lanzador para Openbox
# ==============================================================================
if command -v tint2 >/dev/null 2>&1; then
    tint2 &
fi

if command -v openbox-session >/dev/null 2>&1; then
    exec openbox-session
else
    exec openbox
fi
