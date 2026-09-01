"""
Constantes globales y puertos predeterminados para Termux Display Manager (TDM).
"""

# Identificadores de Servidores / Backends
BACKEND_TERMUX_X11 = "termux-x11"
BACKEND_NOVNC = "novnc"
BACKEND_VNC = "vnc"
BACKEND_RDP = "rdp"

# Modos de Sesión
SESSION_MODE_DESKTOP = "desktop"
SESSION_MODE_TERMINAL = "terminal"

# Puertos Predeterminados (Rango 1905x)
PORT_TDM_SERVER = 19050
PORT_TDM_SERVER_ALT = 19051
PORT_NOVNC_DEFAULT = 19052
PORT_VNC_DEFAULT = 19053
PORT_RDP_DEFAULT = 19054
PORT_PULSEAUDIO = 19055

# Ajustes de Pantalla Predeterminados
DEFAULT_DISPLAY_NUM = 0
DEFAULT_DISPLAY_STR = ":0"
DEFAULT_RESOLUTION = "1080x2400"
DEFAULT_DPI = 96
DEFAULT_COLOR_DEPTH = 24

# Estados del Ciclo de Vida
STATE_IDLE = "idle"
STATE_STARTING = "starting"
STATE_RUNNING = "running"
STATE_STOPPING = "stopping"
STATE_STOPPED = "stopped"
STATE_FAILED = "failed"
STATE_CRASHED = "crashed"

import os
import shutil
from typing import Optional

PREFIX = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
_current_path = os.environ.get("PATH", "")
_prefix_bin = f"{PREFIX}/bin"
_prefix_applets = f"{PREFIX}/bin/applets"
if _prefix_bin not in _current_path:
    os.environ["PATH"] = f"{_prefix_bin}:{_prefix_applets}:{_current_path}"

def find_binary(cand: str) -> Optional[str]:
    """Busca un ejecutable considerando rutas nativas de Termux y del sistema."""
    if not cand:
        return None
    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    search_dirs = [
        f"{prefix}/bin",
        f"{prefix}/bin/applets",
        "/data/data/com.termux/files/usr/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/system/bin",
        "/system/xbin",
    ]
    env_p = os.environ.get("PATH", "")
    if env_p:
        search_dirs = env_p.split(":") + search_dirs

    combined_path = ":".join(dict.fromkeys(p for p in search_dirs if p))
    
    # 1. shutil.which con PATH ampliado
    found = shutil.which(cand, path=combined_path)
    if found:
        return found
        
    # 2. Comprobación directa de archivo ejecutable
    for d in search_dirs:
        full_p = os.path.join(d, cand)
        if os.path.isfile(full_p) and os.access(full_p, os.X_OK):
            return full_p
            
    return None

