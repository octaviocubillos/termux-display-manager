"""
Catálogo centralizado y unificado de Entornos de Escritorio y Servidores Gráficos.
Fuente única de verdad (Single Source of Truth) para TDM.
"""

from typing import Dict, List, Any, Optional
from tdm.constants import (
    BACKEND_TERMUX_X11,
    BACKEND_NOVNC,
    BACKEND_VNC,
    BACKEND_RDP,
    PORT_VNC_DEFAULT,
    PORT_NOVNC_DEFAULT,
    PORT_RDP_DEFAULT,
)

# Catálogo Maestro de Entornos de Escritorio y Window Managers
DESKTOP_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "kde",
        "name": "KDE Plasma",
        "type": "de",
        "description": "Entorno de escritorio moderno, completo y visualmente refinado.",
        "required_disk": "~2.8 GB",
        "ram_usage": "~450 MB",
        "exec_candidates": ["startplasma-x11", "plasma-session", "startplasma-wayland"],
        "packages": ["plasma-desktop", "plasma-workspace", "konsole", "dolphin", "powerdevil", "pavucontrol"],
        "icon": "kde",
        "env_vars": {
            "XDG_CURRENT_DESKTOP": "KDE",
            "DESKTOP_SESSION": "plasma",
            "KDE_FULL_SESSION": "true",
            "KDE_SESSION_VERSION": "5",
            "QT_AUTO_SCREEN_SCALE_FACTOR": "0"
        }
    },
    {
        "id": "mate",
        "name": "MATE Desktop",
        "type": "de",
        "description": "Escritorio tradicional, ligero y altamente responsivo basado en GNOME 2.",
        "required_disk": "~1.6 GB",
        "ram_usage": "~250 MB",
        "exec_candidates": ["mate-session"],
        "packages": ["mate-desktop", "mate-session-manager", "mate-panel", "mate-terminal", "mate-settings-daemon", "marco", "caja", "mate-media", "mate-power-manager", "mate-applets", "pavucontrol"],
        "icon": "mate",
        "env_vars": {
            "XDG_CURRENT_DESKTOP": "MATE",
            "DESKTOP_SESSION": "mate",
            "GSETTINGS_BACKEND": "keyfile"
        }
    },
    {
        "id": "xfce4",
        "name": "XFCE4",
        "type": "de",
        "description": "Entorno ligero, altamente personalizable y de bajo consumo.",
        "required_disk": "~1.2 GB",
        "ram_usage": "~150 MB",
        "exec_candidates": ["xfce4-session", "startxfce4"],
        "packages": ["xfce4", "xfce4-terminal", "thunar", "libxres", "xfce4-pulseaudio-plugin", "xfce4-battery-plugin", "xfce4-power-manager", "pavucontrol"],
        "icon": "xfce",
        "env_vars": {
            "XDG_CURRENT_DESKTOP": "XFCE",
            "DESKTOP_SESSION": "xfce",
            "XFCE4_SESSION_DISABLE_SAVED_SESSION": "1"
        }
    },
    {
        "id": "lxqt",
        "name": "LXQt",
        "type": "de",
        "description": "Entorno ligero y modular basado en Qt.",
        "required_disk": "~1.1 GB",
        "ram_usage": "~180 MB",
        "exec_candidates": ["startlxqt", "lxqt-session"],
        "packages": ["lxqt-session", "lxqt", "qterminal", "pcmanfm-qt", "lxqt-powermanagement", "pavucontrol"],
        "icon": "lxqt",
        "env_vars": {
            "XDG_CURRENT_DESKTOP": "LXQt",
            "DESKTOP_SESSION": "lxqt"
        }
    },
    {
        "id": "i3",
        "name": "i3 Window Manager",
        "type": "wm",
        "description": "Gestor de ventanas en mosaico (Tiling WM) ultrarrápido y manejado por teclado.",
        "required_disk": "~350 MB",
        "ram_usage": "~50 MB",
        "exec_candidates": ["i3"],
        "packages": ["i3", "i3status", "dmenu", "aterm", "pavucontrol", "pulseaudio"],
        "icon": "i3",
        "env_vars": {
            "XDG_CURRENT_DESKTOP": "i3",
            "DESKTOP_SESSION": "i3"
        }
    },
    {
        "id": "openbox",
        "name": "Openbox",
        "type": "wm",
        "description": "Gestor de ventanas flotante ultraligero y altamente configurable.",
        "required_disk": "~450 MB",
        "ram_usage": "~70 MB",
        "exec_candidates": ["openbox-session", "openbox"],
        "packages": ["openbox", "obconf-qt", "tint2", "aterm", "pavucontrol", "pulseaudio"],
        "icon": "openbox",
        "env_vars": {
            "XDG_CURRENT_DESKTOP": "OPENBOX",
            "DESKTOP_SESSION": "openbox"
        }
    },
    {
        "id": "terminal",
        "name": "Modo Terminal X11 (Ultraligero)",
        "type": "terminal",
        "description": "Sesión gráfica pura ejecutando emulador de terminal a pantalla completa.",
        "exec_candidates": ["aterm", "st", "xfce4-terminal", "mate-terminal", "qterminal", "konsole", "xterm"],
        "packages": ["aterm"],
        "icon": "terminal",
        "env_vars": {
            "XDG_CURRENT_DESKTOP": "TERMINAL",
            "DESKTOP_SESSION": "terminal"
        }
    }
]

