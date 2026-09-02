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

    Estrategia: xrdp en Termux no tiene sesman funcional ni PAM. El enfoque
    más confiable es levantar un servidor VNC (Xvnc) y luego configurar xrdp
    para que actúe como proxy RDP → VNC en el mismo display. Así el cliente
    RDP (Microsoft Remote Desktop, Remmina, etc.) se conecta al puerto 3389
    y xrdp lo redirige internamente al Xvnc local.

    Requisitos en Termux:
        pkg install tigervnc xrdp
    """

    def __init__(self, config: DisplayConfig):
        super().__init__(config)
        if not self.config.rdp_port:
            self.config.rdp_port = PORT_RDP_DEFAULT
        # Puerto VNC interno (no expuesto directamente)
        self._internal_vnc_port = PORT_VNC_DEFAULT + self.config.display_num

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_vnc_dir(self) -> None:
        (Path.home() / ".vnc").mkdir(parents=True, exist_ok=True)

    def _xrdp_conf_path(self) -> Path:
        return Path.home() / ".tdm" / "xrdp.ini"

    def _write_xrdp_conf(self) -> Path:
        """
        Genera un xrdp.ini mínimo que redirige RDP → VNC local.
        Evita depender del xrdp.ini del sistema (que puede no existir en Termux).
        """
        conf_dir = Path.home() / ".tdm"
        conf_dir.mkdir(parents=True, exist_ok=True)
        conf_path = conf_dir / "xrdp.ini"

        conf_content = f"""; xrdp.ini generado por TDM — no editar manualmente
[globals]
port={self.config.rdp_port}
allow_channels=true
max_bpp=32
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
bulk_compression=yes
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
rail=false
xrdpvr=false

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
    # Paso 1: Levantar Xvnc en el puerto interno
    # ------------------------------------------------------------------

    def _build_xvnc_command(self) -> Tuple[list, Dict[str, str]]:
        env = prepare_environment(
            self.config.display_num,
            self.config.desktop_id,
            self.config.audio,
            self.config.virgl,
            dpi=self.config.dpi,
        )
        self._ensure_vnc_dir()
        xvnc = find_binary("Xvnc") or f"{PREFIX}/bin/Xvnc"
        cmd = [
            xvnc,
            f":{self.config.display_num}",
            "-geometry", self.config.resolution,
            "-depth", str(self.config.depth),
            "-dpi", str(self.config.dpi),
            "-rfbport", str(self._internal_vnc_port),
            "-SecurityTypes", "None",
            "-ac",
            "-localhost", "yes",   # Solo local: xrdp accede desde 127.0.0.1
            "-alwaysshared",
            "-MaxIdleTime", "0",
        ]
        return cmd, env

    # ------------------------------------------------------------------
    # Paso 2: build_server_command usa Xvnc como servidor principal
    # ------------------------------------------------------------------

    def build_server_command(self) -> Tuple[list, Dict[str, str]]:
        return self._build_xvnc_command()

    # ------------------------------------------------------------------
    # Paso 3: xrdp como proceso puente (bridge) RDP → VNC
    # ------------------------------------------------------------------

    def build_bridge_command(self) -> Optional[list]:
        xrdp_bin = find_binary("xrdp") or f"{PREFIX}/bin/xrdp"
        if not os.path.exists(xrdp_bin):
            print("[!] xrdp no está instalado. Instálalo con: pkg install xrdp")
            print("[!] El servidor VNC (Xvnc) estará disponible directamente.")
            return None

        conf_path = self._write_xrdp_conf()
        return [
            xrdp_bin,
            "--nodaemon",
            "--config", str(conf_path),
        ]

    # ------------------------------------------------------------------
    # Limpieza
    # ------------------------------------------------------------------

    def cleanup(self, session: Optional[DisplaySession] = None) -> None:
        num = self.config.display_num

        # Matar xrdp
        subprocess.run(["pkill", "-f", "xrdp"], capture_output=True)

        # Matar Xvnc interno
        subprocess.run(["pkill", "-f", f"Xvnc.*:{num}"], capture_output=True)

        # Asegurar directorios de sockets X11
        for socket_dir in ["/tmp/.X11-unix", f"{PREFIX}/tmp/.X11-unix"]:
            try:
                os.makedirs(socket_dir, mode=0o1777, exist_ok=True)
            except Exception:
                pass

        # Archivos lock / socket / PID
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
    # Información de conexión
    # ------------------------------------------------------------------

    def get_connection_info(self, host: str = "127.0.0.1") -> Dict[str, str]:
        rdp_port = self.config.rdp_port or PORT_RDP_DEFAULT
        xrdp_available = bool(find_binary("xrdp"))
        return {
            "type": BACKEND_RDP,
            "protocol": "RDP",
            "port": str(rdp_port),
            "rdp_url": f"rdp://{host}:{rdp_port}",
            "vnc_fallback_port": str(self._internal_vnc_port),
            "xrdp_available": str(xrdp_available),
            "instructions": (
                f"Cliente RDP → {host}:{rdp_port}\n"
                f"• Android: Microsoft Remote Desktop\n"
                f"• PC: Remmina, mstsc.exe\n"
                + (
                    f"• VNC directo también disponible en {host}:{self._internal_vnc_port}"
                    if not xrdp_available
                    else f"• xrdp activo: conecta como usuario 'na' sin contraseña"
                )
            ),
        }
