#!/usr/bin/env bash
# ==============================================================================
# 🐭 [TDM] Desinstalador específico para XFCE4
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:20:Deteniendo procesos de XFCE4]"
for proc in xfce4-session xfwm4 xfdesktop xfdesktop4 thunar xfce4-panel xfce4-terminal; do
    pkill -9 -x "$proc" 2>/dev/null || true
done

echo "[TDM_PROGRESS:50:Purgando paquetes de XFCE4]"
if command -v pkg >/dev/null 2>&1; then
    INSTALLED="$(dpkg -l 2>/dev/null | awk '/^ii/ {split($2, a, ":"); print a[1]}' | grep -E '^(xfce4|xfwm4|xfdesktop4?|thunar|libxfce4|xfconf)' || true)"
    for p in $INSTALLED; do
        pkg uninstall -y "$p" >/dev/null 2>&1 || true
        apt-get purge -y -o Dpkg::Options::="--force-confdef" "$p" >/dev/null 2>&1 || true
    done
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    apk del xfce4 xfce4-terminal thunar 2>/dev/null || true
elif command -v apt-get >/dev/null 2>&1; then
    apt-get purge -y xfce4 xfce4-terminal thunar >/dev/null 2>&1 || true
elif command -v pacman >/dev/null 2>&1; then
    pacman -Rns --noconfirm xfce4 xfce4-terminal thunar 2>/dev/null || true
elif command -v dnf >/dev/null 2>&1; then
    dnf remove -y @xfce-desktop-environment 2>/dev/null || true
fi

echo "[TDM_PROGRESS:80:Limpiando binarios residuales]"
rm -f "$PREFIX_PATH/bin/startxfce4" "$PREFIX_PATH/bin/xfce4-session" "$PREFIX_PATH/bin/xfwm4" "$PREFIX_PATH/bin/xfdesktop" "$PREFIX_PATH/bin/xfdesktop4" "$PREFIX_PATH/bin/thunar" "$PREFIX_PATH/bin/xfce4-panel" 2>/dev/null || true

echo "[TDM_PROGRESS:100:XFCE4 desinstalado correctamente]"
echo "✅ [TDM] XFCE4 desinstalado completamente."
