#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Instalación Mínima / Fundamental
# ==============================================================================
# Solo instala lo estrictamente necesario para que el núcleo de TDM, la API REST,
# y la comunicación con el APK funcionen. No instala servidores gráficos pesados
# hasta que el usuario los solicite bajo demanda.
# ==============================================================================

set -e

echo "====================================================="
echo "⚡ [TDM] Instalando Dependencias Mínimas Fundamentales"
echo "====================================================="

# 1. Asegurar repositorios oficiales
echo "[*] Actualizando repositorios..."
pkg update -y

echo "[*] Añadiendo repositorio x11-repo..."
pkg install -y x11-repo

# 2. Herramientas base del sistema y Python
echo "[*] Instalando Python y utilidades de proceso..."
pkg install -y \
    python \
    procps \
    psmisc \
    net-tools \
    dbus

# 3. Directorios de configuración y runtime de TDM
echo "[*] Creando estructura de directorios en $HOME/.tdm..."
mkdir -p "$HOME/.tdm/run"
mkdir -p "$HOME/.tdm/logs"
mkdir -p "$HOME/.tdm/sessions"
mkdir -p "$HOME/.termux"

# 4. Configurar allow-external-apps para permitir comunicación fluida con la App Android
if [ -f "$HOME/.termux/termux.properties" ]; then
    if ! grep -q "allow-external-apps" "$HOME/.termux/termux.properties"; then
        echo "allow-external-apps = true" >> "$HOME/.termux/termux.properties"
    fi
else
    echo "allow-external-apps = true" > "$HOME/.termux/termux.properties"
fi

echo "====================================================="
echo "✅ [TDM] Instalación mínima completada en tiempo récord."
echo "💡 Los servidores gráficos (Termux:X11, noVNC, xrdp) se instalarán bajo demanda."
echo "====================================================="
