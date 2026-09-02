import os
from typing import Dict, Any, Tuple, Optional
from tdm.backends.vnc import VNCBackend
from tdm.core.models import DisplayConfig, DisplaySession
from tdm.config import PREFIX
from tdm.constants import BACKEND_NOVNC, PORT_TDM_SERVER

class NoVNCBackend(VNCBackend):
    """
    Adaptador noVNC: Xvnc headless + websockify gestionado por el servidor TDM.
    El cliente accede vía navegador HTML5, sin instalar ningún cliente VNC externo.
    """

    def __init__(self, config: DisplayConfig):
        super().__init__(config)
        self.config.web_port = PORT_TDM_SERVER

    def build_bridge_command(self) -> Optional[list]:
        """El servidor HTTP de TDM gestiona el puente WebSocket nativo (websockify integrado)."""
        return None

    def get_connection_info(self, host: str = "127.0.0.1") -> Dict[str, str]:
        vnc_info = super().get_connection_info(host)
        web_port = PORT_TDM_SERVER

        # URL con parámetros proxy-friendly (igual que genera el frontend)
        novnc_url = (
            f"http://{host}:{web_port}/novnc/vnc_lite.html"
            f"?host={host}&path=websockify&scale=false&resize=remote&embedded=true"
        )
        vnc_info.update({
            "type": BACKEND_NOVNC,
            "web_port": str(web_port),
            "web_url": novnc_url,
            "instructions": f"Abre en tu navegador: {novnc_url}",
        })
        return vnc_info
