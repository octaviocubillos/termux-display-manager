#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# 🧹 Termux Display Manager (TDM) - Limpiador Total y Reseteo a Cero
# ==============================================================================
# Uso:
#   bash clean.sh
#   curl -sSL https://tdm.oton.cl/clean | bash
# ==============================================================================

set -e
export DEBIAN_FRONTEND=noninteractive

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
MANIFEST_DB="$HOME_DIR/.tdm/manifest.sqlite3"

echo "=================================================================="
echo "🧹 [TDM] Limpiando Termux de TDM y Entornos de Escritorio..."
echo "=================================================================="

# ------------------------------------------------------------------------------
# 1. Detener absolutamente todos los procesos de TDM y entornos gráficos
# ------------------------------------------------------------------------------
echo "⏹️  [1/6] Deteniendo procesos, servidores gráficos y daemons..."

PROCS_TO_KILL=(
    "tdm.cli.main" "tdm.server" "tdm.agent" "websockify"
    "termux-x11" "Xvnc" "vncserver" "x0vncserver" "xrdp" "xrdp-sesman"
    "startplasma-x11" "plasma_session" "plasma-session" "plasmashell" "kwin_x11" "kwin" "kded5" "kded6" "kglobalacceld"
    "xfce4-session" "xfwm4" "xfdesktop" "xfce4-panel" "xfsettingsd" "xfconfd" "wrapper-2.0" "startxfce4"
    "mate-session" "mate-panel" "marco" "mate-settings-daemon"
    "startlxqt" "lxqt-session" "openbox" "i3"
    "pulseaudio" "virgl_test_server" "dbus-daemon"
)

for proc in "${PROCS_TO_KILL[@]}"; do
    pkill -9 -f "$proc" 2>/dev/null || true
    pkill -9 -x "$proc" 2>/dev/null || true
done

# Detener servicios supervisados runit si existen
if [ -d "$PREFIX/var/service" ]; then
    for s in "$PREFIX/var/service"/tx11-*; do
        if [ -d "$s" ]; then
            sv down "$(basename "$s")" 2>/dev/null || true
            rm -rf "$s" 2>/dev/null || true
        fi
    done
fi

# Cerrar app Termux:X11 en Android y liberar wake lock
if command -v am >/dev/null 2>&1; then
    am broadcast -a com.termux.x11.ACTION_STOP >/dev/null 2>&1 || true
    am force-stop com.termux.x11 >/dev/null 2>&1 || true
fi
termux-wake-unlock 2>/dev/null || true

# ------------------------------------------------------------------------------
# 2. Desinstalar paquetes registrados en el SQLite Manifest de TDM
# ------------------------------------------------------------------------------
echo "📦 [2/6] Desinstalando paquetes registrados en SQLite Manifest..."

