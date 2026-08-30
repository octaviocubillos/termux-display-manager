#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Diagnóstico y Verificación del Sistema
# ==============================================================================

echo "====================================================="
echo "🔍 [TDM] Diagnóstico del Entorno Termux y Dependencias"
echo "====================================================="

check_cmd() {
    local name="$1"
    local cmd="$2"
    local optional="$3"
    
    if command -v "$cmd" >/dev/null 2>&1; then
        local path=$(command -v "$cmd")
        echo -e "  [\e[32mOK\e[0m] $name: $path"
        return 0
    else
        if [ "$optional" = "opt" ]; then
            echo -e "  [\e[33mOPCIONAL\e[0m] $name ($cmd no encontrado)"
        else
            echo -e "  [\e[31mFALTA\e[0m] $name ($cmd no encontrado)"
        fi
        return 1
    fi
}

echo ""
echo "📌 1. Entorno Base:"
echo "  • Sistema: $(uname -s) $(uname -m)"
echo "  • Kernel:  $(uname -r)"
echo "  • Usuario: $(id -un) (UID: $(id -u))"
echo "  • PREFIX:  ${PREFIX:-/usr}"
echo "  • HOME:    $HOME"

echo ""
echo "📌 2. Lenguaje y Herramientas Base:"
check_cmd "Python 3" "python3"
check_cmd "Python PIP" "pip" "opt"
check_cmd "D-Bus Launch" "dbus-launch" "opt"
check_cmd "PulseAudio" "pulseaudio" "opt"

echo ""
echo "📌 3. Servidores de Pantalla (Backends):"
check_cmd "Termux:X11 Server" "termux-x11" "opt"
check_cmd "TigerVNC (Xvnc)" "Xvnc" "opt"
check_cmd "noVNC / Websockify" "websockify" "opt"
check_cmd "xrdp (RDP Server)" "xrdp" "opt"
check_cmd "X11 Display Info (xdpyinfo)" "xdpyinfo" "opt"
check_cmd "X11 Root Tool (xsetroot)" "xsetroot" "opt"

echo ""
echo "📌 4. Entornos de Escritorio Nativos Detectados:"
check_cmd "KDE Plasma" "startplasma-x11" "opt"
check_cmd "MATE Desktop" "mate-session" "opt"
check_cmd "XFCE4" "xfce4-session" "opt"
check_cmd "LXQt" "startlxqt" "opt"
check_cmd "i3 Window Manager" "i3" "opt"
check_cmd "Openbox" "openbox-session" "opt"
check_cmd "Fluxbox" "startfluxbox" "opt"

echo ""
echo "📌 5. Emuladores de Terminal (Modo Terminal X11):"
check_cmd "Konsole" "konsole" "opt"
check_cmd "MATE Terminal" "mate-terminal" "opt"
check_cmd "XFCE Terminal" "xfce4-terminal" "opt"
check_cmd "QTerminal" "qterminal" "opt"
check_cmd "XTerm" "xterm" "opt"

echo ""
echo "====================================================="
echo "✅ [TDM] Diagnóstico finalizado."
echo "====================================================="
