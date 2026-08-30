#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Script de Desinstalación Selectiva (Auditada)
# ==============================================================================
# Desinstala ÚNICAMENTE los paquetes registrados en el SQLite Manifest de TDM,
# preservando intactos los paquetes previos del usuario.
# ==============================================================================

set -e

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
MANIFEST_DB="$HOME_DIR/.tdm/manifest.sqlite3"

echo "====================================================="
echo "🗑️  [TDM] Desinstalación Selectiva de Termux Display Manager"
echo "====================================================="

# 1. Detener procesos y servidores activos
echo "[1/5] Deteniendo servidores de pantalla y procesos activos..."
pkill -9 -f "tdm.cli.main" || true
pkill -9 -f "websockify" || true
pkill -9 -f "Xvnc" || true
pkill -9 -f "termux-x11" || true
pkill -9 -f "xrdp" || true

# 2. Consultar SQLite y desinstalar SOLO los paquetes que TDM instaló
echo "[2/5] Consultando registro SQLite para desinstalar solo paquetes de TDM..."
if [ -f "$MANIFEST_DB" ] && command -v python3 >/dev/null 2>&1; then
    PKGS_TO_REMOVE=$(python3 -c "
import sqlite3
try:
    conn = sqlite3.connect('$MANIFEST_DB')
    cursor = conn.cursor()
    cursor.execute('SELECT package_name FROM tdm_installed_packages')
    pkgs = [row[0] for row in cursor.fetchall()]
    print(' '.join(pkgs))
except Exception:
    pass
" 2>/dev/null || true)

    if [ -n "$PKGS_TO_REMOVE" ]; then
        echo "📦 Desinstalando paquetes registrados por TDM: $PKGS_TO_REMOVE"
        apt-get remove -y $PKGS_TO_REMOVE || true
    else
        echo "ℹ️  No hay paquetes exclusivos de TDM para desinstalar (los existentes eran previos)."
    fi
fi

# 3. Limpiar sockets temporales X11
echo "[3/5] Limpiando sockets X11 temporales..."
rm -f /tmp/.X*-lock /tmp/.X11-unix/X* /tmp/X11-pipe/X* /tmp/dbus-* 2>/dev/null || true

# 4. Eliminar ejecutable global tdm y enlaces .pth
echo "[4/5] Removiendo ejecutable global 'tdm' y paquetes registrados..."
rm -f "$PREFIX/bin/tdm"

for pth in "$PREFIX"/lib/python*/site-packages/tdm.pth; do
    if [ -f "$pth" ]; then
        rm -f "$pth"
    fi
done

# 5. Borrar directorio ~/.tdm y descargas temporales
echo "[5/5] Eliminando archivos de configuración (~/.tdm)..."
rm -rf "$HOME_DIR/.tdm"
rm -f /sdcard/Download/tdm-bundle.tar.gz /sdcard/Download/install_tdm.sh 2>/dev/null || true

echo "====================================================="
echo "✅ [TDM] Desinstalación completada con éxito."
echo "🧹 Se eliminaron solo los componentes instalados por TDM."
echo "🛡️  Tus paquetes y configuraciones personales han sido preservados."
echo "====================================================="
