import os
import subprocess
import shutil
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from tdm.backends.base import BaseDisplayBackend
from tdm.core.models import DisplayConfig, DisplaySession
from tdm.runners.env_helper import prepare_environment
from tdm.constants import BACKEND_VNC, PORT_VNC_DEFAULT, PREFIX, find_binary

class VNCBackend(BaseDisplayBackend):
    """Adaptador para servidores VNC (TigerVNC / TightVNC) sobre Termux."""

    def __init__(self, config: DisplayConfig):
        super().__init__(config)
        if not self.config.vnc_port:
            self.config.vnc_port = PORT_VNC_DEFAULT + self.config.display_num

    # ------------------------------------------------------------------
    # Helpers de seguridad
    # ------------------------------------------------------------------

    def _passwd_file(self) -> Optional[Path]:
        """Devuelve el fichero de contraseña VNC si existe."""
        p = Path.home() / ".vnc" / "passwd"
        return p if p.exists() else None

    def _ensure_vnc_dir(self) -> None:
        """Garantiza que ~/.vnc existe."""
        vnc_dir = Path.home() / ".vnc"
        vnc_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Comando de servidor
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
        display_str = f":{self.config.display_num}"

        # Preferir Xvnc (servidor headless) → vncserver (wrapper script)
        xvnc = find_binary("Xvnc") or find_binary("vncserver") or f"{PREFIX}/bin/Xvnc"

        cmd = [
            xvnc,
            display_str,
            "-geometry", self.config.resolution,
            "-depth", str(self.config.depth),
            "-dpi", str(self.config.dpi),
            "-rfbport", str(self.config.vnc_port),
            "-rfbauth", str(self._passwd_file()) if self._passwd_file() else "",
            # Sin autenticación cuando no hay contraseña configurada
        ]

        # Quitar "-rfbauth" vacío si no hay passwd
        if not self._passwd_file():
            cmd = [c for c in cmd if c not in ("-rfbauth", "")]
            cmd.extend(["-SecurityTypes", "None"])

        # Evitar uso de localhost loopback en Android
        cmd.extend(["-ac", "-localhost", "no"])

        # Optimizaciones de rendimiento en red local / WiFi
        cmd.extend([
            "-alwaysshared",
            "-MaxDisconnectionTime", "0",
            "-MaxIdleTime", "0",
        ])

        return cmd, env

    # ------------------------------------------------------------------
    # Limpieza de artefactos X11 / VNC
    # ------------------------------------------------------------------

    def cleanup(self, session: Optional[DisplaySession] = None) -> None:
        num = self.config.display_num

        # Matar vncserver wrapper si está corriendo
        subprocess.run(["pkill", "-f", f"Xvnc.*:{num}"], capture_output=True)

        # Asegurar directorios de sockets X11
        for socket_dir in ["/tmp/.X11-unix", f"{PREFIX}/tmp/.X11-unix"]:
            try:
                os.makedirs(socket_dir, mode=0o1777, exist_ok=True)
            except Exception:
                pass

        # Archivos lock / socket / PID a eliminar
        node = os.uname().nodename
        locks = [
            f"/tmp/.X{num}-lock",
            f"/tmp/.X11-unix/X{num}",
            f"/tmp/.X11-pipe/X{num}",
            f"{PREFIX}/tmp/.X{num}-lock",
            f"{PREFIX}/tmp/.X11-unix/X{num}",
            str(Path.home() / ".vnc" / f"{node}:{num}.pid"),
            str(Path.home() / ".vnc" / f"{node}:{num}.log"),
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
        port = self.config.vnc_port or (PORT_VNC_DEFAULT + self.config.display_num)
        passwd_ok = self._passwd_file() is not None
        return {
            "type": BACKEND_VNC,
            "protocol": "RFB",
            "display": f":{self.config.display_num}",
            "port": str(port),
            "has_password": str(passwd_ok),
            "vnc_url": f"vnc://{host}:{port}",
            "instructions": (
                f"Conéctate con tu cliente VNC a {host}:{port}\n"
                f"• Android: bVNC Free, MultiVNC\n"
                f"• PC: TigerVNC Viewer, RealVNC\n"
                + ("• Sin contraseña (SecurityTypes=None)" if not passwd_ok else "• Autenticación: contraseña configurada")
            ),
        }
