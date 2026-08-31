import os
import shutil
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from tdm.backends.vnc import VNCBackend
from tdm.core.models import DisplayConfig, DisplaySession
from tdm.config import PREFIX
from tdm.constants import BACKEND_NOVNC, PORT_TDM_SERVER

class NoVNCBackend(VNCBackend):
    """Adaptador para noVNC (acceso HTML5 en navegador o WebView mediante WebSockets)."""
    
    def __init__(self, config: DisplayConfig):
        super().__init__(config)
        self.config.web_port = PORT_TDM_SERVER

    def build_bridge_command(self) -> Optional[list]:
        """El servidor TDM gestiona el puente WebSocket nativamente sin dependencias externas."""
        return None

    def get_connection_info(self, host: str = "127.0.0.1") -> Dict[str, str]:
        vnc_info = super().get_connection_info(host)
        web_port = PORT_TDM_SERVER
        
        novnc_url = f"http://{host}:{web_port}/novnc/vnc.html?autoconnect=true&resize=remote&path=websockify"
        vnc_info.update({
            "type": BACKEND_NOVNC,
            "web_port": str(web_port),
            "web_url": novnc_url,
            "instructions": f"Abre en tu navegador o WebView: {novnc_url}"
        })
        return vnc_info
