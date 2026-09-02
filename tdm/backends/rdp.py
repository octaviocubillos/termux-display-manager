import os
import subprocess
import shutil
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from tdm.backends.base import BaseDisplayBackend
from tdm.core.models import DisplayConfig, DisplaySession
from tdm.runners.env_helper import prepare_environment
from tdm.constants import BACKEND_RDP, PORT_RDP_DEFAULT, PORT_VNC_DEFAULT, PREFIX, find_binary

class XRDPBackend(BaseDisplayBackend):
    """
    Adaptador RDP para Termux.

    Modo de operación:
    ─────────────────
    • Si xrdp está instalado → Xvnc (localhost:5900) + xrdp (0.0.0.0:3389 como proxy RDP→VNC)
    • Si xrdp NO está instalado (Termux por defecto) → Xvnc expuesto directamente en 0.0.0.0:5900
      El cliente se conecta con cualquier cliente VNC o con Microsoft RD Client en modo VNC.

    Puerto expuesto al cliente:
    • Con xrdp: 3389  (protocolo RDP puro)
    • Sin xrdp: 5900  (protocolo VNC/RFB)
    """

    def __init__(self, config: DisplayConfig):
        super().__init__(config)
        if not self.config.rdp_port:
            self.config.rdp_port = PORT_RDP_DEFAULT
        self._internal_vnc_port = PORT_VNC_DEFAULT + self.config.display_num
        self._xrdp_available = bool(find_binary("xrdp"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_vnc_dir(self) -> None:
        (Path.home() / ".vnc").mkdir(parents=True, exist_ok=True)

    def _write_xrdp_conf(self) -> Path:
        """Genera xrdp.ini mínimo que redirige RDP → VNC local."""
        conf_dir = Path.home() / ".tdm"
        conf_dir.mkdir(parents=True, exist_ok=True)
        conf_path = conf_dir / "xrdp.ini"
        conf_content = f"""; xrdp.ini generado por TDM
[globals]
port={self.config.rdp_port}
fork=false
tcp_nodelay=true
tcp_keepalive=true
security_layer=negotiate
crypt_level=high
certificate=
key_file=
ssl_protocols=TLSv1.2, TLSv1.3
tls_ciphers=HIGH
channel_code=1
bitmap_compression=yes
autorun=
hidelogwindow=true
loglevel=ERROR
logfile={conf_dir}/xrdp.log
enable_token_login=false

[Logging]
LogFile={conf_dir}/xrdp.log
LogLevel=ERROR
EnableSyslog=false

[Channels]
rdpdr=true
rdpsnd=true
drdynvc=true
cliprdr=true

[vnc-any]
name=Sesión VNC Local (TDM)
lib=libvnc.so
username=na
password=ask
ip=127.0.0.1
port={self._internal_vnc_port}
delay_ms=2000
"""
        conf_path.write_text(conf_content)
        return conf_path

    # ------------------------------------------------------------------
    # Comando principal: Xvnc
    # ------------------------------------------------------------------

    def build_server_command(self) -> Tuple[list, Dict[str, str]]:
        env = prepare_environment(
            self.config.display_num,
            self.config.desktop_id,
            self.config.audio,
            self.config.virgl,
            dpi=self.config.dpi,
        )
        self._ensure_vnc_dir()
        xvnc = find_binary("Xvnc") or f"{PREFIX}/bin/Xvnc"

        # Si xrdp está disponible → Xvnc solo en localhost (xrdp actúa de proxy)
        # Si xrdp NO está → Xvnc expuesto directamente en todas las interfaces
        localhost_only = "yes" if self._xrdp_available else "no"
        vnc_port = self._internal_vnc_port if self._xrdp_available else self._internal_vnc_port

        cmd = [
            xvnc,
            f":{self.config.display_num}",
            "-geometry", self.config.resolution,
            "-depth", str(self.config.depth),
            "-dpi", str(self.config.dpi),
            "-rfbport", str(vnc_port),
            "-SecurityTypes", "None",
            "-ac",
            "-localhost", localhost_only,
            "-alwaysshared",
            "-MaxIdleTime", "0",
        ]
        return cmd, env

    # ------------------------------------------------------------------
    # Bridge: xrdp (solo si está instalado)
    # ------------------------------------------------------------------

    def build_bridge_command(self) -> Optional[list]:
        if not self._xrdp_available:
            return None  # Sin xrdp → Xvnc directo, no hay bridge
        xrdp_bin = find_binary("xrdp")
        conf_path = self._write_xrdp_conf()
        return [xrdp_bin, "--nodaemon", "--config", str(conf_path)]

    # ------------------------------------------------------------------
    # Limpieza
    # ------------------------------------------------------------------

    def cleanup(self, session: Optional[DisplaySession] = None) -> None:
        num = self.config.display_num
        subprocess.run(["pkill", "-f", "xrdp"], capture_output=True)
        subprocess.run(["pkill", "-f", f"Xvnc.*:{num}"], capture_output=True)

        for socket_dir in ["/tmp/.X11-unix", f"{PREFIX}/tmp/.X11-unix"]:
            try:
                os.makedirs(socket_dir, mode=0o1777, exist_ok=True)
            except Exception:
                pass

        node = os.uname().nodename
        locks = [
            f"/tmp/.X{num}-lock",
            f"/tmp/.X11-unix/X{num}",
            f"{PREFIX}/tmp/.X{num}-lock",
            f"{PREFIX}/tmp/.X11-unix/X{num}",
            f"{PREFIX}/var/run/xrdp.pid",
            str(Path.home() / ".vnc" / f"{node}:{num}.pid"),
        ]
        for lock in locks:
            try:
                if os.path.exists(lock):
                    os.unlink(lock)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Información de conexión (clara y precisa)
    # ------------------------------------------------------------------

    def get_connection_info(self, host: str = "127.0.0.1") -> Dict[str, str]:
        if self._xrdp_available:
            # xrdp en puerto 3389 (RDP real)
            exposed_port = self.config.rdp_port or PORT_RDP_DEFAULT
            protocol = "RDP"
            url = f"rdp://{host}:{exposed_port}"
            instructions = (
                f"Cliente RDP → {host}:{exposed_port}\n"
                f"• Android: Microsoft Remote Desktop\n"
                f"• PC: mstsc.exe / Remmina\n"
                f"• Usuario: na  •  Sin contraseña"
            )
        else:
            # Sin xrdp → VNC directo en puerto 5900
            exposed_port = self._internal_vnc_port
            protocol = "RFB (VNC)"
            url = f"vnc://{host}:{exposed_port}"
            instructions = (
                f"xrdp no instalado en Termux. Conexión VNC directa en {host}:{exposed_port}\n"
                f"• Android: bVNC, MultiVNC\n"
                f"• PC: TigerVNC Viewer, RealVNC\n"
                f"• Sin contraseña (SecurityTypes=None)"
            )

        return {
            "type": BACKEND_RDP,
            "protocol": protocol,
            "port": str(exposed_port),
            "display": f":{self.config.display_num}",
            "url": url,
            "xrdp_available": str(self._xrdp_available),
            "vnc_port": str(self._internal_vnc_port),
            "rdp_port": str(self.config.rdp_port or PORT_RDP_DEFAULT),
            "instructions": instructions,
        }
