#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Instalación Mínima & Gestor de Servicios Termux
# ==============================================================================
# Instala dependencias base y configura el servicio TDM bajo termux-services (sv)
# ==============================================================================

set -e

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
HOME="${HOME:-/data/data/com.termux/files/home}"
PROJECT_DIR="${HOME}/termux-display-manager"

echo "====================================================="
echo "⚡ [TDM] Instalando Dependencias Mínimas & Gestor de Servicios"
echo "====================================================="

# 1. Asegurar repositorios oficiales
echo "[*] Actualizando repositorios..."
pkg update -y || true

echo "[*] Añadiendo repositorio x11-repo..."
pkg install -y x11-repo || true

# 2. Herramientas base del sistema, Python y Gestor de Servicios de Termux
echo "[*] Instalando termux-services, Python y utilidades de proceso..."
pkg install -y \
    termux-services \
    python \
    procps \
    psmisc \
    net-tools \
    dbus

# 3. Estructura de directorios de configuración y runtime
echo "[*] Creando estructura de directorios..."
mkdir -p "$HOME/.tdm/run"
mkdir -p "$HOME/.tdm/logs"
mkdir -p "$HOME/.tdm/assets"
mkdir -p "$HOME/.tdm/sessions"
mkdir -p "$HOME/.termux"

# 4. Configurar allow-external-apps para permitir comunicación con la App Android
if [ -f "$HOME/.termux/termux.properties" ]; then
    if ! grep -q "allow-external-apps" "$HOME/.termux/termux.properties"; then
        echo "allow-external-apps = true" >> "$HOME/.termux/termux.properties"
    fi
else
    echo "allow-external-apps = true" > "$HOME/.termux/termux.properties"
fi

# 5. Configurar el Servicio TDM en el Gestor de Servicios de Termux (termux-services / runit)
echo "[*] Configurando servicio 'tdm' en termux-services ($PREFIX/var/service/tdm)..."
SERVICE_DIR="$PREFIX/var/service/tdm"
mkdir -p "$SERVICE_DIR/log"

cat << 'EOS' > "$SERVICE_DIR/run"
#!/data/data/com.termux/files/usr/bin/sh
exec 2>&1

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
HOME="${HOME:-/data/data/com.termux/files/home}"
PROJECT_DIR="${HOME}/termux-display-manager"

# Adquirir Wake-Lock para evitar suspensión por ahorro de energía
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock || true
fi

export PATH="$PREFIX/bin:$PATH"
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
export HOME="$HOME"
export PREFIX="$PREFIX"

exec python3 -m tdm.cli.main server --port 19050
EOS

cat << 'EOS' > "$SERVICE_DIR/log/run"
#!/data/data/com.termux/files/usr/bin/sh
LOG_DIR="${HOME:-/data/data/com.termux/files/home}/.tdm/logs"
mkdir -p "$LOG_DIR"
exec svlogd -tt "$LOG_DIR"
EOS

chmod +x "$SERVICE_DIR/run"
chmod +x "$SERVICE_DIR/log/run"

# 6. Habilitar servicio TDM si termux-services está activo
if command -v sv-enable >/dev/null 2>&1; then
    echo "[*] Habilitando servicio 'tdm' en el gestor de servicios de Termux..."
    sv-enable tdm 2>/dev/null || true
fi

# 7. Instalar lanzador binario 'tdm'
if [ -f "$PROJECT_DIR/tdm/scripts/install_tdm.sh" ]; then
    bash "$PROJECT_DIR/tdm/scripts/install_tdm.sh" || true
elif [ -f "./tdm/scripts/install_tdm.sh" ]; then
    bash "./tdm/scripts/install_tdm.sh" || true
fi

echo "====================================================="
echo "✅ [TDM] Instalación mínima completada."
echo "💡 El servicio TDM ahora está gestionado por 'termux-services' (sv)."
echo "   • Iniciar/Habilitar: sv-enable tdm   (o tdm service start)"
echo "   • Detener/Deshabilitar: sv-disable tdm (o tdm service stop)"
echo "   • Estado: sv status tdm              (o tdm service status)"
echo "====================================================="
