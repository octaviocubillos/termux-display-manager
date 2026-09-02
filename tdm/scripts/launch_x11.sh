#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# 🚀 [TDM] Lanzador Nativo de Termux:X11 + Entorno de Escritorio
# ==============================================================================
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
export PATH="$PREFIX/bin:$PATH"
export TMPDIR="$PREFIX/tmp"
export DISPLAY=:0

# Configurar shell por defecto (bash a menos que el usuario lo haya cambiado en ~/.termux/shell)
export SHELL="${SHELL:-$PREFIX/bin/bash}"
if [ -f "$HOME_DIR/.termux/shell" ]; then
    CUSTOM_SHELL=$(cat "$HOME_DIR/.termux/shell" | tr -d ' \t\r\n')
    if [ -x "$CUSTOM_SHELL" ]; then export SHELL="$CUSTOM_SHELL"; fi
fi

# Establecer ubicación por defecto en el directorio de usuario (HOME)
cd "$HOME_DIR" 2>/dev/null || true

export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export GDK_BACKEND=x11
export QT_QPA_PLATFORM=xcb

export XDG_RUNTIME_DIR="$HOME_DIR/.tdm/run/user-$(id -u)-display-0"
mkdir -p "$XDG_RUNTIME_DIR" "$TMPDIR"
chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null || true

echo "====================================================="
echo "⚡ [TDM] Iniciando Servidor Gráfico Termux:X11 (:0)..."
echo "====================================================="

# 1. Matar instancias previas y limpiar sockets
pkill -f termux-x11 || true
pkill -f xfce4-session || true
rm -rf /tmp/.X11-unix/X0 /tmp/X11-pipe/X0 "$PREFIX/tmp/.X11-unix/X0" "$PREFIX/tmp/X11-pipe/X0" 2>/dev/null || true

# 2. Iniciar servidor termux-x11 en background
termux-x11 :0 -ac -listen tcp &
sleep 1

# 3. Lanzar la aplicación Android Termux:X11 al frente
echo "[*] Abriendo la aplicación Termux:X11 en pantalla..."
am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity 2>/dev/null || am start -n com.termux.x11/com.termux.x11.MainActivity 2>/dev/null || true

# 4. Iniciar D-Bus y XFCE4
if command -v dbus-launch >/dev/null 2>&1 && [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    eval $(dbus-launch --sh-syntax)
    export DBUS_SESSION_BUS_ADDRESS
    export DBUS_SESSION_BUS_PID
fi

if command -v xsetroot >/dev/null 2>&1; then
    xsetroot -solid '#1e1e2e' 2>/dev/null || true
fi

echo "====================================================="
echo "🐭 [TDM] Iniciando sesión de escritorio XFCE4..."
echo "====================================================="

if command -v xfce4-session >/dev/null 2>&1; then
    exec xfce4-session
elif command -v startxfce4 >/dev/null 2>&1; then
    exec startxfce4
else
    exec xfce4-terminal
fi
