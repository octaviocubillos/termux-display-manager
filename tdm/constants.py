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