# Catálogo Maestro de Servidores de Pantalla / Backends
BACKEND_CATALOG: List[Dict[str, Any]] = [
    {
        "id": BACKEND_TERMUX_X11,
        "name": "Termux:X11",
        "description": "Servidor X11 nativo de alto rendimiento para Android. Ideal para pantalla del móvil/tablet (60/120 Hz).",
        "exec_candidates": ["termux-x11"],
        "packages": ["termux-x11-nightly", "x11-repo"],
        "protocols": ["X11"],
        "default_display": ":0",
        "icon": "termux"
    },
    {
        "id": BACKEND_NOVNC,
        "name": "noVNC (Web HTML5)",
        "description": "Visor web directo desde cualquier navegador o WebView sin instalar clientes externos.",
        "exec_candidates": ["websockify", "novnc"],
        "packages": ["tigervnc", "websockify", "novnc"],
        "protocols": ["WebSocket", "HTTP/HTML5"],
        "default_port": PORT_NOVNC_DEFAULT,
        "icon": "globe"
    },
    {
        "id": BACKEND_VNC,
        "name": "VNC Server",
        "description": "Servidor VNC estándar en protocolo RFB. Permite clientes como bVNC en Android o RealVNC en PC.",
        "exec_candidates": ["Xvnc", "vncserver", "tightvncserver"],
        "packages": ["tigervnc", "xorg-xauth", "xorg-xsetroot"],
        "protocols": ["RFB (VNC)"],
        "default_port": PORT_VNC_DEFAULT,
        "icon": "vnc"
    },
    {
        "id": BACKEND_RDP,
        "name": "RDP / Remote Desktop",
        "description": "Acceso remoto con Microsoft RD Client (Android/PC). Levanta Xvnc en :5900 + xrdp si está instalado.",
        "exec_candidates": ["xrdp", "Xvnc", "vncserver"],
        "packages": ["tigervnc", "xrdp"],
        "protocols": ["RDP", "RFB (VNC)"],
        "default_port": PORT_RDP_DEFAULT,
        "vnc_fallback_port": PORT_VNC_DEFAULT,
        "icon": "desktop"
    }
]

def get_desktop_entry(desktop_id: str) -> Optional[Dict[str, Any]]:
    # Normalizar alias comunes
    normalized_id = "xfce4" if desktop_id == "xfce" else desktop_id
    for d in DESKTOP_CATALOG:
        if d["id"] == normalized_id or d["id"] == desktop_id:
            return dict(d)
    return None

def get_backend_entry(backend_id: str) -> Optional[Dict[str, Any]]:
    for b in BACKEND_CATALOG:
        if b["id"] == backend_id:
            return dict(b)
    return None
