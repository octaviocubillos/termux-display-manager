import os
import shutil
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from tdm.backends.base import BaseDisplayBackend
from tdm.core.models import DisplayConfig, DisplaySession
from tdm.runners.env_helper import prepare_environment
from tdm.constants import BACKEND_RDP, PORT_RDP_DEFAULT, PREFIX, find_binary

class XRDPBackend(BaseDisplayBackend):
    """Adaptador para el servidor Microsoft Remote Desktop (xrdp)."""

    def __init__(self, config: DisplayConfig):
        super().__init__(config)
        if not self.config.rdp_port:
            self.config.rdp_port = PORT_RDP_DEFAULT

    def build_server_command(self) -> Tuple[list, Dict[str, str]]:
        env = prepare_environment(self.config.display_num, self.config.desktop_id, self.config.audio, self.config.virgl)
        xrdp_bin = find_binary("xrdp") or f"{PREFIX}/bin/xrdp"
        
        cmd = [
            xrdp_bin,
            "--nodaemon",
            "-p", str(self.config.rdp_port)
        ]
        return cmd, env

    def cleanup(self, session: Optional[DisplaySession] = None) -> None:
        try:
            pid_file = f"{PREFIX}/var/run/xrdp.pid"
            if os.path.exists(pid_file):
                os.unlink(pid_file)
        except Exception:
            pass

    def get_connection_info(self, host: str = "127.0.0.1") -> Dict[str, str]:
        port = self.config.rdp_port or PORT_RDP_DEFAULT
        return {
            "type": BACKEND_RDP,
            "protocol": "RDP",
            "port": str(port),
            "rdp_url": f"rdp://{host}:{port}",
            "instructions": f"Conéctate con Microsoft Remote Desktop Client a {host}:{port}"
        }
