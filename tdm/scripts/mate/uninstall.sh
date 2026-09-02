#!/usr/bin/env bash
# ==============================================================================
# 🧉 [TDM] Desinstalador específico para MATE Desktop
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:20:Deteniendo procesos de MATE]"
for proc in mate-session marco caja mate-panel mate-terminal; do
    pkill -9 -x "$proc" 2>/dev/null || true
done

echo "[TDM_PROGRESS:50:Purgando paquetes de MATE]"
if command -v pkg >/dev/null 2>&1; then
    INSTALLED="$(dpkg -l 2>/dev/null | awk '/^ii/ {split($2, a, ":"); print a[1]}' | grep -E '^(mate-|marco|caja)' || true)"
    for p in $INSTALLED; do
        pkg uninstall -y "$p" >/dev/null 2>&1 || true
        apt-get purge -y -o Dpkg::Options::="--force-confdef" "$p" >/dev/null 2>&1 || true
    done
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    apk del mate-desktop mate-panel mate-session-manager marco caja 2>/dev/null || true
elif command -v apt-get >/dev/null 2>&1; then
    apt-get purge -y mate-desktop-environment mate-session-manager >/dev/null 2>&1 || true
elif command -v pacman >/dev/null 2>&1; then
    pacman -Rns --noconfirm mate mate-extra 2>/dev/null || true
elif command -v dnf >/dev/null 2>&1; then
    dnf remove -y @mate-desktop-environment 2>/dev/null || true
fi

rm -f "$PREFIX_PATH/bin/mate-session" "$PREFIX_PATH/bin/marco" "$PREFIX_PATH/bin/caja" "$PREFIX_PATH/bin/mate-panel" 2>/dev/null || true
echo "[TDM_PROGRESS:100:MATE desinstalado correctamente]"
echo "✅ [TDM] MATE Desktop desinstalado completamente."
