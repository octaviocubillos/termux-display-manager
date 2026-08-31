#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Bootstrap Installer One-Liner
# ==============================================================================
# Script de instalación automática del Backend de TDM dentro de Termux.
# Registra los paquetes instalados en el SQLite Manifest para desinstalación limpia.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    DIR="$SCRIPT_DIR"
else
    DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"

echo "====================================================="
echo "🚀 [TDM] Instalando Backend de Termux Display Manager"
echo "====================================================="

# 1. Habilitar permisos de comunicación externa para el APK
echo "[1/4] Configurando permisos de comunicación externa..."
mkdir -p "$HOME_DIR/.termux"
PROP_FILE="$HOME_DIR/.termux/termux.properties"
if [ ! -f "$PROP_FILE" ]; then
    echo "allow-external-apps = true" > "$PROP_FILE"
else
    if ! grep -q "allow-external-apps" "$PROP_FILE"; then
        echo "allow-external-apps = true" >> "$PROP_FILE"
    else
        sed -i 's/allow-external-apps = false/allow-external-apps = true/g' "$PROP_FILE" || true
    fi
fi

# 2. Configurar directorios de TDM y registrar código fuente
echo "[2/4] Preparando entorno de ejecución TDM..."
mkdir -p "$HOME_DIR/.tdm/run" "$HOME_DIR/.tdm/logs" "$HOME_DIR/.tdm/config"

# Registrar TDM en site-packages de Python si Python ya existe
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    SITE_PACKAGES="$PREFIX/lib/python${PYTHON_VER}/site-packages"
    if [ -d "$SITE_PACKAGES" ]; then
        echo "$DIR" > "$SITE_PACKAGES/tdm.pth"
    fi
fi

# 3. Registrar en SQLite los paquetes que TDM va a instalar
PACKAGES_TO_INSTALL="python x11-repo dbus xorg-xauth xorg-xsetroot procps"
if command -v python3 >/dev/null 2>&1 && [ -f "$DIR/tdm/core/manifest.py" ]; then
    PYTHONPATH="$DIR" python3 -c "
from tdm.core.manifest import manifest_ledger
manifest_ledger.record_packages_if_new('$PACKAGES_TO_INSTALL'.split(), component='minimal')
" 2>/dev/null || true
fi

echo "[3/4] Instalando dependencias base (Python, x11-repo, D-Bus)..."
pkg update -y || true
pkg install -y $PACKAGES_TO_INSTALL || true

# Registrar enlace .pth después de instalar python si no estaba instalado
PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
SITE_PACKAGES="$PREFIX/lib/python${PYTHON_VER}/site-packages"
if [ -d "$SITE_PACKAGES" ]; then
    echo "$DIR" > "$SITE_PACKAGES/tdm.pth"
fi

# 4. Crear ejecutable global 'tdm'
BIN_PATH="$PREFIX/bin/tdm"
cat << 'EOF' > "$BIN_PATH"
#!/data/data/com.termux/files/usr/bin/bash
exec python3 -m tdm.cli.main "$@"
EOF
chmod +x "$BIN_PATH" || true

echo "====================================================="
echo "✅ [TDM] Backend instalado con éxito!"
echo "🚀 Iniciando TDM Daemon en segundo plano (puerto 19050)..."
echo "====================================================="

pkill -f "tdm.cli.main" || true
nohup "$BIN_PATH" server --port 19050 > "$HOME_DIR/.tdm/logs/server.log" 2>&1 &

echo "🎉 TDM Core activo en http://127.0.0.1:19050"
