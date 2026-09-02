#!/usr/bin/env bash
# ==============================================================================
# 📦 [TDM] Desinstalador específico para Openbox
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"

echo "[TDM_PROGRESS:20:Deteniendo procesos de Openbox]"
for proc in openbox openbox-session tint2 obconf obconf-qt; do
    pkill -9 -x "$proc" 2>/dev/null || true
done

echo "[TDM_PROGRESS:50:Purgando paquetes de Openbox]"
if command -v pkg >/dev/null 2>&1; then
    INSTALLED="$(dpkg -l 2>/dev/null | awk '/^ii/ {split($2, a, ":"); print a[1]}' | grep -E '^(openbox|obconf|tint2)' || true)"
    for p in $INSTALLED; do
        pkg uninstall -y "$p" >/dev/null 2>&1 || true
        apt-get purge -y -o Dpkg::Options::="--force-confdef" "$p" >/dev/null 2>&1 || true
    done
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    apk del openbox tint2 2>/dev/null || true
elif command -v apt-get >/dev/null 2>&1; then
    apt-get purge -y openbox obconf tint2 >/dev/null 2>&1 || true
elif command -v pacman >/dev/null 2>&1; then
    pacman -Rns --noconfirm openbox tint2 2>/dev/null || true
elif command -v dnf >/dev/null 2>&1; then
    dnf remove -y openbox tint2 2>/dev/null || true
fi

rm -f "$PREFIX_PATH/bin/openbox" "$PREFIX_PATH/bin/openbox-session" "$PREFIX_PATH/bin/tint2" 2>/dev/null || true
echo "[TDM_PROGRESS:100:Openbox desinstalado correctamente]"
echo "✅ [TDM] Openbox desinstalado completamente."
