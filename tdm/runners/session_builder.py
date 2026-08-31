import os
import stat
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from tdm.discovery.desktops import get_desktop_by_id
from tdm.config import TDM_RUN_DIR

def build_session_script(display_num: int, desktop_id: str, custom_command: Optional[str] = None, custom_list=None) -> Path:
    """Genera un script ejecutable limpio para iniciar el entorno de escritorio en el display indicado."""
    TDM_RUN_DIR.mkdir(parents=True, exist_ok=True)
    script_path = TDM_RUN_DIR / f"session-display-{display_num}.sh"
    
    de_info = get_desktop_by_id(desktop_id, custom_list) if not custom_command else None
    
    lines = [
        "#!/usr/bin/env sh",
        f"# Auto-generated session script for Display :{display_num}",
        "PREFIX=\"${PREFIX:-/data/data/com.termux/files/usr}\"",
        "export PATH=\"$PREFIX/bin:$PATH\"",
        f"export DISPLAY=:{display_num}",
        "",
        "# Esperar a que el socket X11 esté disponible",
        "for i in $(seq 1 30); do",
        f"    if [ -e /tmp/.X11-unix/X{display_num} ] || [ -e /tmp/X11-pipe/X{display_num} ] || [ -e \"$PREFIX/tmp/.X11-unix/X{display_num}\" ] || xdpyinfo -display :{display_num} >/dev/null 2>&1; then",
        "        break",
        "    fi",
        "    sleep 0.2",
        "done",
        "",
        "# Iniciar D-Bus si está disponible",
        "if command -v dbus-launch >/dev/null 2>&1 && [ -z \"$DBUS_SESSION_BUS_ADDRESS\" ]; then",
        "    eval $(dbus-launch --sh-syntax)",
        "    export DBUS_SESSION_BUS_ADDRESS",
        "    export DBUS_SESSION_BUS_PID",
        "fi",
        "",
        "# Fondo de ventana neutro si existe xsetroot",
        "if command -v xsetroot >/dev/null 2>&1; then",
        "    xsetroot -solid '#1e1e2e'",
        "fi",
        "",
        "# Lanzar la aplicación Android Termux:X11",
        "if command -v am >/dev/null 2>&1; then",
        "    am start --user 0 -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n com.termux.x11/com.termux.x11.MainActivity >/dev/null 2>&1 || \\",
        "    am start -n com.termux.x11/com.termux.x11.MainActivity >/dev/null 2>&1 || true",
        "fi",
        ""
    ]
    
    if custom_command:
        lines.append(f"# Ejecutar aplicación personalizada")
        lines.append(f"exec {custom_command}")
    elif desktop_id == "kde":
        lines.append("# Ejecutar KDE Plasma")
        lines.append("export KDE_FULL_SESSION=true")
        lines.append("if command -v startplasma-x11 >/dev/null 2>&1; then")
        lines.append("    exec startplasma-x11")
        lines.append("elif command -v plasma-session >/dev/null 2>&1; then")
        lines.append("    exec plasma-session")
        lines.append("else")
        lines.append("    kwin_x11 &")
        lines.append("    exec plasmashell")
        lines.append("fi")
    elif desktop_id == "mate":
        lines.append("# Ejecutar MATE Desktop")
        lines.append("export GSETTINGS_BACKEND=keyfile")
        lines.append("exec mate-session")
    elif desktop_id in ["xfce", "xfce4"]:
        lines.append("# Configurar logo de menú en panel XFCE")
        lines.append("LOGO_PATH=\"$HOME/.tdm/assets/xfce.gif\"")
        lines.append("if [ -f \"$LOGO_PATH\" ] && command -v xfconf-query >/dev/null 2>&1; then")
        lines.append("    (sleep 1 && xfconf-query -c xfce4-panel -p /plugins/plugin-1/button-icon -s \"$LOGO_PATH\" --create -t string >/dev/null 2>&1) &")
        lines.append("fi")
        lines.append("# Ejecutar XFCE4")
        lines.append("if command -v xfce4-session >/dev/null 2>&1; then")
        lines.append("    exec xfce4-session")
        lines.append("else")
        lines.append("    exec startxfce4")
        lines.append("fi")
    elif desktop_id == "lxqt":
        lines.append("# Ejecutar LXQt")
        lines.append("exec startlxqt")
    elif desktop_id == "i3":
        lines.append("# Ejecutar i3 Window Manager")
        lines.append("exec i3")
    elif desktop_id == "openbox":
        lines.append("# Ejecutar Openbox")
        lines.append("if command -v tint2 >/dev/null 2>&1; then tint2 & fi")
        lines.append("exec openbox-session")
    else:
        executable = de_info.get("executable") if de_info else None
        if executable:
            lines.append(f"exec {executable}")
        else:
            lines.append(f"exec xterm || exec sh")

    script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    
    try:
        script_path.chmod(0o755)
    except Exception:
        pass

    return script_path
