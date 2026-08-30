"""
Hub de Reenvío (Relay) y Emparejamiento de Sesiones para TDM Cloud / PWA.
Permite conectar una interfaz Web/PWA alojada en dominio remoto (ej. tdm.oton.cl)
con un agente que se ejecuta dentro de Termux en el dispositivo Android vía WebSockets.
"""

import asyncio
import secrets
import time
from typing import Dict, List, Optional, Any
from tdm.server.websocket import WebSocketConnection

class HubSession:
    """Representa una sesión de vinculación entre un navegador (PWA) y un dispositivo Termux."""
    def __init__(self, token: str):
        self.token = token
        self.created_at = time.time()
        self.last_seen = time.time()
        self.agent_ws: Optional[WebSocketConnection] = None
        self.clients_ws: List[WebSocketConnection] = []
        self.device_info: Dict[str, Any] = {}

    @property
    def is_agent_connected(self) -> bool:
        return self.agent_ws is not None and not self.agent_ws.closed

    async def broadcast_to_clients(self, message: Dict[str, Any]):
        """Envía un mensaje a todos los navegadores conectados a este token."""
        dead_clients = []
        for ws in self.clients_ws:
            if ws.closed:
                dead_clients.append(ws)
            else:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead_clients.append(ws)
        for dc in dead_clients:
            if dc in self.clients_ws:
                self.clients_ws.remove(dc)

    async def send_to_agent(self, message: Dict[str, Any]) -> bool:
        """Envía una orden directa al agente en Termux."""
        if not self.is_agent_connected:
            return False
        try:
            await self.agent_ws.send_json(message)
            return True
        except Exception:
            self.agent_ws = None
            return False


