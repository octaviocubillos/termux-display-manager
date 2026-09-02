#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# 🛑 [TDM] Script de Apagado Completo de Pantalla y Entorno Gráfico (UI)
# ==============================================================================
set -e

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
export PATH="$PREFIX/bin:$PATH"

echo "====================================================="
echo "🛑 [TDM] Apagando entorno gráfico, servidores y procesos..."
echo "====================================================="

# 1. Purgado exhaustivo de todos los procesos en DISPLAY=: y gestores de UI mediante Linux /proc
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import os, signal
target_names = {
    'termux-x11', 'Xvnc', 'vncserver', 'xrdp', 'xrdp-sesman', 'websockify',
    'xfce4-session', 'xfce4-panel', 'xfce4-power-manager', 'xfce4-notifyd',
    'xfwm4', 'xfdesktop', 'thunar', 'wrapper-2.0', 'xfconfd', 'xfsettingsd',
    'startplasma-x11', 'plasmashell', 'kwin_x11', 'plasma-session', 'kded5', 'klauncher', 'ksmserver', 'kaccess',
    'mate-session', 'mate-panel', 'marco', 'caja', 'mate-settings-daemon',
    'startlxqt', 'lxqt-session', 'pcmanfm-qt', 'lxqt-panel', 'lxqt-globalkeysd', 'lxqt-notificationd',
    'openbox', 'openbox-session', 'tint2', 'i3', 'i3bar', 'i3status',
    'xterm', 'qterminal', 'mate-terminal', 'xfce4-terminal',
    'pulseaudio', 'virgl_test_server'
}
for entry in os.listdir('/proc'):
    if not entry.isdigit(): continue
    pid = int(entry)
    if pid == os.getpid() or pid == 1: continue
    try:
        comm = open(f'/proc/{pid}/comm').read().strip() if os.path.exists(f'/proc/{pid}/comm') else ''
        cmdline = open(f'/proc/{pid}/cmdline', 'rb').read().decode('utf-8', errors='ignore').replace('\x00', ' ') if os.path.exists(f'/proc/{pid}/cmdline') else ''
        environ_str = open(f'/proc/{pid}/environ', 'rb').read().decode('utf-8', errors='ignore') if os.path.exists(f'/proc/{pid}/environ') else ''
        
        if any(safe in cmdline for safe in ['tdm.cli.main', 'tdm.agent.client', 'tdm hub', 'tdm server']):
            continue

        if 'DISPLAY=:' in environ_str or comm in target_names or comm.startswith('xfce4-') or comm.startswith('mate-') or comm.startswith('lxqt-') or comm.startswith('plasma-'):
            os.kill(pid, signal.SIGKILL)
    except Exception: pass
" 2>/dev/null || true
fi

# 2. Respaldo por nombres exactos con pkill y killall
for proc in xfce4-session xfce4-panel xfwm4 xfdesktop thunar wrapper-2.0 xfsettingsd plasmashell startplasma-x11 kwin_x11 mate-session mate-panel marco caja startlxqt lxqt-session pcmanfm-qt lxqt-panel openbox i3 i3bar i3status termux-x11 Xvnc xrdp websockify virgl_test_server pulseaudio aterm; do
    pkill -9 -x "$proc" 2>/dev/null || true
done

# 3. Cerrar la app Android Termux:X11
if command -v am >/dev/null 2>&1; then
    am broadcast -a com.termux.x11.ACTION_STOP >/dev/null 2>&1 || true
    am force-stop com.termux.x11 >/dev/null 2>&1 || true
fi

# 4. Limpiar sockets y archivos temporales de X11
rm -rf /tmp/.X11-unix /tmp/.X*-lock /tmp/X11-pipe \
       "$PREFIX/tmp/.X11-unix" "$PREFIX/tmp/.X*-lock" "$PREFIX/tmp/X11-pipe" 2>/dev/null || true

echo "====================================================="
echo "✅ [TDM] Pantalla y entorno gráfico apagados al 100%."
echo "====================================================="
