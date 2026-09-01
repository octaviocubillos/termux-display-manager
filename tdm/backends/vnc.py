import os
import shutil
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from tdm.backends.base import BaseDisplayBackend
from tdm.core.models import DisplayConfig, DisplaySession
from tdm.runners.env_helper import prepare_environment
from tdm.config import PREFIX
from tdm.constants import BACKEND_VNC, PORT_VNC_DEFAULT

class VNCBackend(BaseDisplayBackend):
    """Adaptador para servidores VNC (TigerVNC / TightVNC)."""
    
    def __init__(self, config: DisplayConfig):
        super().__init__(config)
        if not self.config.vnc_port:
            self.config.vnc_port = PORT_VNC_DEFAULT + self.config.display_num

    def build_server_command(self) -> Tuple[list, Dict[str, str]]:
        env = prepare_environment(self.config.display_num, self.config.desktop_id, self.config.audio, self.config.virgl)
        display_str = f":{self.config.display_num}"
        
        xvnc = shutil.which("Xvnc") or shutil.which("vncserver") or f"{PREFIX}/bin/Xvnc"
            
        cmd = [
            xvnc,
            display_str,
            "-geometry", self.config.resolution,
            "-depth", str(self.config.depth),
            "-dpi", str(self.config.dpi),
            "-rfbport", str(self.config.vnc_port),
            "-ac"
        ]
        
        if self.config.password:
            passwd_file = Path.home() / ".vnc" / "passwd"
            if passwd_file.exists():
                cmd.extend(["-PasswordFile", str(passwd_file)])
            else:
                cmd.extend(["-SecurityTypes", "None"])
        else:
            cmd.extend(["-SecurityTypes", "None"])
            
        return cmd, env

    def cleanup(self, session: Optional[DisplaySession] = None) -> None:
        num = self.config.display_num
        try:
            os.makedirs("/tmp/.X11-unix", mode=0o1777, exist_ok=True)
        except Exception:
            pass
        try:
            os.makedirs(f"{PREFIX}/tmp/.X11-unix", mode=0o1777, exist_ok=True)
        except Exception:
            pass
        locks = [
            f"/tmp/.X{num}-lock",
            f"/tmp/.X11-unix/X{num}",
            f"/tmp/.X11-pipe/X{num}",
            f"{Path.home()}/.vnc/{os.uname().nodename}:{num}.pid"
        ]
        for lock in locks:
            try:
                if os.path.exists(lock):
                    os.unlink(lock)
            except Exception:
                pass

    def get_connection_info(self, host: str = "127.0.0.1") -> Dict[str, str]:
        port = self.config.vnc_port or (PORT_VNC_DEFAULT + self.config.display_num)
        return {
            "type": BACKEND_VNC,
            "protocol": "RFB",
            "display": f":{self.config.display_num}",
            "port": str(port),
            "vnc_url": f"vnc://{host}:{port}",
            "instructions": f"Conéctate con tu cliente VNC (bVNC en Android, TigerVNC en PC) a {host}:{port}"
        }