class HubManager:
    """Gestor global de sesiones y emparejamiento."""
    def __init__(self):
        self.sessions: Dict[str, HubSession] = {}
        self._lock = asyncio.Lock()

    def get_or_create_session(self, token: Optional[str] = None) -> HubSession:
        if not token:
            token = f"tdm-{secrets.token_hex(4)}"
        if token not in self.sessions:
            self.sessions[token] = HubSession(token)
        return self.sessions[token]

    def get_session(self, token: str) -> Optional[HubSession]:
        return self.sessions.get(token)

    async def register_agent(self, token: str, ws: WebSocketConnection, device_info: Dict[str, Any] = None):
        session = self.get_or_create_session(token)
        session.agent_ws = ws
        session.device_info = device_info or {}
        session.last_seen = time.time()
        
        await session.broadcast_to_clients({
            "type": "agent_connected",
            "token": token,
            "device_info": session.device_info,
            "message": "Dispositivo Termux conectado y listo."
        })

    async def unregister_agent(self, token: str):
        session = self.get_session(token)
        if session:
            session.agent_ws = None
            await session.broadcast_to_clients({
                "type": "agent_disconnected",
                "token": token,
                "message": "El agente de Termux se ha desconectado."
            })

    async def register_client(self, token: str, ws: WebSocketConnection):
        session = self.get_or_create_session(token)
        if ws not in session.clients_ws:
            session.clients_ws.append(ws)

        await ws.send_json({
            "type": "pairing_status",
            "token": session.token,
            "agent_connected": session.is_agent_connected,
            "device_info": session.device_info
        })

    async def unregister_client(self, token: str, ws: WebSocketConnection):
        session = self.get_session(token)
        if session and ws in session.clients_ws:
            session.clients_ws.remove(ws)

    async def delete_session(self, token: str):
        session = self.get_session(token)
        if session:
            if session.agent_ws and not session.agent_ws.closed:
                try:
                    await session.agent_ws.send_json({"type": "uninstall"})
                except Exception:
                    pass
            for ws in list(session.clients_ws):
                if not ws.closed:
                    try:
                        await ws.send_json({
                            "type": "session_deleted",
                            "token": token,
                            "message": "Dispositivo eliminado y desvinculado."
                        })
                    except Exception:
                        pass
            if token in self.sessions:
                del self.sessions[token]

    def generate_setup_script(self, base_url: str, token: str) -> str:
        """Genera el script de instalación completa autónomo y robusto."""
        return f"""#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# 🚀 [TDM] Instalador Automático de Backend y Vinculación ({base_url})
# ==============================================================================
set -e
export DEBIAN_FRONTEND=noninteractive

PREFIX="${{PREFIX:-/data/data/com.termux/files/usr}}"
HOME_DIR="${{HOME:-/data/data/com.termux/files/home}}"
TMPDIR="${{TMPDIR:-$PREFIX/tmp}}"
mkdir -p "$TMPDIR"
export PATH="$PREFIX/bin:$PATH"

echo -e "\\033[1;34m=====================================================\\033[0m"
echo -e "\\033[1;34m🚀 Instalando Backend de Termux Display Manager (TDM)\\033[0m"
echo -e "\\033[1;34m=====================================================\\033[0m"

# 1. Habilitar x11-repo e instalar dependencias del sistema
echo -e "\\033[1;33m[1/3] Habilitando repositorio x11-repo y Python...\\033[0m"
apt-get update -y || true
apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" openssl x11-repo python || true

# 2. Instalar componentes Xorg, D-Bus y Servidores Gráficos (Termux:X11, VNC)
echo -e "\\033[1;33m[2/3] Instalando dependencias gráficas y servidores (Termux:X11, VNC, D-Bus)...\\033[0m"
apt-get update -y || true
apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" dbus xorg-xauth xorg-xsetroot procps termux-x11-nightly tigervnc || true

# 3. Descargar y configurar motor TDM mediante script Python seguro
echo -e "\\033[1;33m[3/3] Descargando y configurando motor TDM Core...\\033[0m"
cat << 'EOF_PY' > "$TMPDIR/setup_tdm.py"
import os, sys, urllib.request, tarfile, ssl

prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
home = os.environ.get("HOME", "/data/data/com.termux/files/home")
tmpdir = os.path.join(prefix, "tmp")
tdm_dir = os.path.join(home, "termux-display-manager")
os.makedirs(tdm_dir, exist_ok=True)
os.makedirs(tmpdir, exist_ok=True)
os.makedirs(os.path.join(home, ".tdm", "logs"), exist_ok=True)
os.makedirs(os.path.join(home, ".tdm", "run"), exist_ok=True)
os.makedirs(os.path.join(home, ".tdm", "config"), exist_ok=True)

termux_dir = os.path.join(home, ".termux")
os.makedirs(termux_dir, exist_ok=True)
with open(os.path.join(termux_dir, "termux.properties"), "w") as f:
    f.write("allow-external-apps = true\\n")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

bundle_path = os.path.join(tmpdir, "tdm-bundle.tar.gz")
base_url = sys.argv[1] if len(sys.argv) > 1 else "https://tdm.oton.cl"
req = urllib.request.Request(base_url + "/tdm-bundle.tar.gz", headers={{"User-Agent": "TDM-Installer"}})
with urllib.request.urlopen(req, context=ctx) as r, open(bundle_path, "wb") as f:
    f.write(r.read())

with tarfile.open(bundle_path, "r:gz") as t:
    t.extractall(path=tdm_dir)

if os.path.exists(bundle_path):
    os.remove(bundle_path)

py_ver = str(sys.version_info.major) + "." + str(sys.version_info.minor)
sp = os.path.join(prefix, "lib", "python" + py_ver, "site-packages")
os.makedirs(sp, exist_ok=True)
with open(os.path.join(sp, "tdm.pth"), "w") as f:
    f.write(tdm_dir + "\\n")

bin_path = os.path.join(prefix, "bin", "tdm")
wrapper_content = "#!/data/data/com.termux/files/usr/bin/bash\\n"
wrapper_content += 'export PATH="/data/data/com.termux/files/usr/bin:$PATH"\\n'
wrapper_content += 'export PYTHONPATH="' + tdm_dir + ':$PYTHONPATH"\\n'
wrapper_content += 'exec python3 -m tdm.cli.main "$@"\\n'

with open(bin_path, "w") as f:
    f.write(wrapper_content)
os.chmod(bin_path, 0o755)

print("[✓] TDM Core desempaquetado correctamente")
EOF_PY

python3 "$TMPDIR/setup_tdm.py" "{base_url}"
rm -f "$TMPDIR/setup_tdm.py"

echo -e "\\033[1;32m=====================================================\\033[0m"
echo -e "\\033[1;32m✓ ¡Backend de TDM instalado y listo!\\033[0m"
echo -e "\\033[1;32m=====================================================\\033[0m"

# 4. Configurar Permisos de Android para Termux:X11 y Wake-Lock
echo -e "\\033[1;36m[*] Configurando permisos del sistema para Termux:X11...\\033[0m"
mkdir -p "$HOME_DIR/.termux"
echo "allow-external-apps = true" > "$HOME_DIR/.termux/termux.properties"

echo -e "\\033[1;33m=====================================================\\033[0m"
echo -e "\\033[1;33m⚠️  PERMISOS DE ANDROID PARA TERMUX:X11:\\033[0m"
echo -e "\\033[1;37m   • Concede a Termux: 'Mostrar ventanas emergentes en 2do plano' / 'Aparecer encima'.\\033[0m"
echo -e "\\033[1;33m=====================================================\\033[0m"

# Abrir ventana de ajustes de permisos en Android para Termux
am start -a android.settings.action.MANAGE_OVERLAY_PERMISSION -d package:com.termux 2>/dev/null || \
am start -a android.settings.APPLICATION_DETAILS_SETTINGS -d package:com.termux 2>/dev/null || true

export PYTHONPATH="$HOME_DIR/termux-display-manager:$PYTHONPATH"
echo -e "\\033[1;36m[*] Activando Wake-Lock para ejecución persistente en segundo plano...\\033[0m"
termux-wake-lock 2>/dev/null || true

echo -e "\\033[1;36m[*] Iniciando servicios TDM en segundo plano...\\033[0m"
pkill -f "tdm.agent.client" || true
pkill -f "tdm.cli.main server" || true

nohup "$PREFIX/bin/python3" -m tdm.cli.main server --port 19050 > "$HOME_DIR/.tdm/logs/server.log" 2>&1 &
sleep 1

# 5. Si hay Token, guardar configuración y arrancar agente en segundo plano
if [ -n "{token}" ] && [ "{token}" != "none" ]; then
    echo -e "\\033[1;36m[*] Vinculando e iniciando agente WebSocket en segundo plano (Token: {token})...\\033[0m"
    mkdir -p "$HOME_DIR/.tdm/config"
    echo '{{"hub": "{base_url}", "token": "{token}"}}' > "$HOME_DIR/.tdm/config/agent.json"
    nohup "$PREFIX/bin/python3" -m tdm.agent.client --hub "{base_url}" --token "{token}" > "$HOME_DIR/.tdm/logs/agent.log" 2>&1 &
    sleep 2
    echo -e "\\033[1;32m=====================================================\\033[0m"
    echo -e "\\033[1;32m🎉 ¡Dispositivo vinculado y ejecutándose en 2do plano!\\033[0m"
    echo -e "\\033[1;32m📱 Puedes volver a tu navegador en {base_url}\\033[0m"
    echo -e "\\033[1;32m=====================================================\\033[0m"
else
    echo -e "\\033[1;32m🎉 TDM Server activo en segundo plano en http://localhost:19050\\033[0m"
fi
"""

# Instancia global del Hub
hub_manager = HubManager()
