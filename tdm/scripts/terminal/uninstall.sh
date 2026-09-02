#!/usr/bin/env bash
# ==============================================================================
# 💻 [TDM] Desinstalador para Modo Terminal X11
# ==============================================================================
for proc in aterm xterm st; do
    pkill -9 -x "$proc" 2>/dev/null || true
done
echo "✅ [TDM] Modo Terminal X11 limpiado."
