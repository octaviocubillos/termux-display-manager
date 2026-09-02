#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Detector Universal de Entornos de Escritorio
# Devuelve: id|nombre|ejecutable|instalado(true/false)
# ==============================================================================

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
SEARCH_DIRS="$PREFIX/bin /data/data/com.termux/files/usr/bin /usr/local/bin /usr/bin /bin"

find_exec() {
    local cmd="$1"
    for dir in $SEARCH_DIRS; do
        if [ -f "$dir/$cmd" ] && [ -x "$dir/$cmd" ]; then
            echo "$dir/$cmd"
            return 0
        fi
    done
    if command -v "$cmd" >/dev/null 2>&1; then
        command -v "$cmd"
        return 0
    fi
    return 1
}

# 1. XFCE4
for bin in xfce4-session startxfce4; do
    if EXEC_PATH="$(find_exec "$bin")"; then
        echo "xfce4|XFCE4 Desktop|$EXEC_PATH|true"
        exit 0
    fi
done

# 2. i3 Window Manager
for bin in i3; do
    if EXEC_PATH="$(find_exec "$bin")"; then
        echo "i3|i3 Window Manager|$EXEC_PATH|true"
        exit 0
    fi
done

# 3. KDE Plasma
for bin in startplasma-x11 plasma-session; do
    if EXEC_PATH="$(find_exec "$bin")"; then
        echo "kde|KDE Plasma|$EXEC_PATH|true"
        exit 0
    fi
done

# 4. MATE Desktop
for bin in mate-session; do
    if EXEC_PATH="$(find_exec "$bin")"; then
        echo "mate|MATE Desktop|$EXEC_PATH|true"
        exit 0
    fi
done

# 5. LXQt
for bin in startlxqt lxqt-session; do
    if EXEC_PATH="$(find_exec "$bin")"; then
        echo "lxqt|LXQt Desktop|$EXEC_PATH|true"
        exit 0
    fi
done

# 6. Openbox
for bin in openbox-session openbox; do
    if EXEC_PATH="$(find_exec "$bin")"; then
        echo "openbox|Openbox Window Manager|$EXEC_PATH|true"
        exit 0
    fi
done

# 7. Terminal Mode
for bin in aterm xfce4-terminal mate-terminal qterminal konsole xterm st; do
    if EXEC_PATH="$(find_exec "$bin")"; then
        echo "terminal|Modo Terminal X11|$EXEC_PATH|true"
        exit 0
    fi
done

# Ninguno detectado
echo "none|Ninguno||false"
exit 0
