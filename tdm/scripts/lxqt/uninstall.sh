#!/usr/bin/env bash
# ==============================================================================
# 🚀 [TDM] Desinstalador específico para LXQt
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:20:Deteniendo procesos de LXQt]"
for proc in startlxqt lxqt-session pcmanfm-qt qterminal; do
    pkill -9 -x "$proc" 2>/dev/null || true
done

echo "[TDM_PROGRESS:50:Purgando paquetes de LXQt]"
if command -v pkg >/dev/null 2>&1; then
    INSTALLED="$(dpkg -l 2>/dev/null | awk '/^ii/ {split($2, a, ":"); print a[1]}' | grep -E '^(lxqt|liblxqt|libdbusmenu-lxqt|pcmanfm-qt|libfm-qt|qterminal)' || true)"
    for p in $INSTALLED; do
        pkg uninstall -y "$p" >/dev/null 2>&1 || true
        apt-get purge -y -o Dpkg::Options::="--force-confdef" "$p" >/dev/null 2>&1 || true
    done
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    apk del lxqt-desktop lxqt-session qterminal pcmanfm-qt 2>/dev/null || true
elif command -v apt-get >/dev/null 2>&1; then
    apt-get purge -y lxqt lxqt-session qterminal pcmanfm-qt >/dev/null 2>&1 || true
elif command -v pacman >/dev/null 2>&1; then
    pacman -Rns --noconfirm lxqt qterminal pcmanfm-qt 2>/dev/null || true
elif command -v dnf >/dev/null 2>&1; then
    dnf remove -y @lxqt-desktop-environment 2>/dev/null || true
fi

rm -f "$PREFIX_PATH/bin/startlxqt" "$PREFIX_PATH/bin/lxqt-session" "$PREFIX_PATH/bin/pcmanfm-qt" 2>/dev/null || true
echo "[TDM_PROGRESS:100:LXQt desinstalado correctamente]"
echo "✅ [TDM] LXQt desinstalado completamente."
