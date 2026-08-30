import os
import shutil
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from tdm.backends.vnc import VNCBackend
from tdm.core.models import DisplayConfig, DisplaySession
from tdm.config import PREFIX
from tdm.constants import BACKEND_NOVNC, PORT_NOVNC_DEFAULT

class NoVNCBackend(VNCBackend):
    """Adaptador para noVNC (acceso HTML5 en navegador o WebView mediante WebSockets)."""
    
    def __init__(self, config: DisplayConfig):
        super().__init__(config)
        if not self.config.web_port:
            self.config.web_port = PORT_NOVNC_DEFAULT + self.config.display_num

    def build_bridge_command(self) -> Optional[list]:
        """Comando para iniciar el proxy WebSockets (websockify) apuntando a la instancia VNC."""
        vnc_target = f"127.0.0.1:{self.config.vnc_port}"
        web_port = self.config.web_port or (PORT_NOVNC_DEFAULT + self.config.display_num)
        
        novnc_web_dir = None
        for cand in [
            str(Path(__file__).parent.parent / "web" / "novnc"),
            f"{PREFIX}/share/novnc",
            "/usr/share/novnc",
            "/usr/share/novnc-core"
        ]:
            if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "vnc.html")):
                novnc_web_dir = cand
                break
                
        websockify_bin = shutil.which("websockify")
        if websockify_bin:
            cmd = [websockify_bin]
        else:
            python_bin = shutil.which("python3") or f"{PREFIX}/bin/python3"
            cmd = [python_bin, "-m", "websockify"]
            
        if novnc_web_dir:
            cmd.extend(["--web", novnc_web_dir])
        cmd.extend([str(web_port), vnc_target])
        
        return cmd

    def get_connection_info(self, host: str = "127.0.0.1") -> Dict[str, str]:
        vnc_info = super().get_connection_info(host)
        web_port = self.config.web_port or (PORT_NOVNC_DEFAULT + self.config.display_num)
        
        novnc_url = f"http://{host}:{web_port}/vnc.html?autoconnect=true&resize=remote"
        vnc_info.update({
            "type": BACKEND_NOVNC,
            "web_port": str(web_port),
            "web_url": novnc_url,
            "instructions": f"Abre en tu navegador o WebView: {novnc_url}"
        })
        return vnc_info