if [ -f "$MANIFEST_DB" ] && command -v python3 >/dev/null 2>&1; then
    PKGS_FROM_MANIFEST=$(python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('$MANIFEST_DB')
    c = conn.cursor()
    c.execute('SELECT package_name FROM tdm_installed_packages')
    print(' '.join(row[0] for row in c.fetchall()))
except Exception:
    pass
" 2>/dev/null || true)

    if [ -n "$PKGS_FROM_MANIFEST" ]; then
        echo "   -> Eliminando paquetes registrados: $PKGS_FROM_MANIFEST"
        pkg uninstall -y $PKGS_FROM_MANIFEST >/dev/null 2>&1 || true
    fi
fi

# ------------------------------------------------------------------------------
# 3. Purgar paquetes de escritorios y dependencias gráficas instaladas
# ------------------------------------------------------------------------------
echo "🗑️  [3/6] Purgando paquetes de entornos gráficos y librerías..."

if command -v dpkg >/dev/null 2>&1; then
    INSTALLED_PKGS="$(dpkg -l 2>/dev/null | awk '/^ii/ {split($2, a, ":"); print a[1]}' || true)"

    GRAPHICAL_PATTERNS=(
        "^plasma-" "^kwin" "^breeze" "^dolphin" "^konsole" "^powerdevil" "^plasma5support" "^libplasma"
        "^xfce4" "^thunar" "^tumbler" "^ristretto"
        "^mate-" "^marco"
        "^lxqt" "^qterminal" "^pcmanfm-qt"
        "^openbox" "^obconf"
        "^i3"
        "^termux-x11" "^tigervnc"
    )

    PKGS_TO_PURGE=()
    for pattern in "${GRAPHICAL_PATTERNS[@]}"; do
        for pkg in $(echo "$INSTALLED_PKGS" | grep -E "$pattern" || true); do
            PKGS_TO_PURGE+=("$pkg")
        done
    done

    if [ ${#PKGS_TO_PURGE[@]} -gt 0 ]; then
        echo "   -> Purgando paquetes gráficos: ${PKGS_TO_PURGE[*]}"
        pkg uninstall -y "${PKGS_TO_PURGE[@]}" >/dev/null 2>&1 || \
        apt-get purge -y -o Dpkg::Options::="--force-confdef" "${PKGS_TO_PURGE[@]}" >/dev/null 2>&1 || true
    fi
fi

# ------------------------------------------------------------------------------
# 4. Limpieza profunda de almacenamiento en Termux (autoremove & clean)
# ------------------------------------------------------------------------------
echo "🧼 [4/6] Limpiando dependencias huérfanas y cachés de paquetes..."

if command -v apt-get >/dev/null 2>&1; then
    apt-get autoremove -y --purge >/dev/null 2>&1 || true
    apt-get autoclean -y >/dev/null 2>&1 || true
    apt-get clean >/dev/null 2>&1 || true
elif command -v pkg >/dev/null 2>&1; then
    pkg clean >/dev/null 2>&1 || true
fi

# ------------------------------------------------------------------------------
# 5. Eliminar ejecutables, módulos Python y archivos de sistema de TDM
# ------------------------------------------------------------------------------
echo "📁 [5/6] Eliminando archivos del sistema TDM y enlaces..."

# Binario CLI
rm -f "$PREFIX/bin/tdm"

# Enlaces .pth de Python
for pth in "$PREFIX"/lib/python*/site-packages/tdm*; do
    rm -rf "$pth" 2>/dev/null || true
done

# Directorios de instalación de TDM
rm -rf "$PREFIX/opt/termux-display-manager"
rm -rf "$PREFIX/share/termux-display-manager"
rm -rf "$HOME_DIR/.tdm"

# Configuraciones generadas por escritorios en pruebas
rm -rf "$HOME_DIR/.config/xfce4"
rm -rf "$HOME_DIR/.config/kwinrc"
rm -rf "$HOME_DIR/.config/plasma*"
rm -rf "$HOME_DIR/.config/baloofilerc"
rm -rf "$HOME_DIR/.config/mate"
rm -rf "$HOME_DIR/.config/lxqt"
rm -rf "$HOME_DIR/.config/i3"
rm -rf "$HOME_DIR/.config/openbox"
rm -rf "$HOME_DIR/.vnc"

# ------------------------------------------------------------------------------
# 6. Limpieza de sockets, tuberías IPC y temporales
# ------------------------------------------------------------------------------
echo "🔌 [6/6] Limpiando sockets X11 y archivos temporales..."

TMPDIRS=("/tmp" "$PREFIX/tmp" "${TMPDIR:-/data/data/com.termux/files/usr/tmp}")
for dir in "${TMPDIRS[@]}"; do
    if [ -d "$dir" ]; then
        rm -f "$dir"/.X*-lock 2>/dev/null || true
        rm -rf "$dir"/.X11-unix 2>/dev/null || true
        rm -rf "$dir"/X11-pipe 2>/dev/null || true
        rm -f "$dir"/dbus-* 2>/dev/null || true
        rm -f "$dir"/tdm* 2>/dev/null || true
    fi
done

# Limpiar descargas temporales si existen
rm -f /sdcard/Download/tdm-bundle.tar.gz /sdcard/Download/install_tdm.sh 2>/dev/null || true

echo "=================================================================="
echo "✨ [TDM] Limpieza completa finalizada exitosamente."
echo "🚀 Termux ha quedado limpio y listo para probar la instalación de 0:"
echo ""
echo "   curl -sSL https://tdm.oton.cl/install | bash"
echo "=================================================================="
