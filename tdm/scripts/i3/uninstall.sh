#!/usr/bin/env bash
# ==============================================================================
# 🪟 [TDM] Desinstalador específico para i3 Window Manager
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:20:Deteniendo procesos de i3]"
for proc in i3 i3status dmenu; do
    pkill -9 -x "$proc" 2>/dev/null || true
done

echo "[TDM_PROGRESS:50:Purgando paquetes de i3]"
if command -v pkg >/dev/null 2>&1; then
    INSTALLED="$(dpkg -l 2>/dev/null | awk '/^ii/ {split($2, a, ":"); print a[1]}' | grep -E '^(i3|i3wm|i3status|dmenu)' || true)"
    for p in $INSTALLED; do
        pkg uninstall -y "$p" >/dev/null 2>&1 || true
        apt-get purge -y -o Dpkg::Options::="--force-confdef" "$p" >/dev/null 2>&1 || true
    done
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    apk del i3wm i3status dmenu 2>/dev/null || true
elif command -v apt-get >/dev/null 2>&1; then
    apt-get purge -y i3 i3status dmenu >/dev/null 2>&1 || true
elif command -v pacman >/dev/null 2>&1; then
    pacman -Rns --noconfirm i3-wm i3status dmenu 2>/dev/null || true
elif command -v dnf >/dev/null 2>&1; then
    dnf remove -y i3 i3status dmenu 2>/dev/null || true
fi

rm -f "$PREFIX_PATH/bin/i3" "$PREFIX_PATH/bin/i3-with-shmlog" "$PREFIX_PATH/bin/i3status" "$PREFIX_PATH/bin/dmenu" 2>/dev/null || true
echo "[TDM_PROGRESS:100:i3 desinstalado correctamente]"
echo "✅ [TDM] i3 Window Manager desinstalado completamente."
