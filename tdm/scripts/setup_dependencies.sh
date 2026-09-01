#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Script de Instalación de Dependencias
# ==============================================================================
# Este script instala y configura todas las herramientas, repositorios,
# servidores de pantalla, librerías y utilidades necesarias para TDM en Termux.
# ==============================================================================

set -e

echo "====================================================="
echo "🚀 [TDM] Instalando Dependencias y Servidores Gráficos"
echo "====================================================="

# 1. Asegurar repositorios oficiales
echo "[*] Actualizando repositorios de Termux..."
pkg update -y

echo "[*] Asegurando repositorio x11-repo..."
pkg install -y x11-repo || true
pkg update -y || apt-get update -y || true

# 2. Instalar herramientas base del sistema y Python
echo "[*] Instalando herramientas base y Python..."
pkg install -y \
    python \
    python-pip \
    git \
    curl \
    wget \
    tar \
    procps \
    psmisc \
    net-tools \
    tmux \
    qrencode || true

# 3. Instalar servidores gráficos y de pantalla (Backends)
echo "[*] Instalando servidores gráficos (Termux:X11, TigerVNC, noVNC, xrdp)..."
pkg install -y \
    termux-x11-nightly || true

pkg install -y \
    tigervnc \
    xorg-xauth \
    xorg-xhost \
    xorg-xrdb \
    xorg-xsetroot \
    xdpyinfo \
    xdotool || true

# noVNC y WebSockets
pkg install -y \
    novnc \
    websockify || true

# 4. Instalar soporte de Audio y D-Bus
echo "[*] Instalando soporte de Audio (PulseAudio) y D-Bus..."
pkg install -y \
    pulseaudio \
    dbus

# 5. Instalar fuentes y temas básicos
echo "[*] Instalando fuentes básicas para renderizado X11..."
pkg install -y \
    fontconfig \
    fontconfig-utils \
    fonts-noto \
    fonts-noto-cjk \
    dejavu-fonts || true

# 6. Directorios de configuración y runtime
echo "[*] Creando estructura de directorios en $HOME/.tdm..."
mkdir -p "$HOME/.tdm/run"
mkdir -p "$HOME/.tdm/logs"
mkdir -p "$HOME/.tdm/sessions"
mkdir -p "$HOME/.termux"

# Configurar allow-external-apps para permitir comunicación con el APK
if [ -f "$HOME/.termux/termux.properties" ]; then
    if ! grep -q "allow-external-apps" "$HOME/.termux/termux.properties"; then
        echo "allow-external-apps = true" >> "$HOME/.termux/termux.properties"
    fi
else
    echo "allow-external-apps = true" > "$HOME/.termux/termux.properties"
fi

echo "====================================================="
echo "✅ [TDM] Todas las dependencias base han sido instaladas con éxito."
echo "====================================================="
