#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Bootstrap Installer One-Liner
# ==============================================================================
# Script de instalación automática del Backend de TDM dentro de Termux.
# Registra los paquetes instalados en el SQLite Manifest para desinstalación limpia.
# ==============================================================================

set -e

# ------------------------------------------------------------------------------
# Verificación de entorno: Solo ejecutable dentro de Termux en Android
# ------------------------------------------------------------------------------
if [ ! -d "/data/data/com.termux" ] || { [ -z "$TERMUX_VERSION" ] && [ ! -f "/data/data/com.termux/files/usr/bin/bash" ]; }; then
    echo "[TDM] Error: Este script está protegido y solo puede ejecutarse dentro del entorno Termux en Android." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    DIR="$SCRIPT_DIR"
else
    DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"

echo "====================================================="
echo "[TDM] Instalando Backend de Termux Display Manager"
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

# 2. Configurar directorios del sistema de TDM y desplegar código fuente
SYSTEM_DIR="$PREFIX/opt/termux-display-manager"
echo "[2/4] Desplegando archivos del sistema en $SYSTEM_DIR..."
mkdir -p "$SYSTEM_DIR" "$PREFIX/bin" "$HOME_DIR/.tdm/run" "$HOME_DIR/.tdm/logs" "$HOME_DIR/.tdm/config"

# Copiar archivos del proyecto o descargar paquete al directorio del sistema
if [ "$DIR" != "$SYSTEM_DIR" ] && [ -f "$DIR/pyproject.toml" ]; then
    cp -rf "$DIR"/* "$SYSTEM_DIR"/ 2>/dev/null || true
    rm -rf "$SYSTEM_DIR/landing" "$SYSTEM_DIR/.git" "$SYSTEM_DIR/dist" 2>/dev/null || true
elif [ ! -f "$SYSTEM_DIR/pyproject.toml" ]; then
    echo "• Descargando paquete oficial de TDM..."
    curl -sSL "https://tdm.oton.cl/tdm-bundle.tar.gz" -o "/tmp/tdm-bundle.tar.gz" 2>/dev/null && \
        tar -xzf "/tmp/tdm-bundle.tar.gz" -C "$SYSTEM_DIR" 2>/dev/null && rm -f "/tmp/tdm-bundle.tar.gz" || \
    curl -sSL "https://github.com/octaviocubillos/termux-display-manager/archive/refs/heads/main.tar.gz" | \
        tar -xz --strip-components=1 -C "$SYSTEM_DIR" --exclude="landing" 2>/dev/null || true
    rm -rf "$SYSTEM_DIR/landing" "$SYSTEM_DIR/.git" "$SYSTEM_DIR/dist" 2>/dev/null || true
fi

# 3. Registrar en SQLite los paquetes que TDM va a instalar
PACKAGES_TO_INSTALL="python x11-repo dbus tigervnc xorg-xauth xorg-xsetroot procps tmux"
if command -v python3 >/dev/null 2>&1 && [ -f "$SYSTEM_DIR/tdm/core/manifest.py" ]; then
    PYTHONPATH="$SYSTEM_DIR" python3 -c "
try:
    from tdm.core.manifest import manifest_ledger
    manifest_ledger.record_packages_if_new('$PACKAGES_TO_INSTALL'.split(), component='minimal')
except Exception:
    pass
" 2>/dev/null || true
fi

echo "[3/4] Instalando dependencias base (Python, x11-repo, TigerVNC, D-Bus)..."
pkg install -y x11-repo || true
apt-get update -y || pkg update -y || true
pkg install -y python dbus tigervnc xorg-xauth xorg-xsetroot procps tmux || true
apt-get --only-upgrade install -y libc++ >/dev/null 2>&1 || true

echo "[TDM] Optimizando espacio en disco..."
apt-get autoremove -y --purge >/dev/null 2>&1 || true
apt-get autoclean -y >/dev/null 2>&1 || true
apt-get clean >/dev/null 2>&1 || true

# Registrar enlace .pth en Python site-packages hacia el directorio del sistema
if command -v python3 >/dev/null 2>&1; then
    PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    SITE_PACKAGES="$PREFIX/lib/python${PYTHON_VER}/site-packages"
    if [ -d "$SITE_PACKAGES" ]; then
        echo "$SYSTEM_DIR" > "$SITE_PACKAGES/tdm.pth"
    fi
fi

# 4. Crear ejecutable global 'tdm' en el sistema
BIN_PATH="$PREFIX/bin/tdm"
cat << 'EOF' > "$BIN_PATH"
#!/data/data/com.termux/files/usr/bin/bash
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
PROJECT_DIR="${PREFIX}/opt/termux-display-manager"

if [ ! -d "$PROJECT_DIR" ]; then
    PROJECT_DIR="${PREFIX}/share/termux-display-manager"
fi

if [ ! -d "$PROJECT_DIR" ]; then
    DEV_DIR="$(cd "$(dirname "$0")/.." && pwd)"
    if [ -f "$DEV_DIR/pyproject.toml" ]; then
        PROJECT_DIR="$DEV_DIR"
    else
        PROJECT_DIR="${HOME}/termux-display-manager"
    fi
fi

export PYTHONPATH="$PROJECT_DIR:${PYTHONPATH}"
exec python3 -m tdm.cli.main "$@"
EOF
chmod +x "$BIN_PATH" || true
chmod +x "$SYSTEM_DIR"/tdm/scripts/*.sh "$SYSTEM_DIR"/*.sh 2>/dev/null || true

echo "====================================================="
echo "[TDM] Backend instalado con éxito en el sistema ($SYSTEM_DIR)"
echo "[TDM] Iniciando TDM Service en segundo plano..."
echo "====================================================="

pkill -f "tdm.cli.main" 2>/dev/null || true
sleep 0.5
PYTHONPATH="$SYSTEM_DIR" "$BIN_PATH" service restart

echo "[TDM] Core activo. Acceso Web: http://127.0.0.1:19050"
