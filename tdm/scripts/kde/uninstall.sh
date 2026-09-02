#!/usr/bin/env bash
# ==============================================================================
# ❄️ [TDM] Desinstalador específico para KDE Plasma
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:20:Deteniendo procesos de KDE]"
for proc in plasma-desktop kwin kwin_x11 plasmashell dolphin konsole; do
    pkill -9 -x "$proc" 2>/dev/null || true
done

echo "[TDM_PROGRESS:50:Purgando paquetes de KDE]"
if command -v pkg >/dev/null 2>&1; then
    INSTALLED="$(dpkg -l 2>/dev/null | awk '/^ii/ {split($2, a, ":"); print a[1]}' | grep -E '^(plasma-|plasma-desktop|plasma-workspace|kwin|dolphin|konsole|breeze|kded[56]|libkf[56])' || true)"
    for p in $INSTALLED; do
        pkg uninstall -y "$p" >/dev/null 2>&1 || true
        apt-get purge -y -o Dpkg::Options::="--force-confdef" "$p" >/dev/null 2>&1 || true
    done
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    apk del plasma-desktop plasma-workspace konsole dolphin 2>/dev/null || true
elif command -v apt-get >/dev/null 2>&1; then
    apt-get purge -y plasma-desktop plasma-workspace dolphin konsole >/dev/null 2>&1 || true
elif command -v pacman >/dev/null 2>&1; then
    pacman -Rns --noconfirm plasma-desktop plasma-workspace konsole dolphin 2>/dev/null || true
elif command -v dnf >/dev/null 2>&1; then
    dnf remove -y @kde-desktop-environment 2>/dev/null || true
fi

rm -f "$PREFIX_PATH/bin/startplasma-x11" "$PREFIX_PATH/bin/plasma-session" "$PREFIX_PATH/bin/plasmashell" "$PREFIX_PATH/bin/kwin" "$PREFIX_PATH/bin/kwin_x11" 2>/dev/null || true
echo "[TDM_PROGRESS:100:KDE Plasma desinstalado correctamente]"
echo "✅ [TDM] KDE Plasma desinstalado completamente."
