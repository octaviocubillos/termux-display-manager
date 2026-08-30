import os
import shutil
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from tdm.backends.base import BaseDisplayBackend
from tdm.core.models import DisplayConfig, DisplaySession
from tdm.runners.env_helper import prepare_environment
from tdm.config import PREFIX
from tdm.constants import BACKEND_TERMUX_X11

class TermuxX11Backend(BaseDisplayBackend):
    """Adaptador para el servidor gráfico nativo Termux:X11 en Android."""
    
    def build_server_command(self) -> Tuple[list, Dict[str, str]]:
        env = prepare_environment(self.config.display_num, self.config.desktop_id, self.config.audio, self.config.virgl)
        display_str = f":{self.config.display_num}"
        
        termux_x11_bin = shutil.which("termux-x11") or f"{PREFIX}/bin/termux-x11"
        cmd = [
            termux_x11_bin,
            display_str,
            "-ac",
            "-listen", "tcp"
        ]
        return cmd, env

    def build_bridge_command(self) -> Optional[list]:
        """Lanza la app Termux:X11 en Android automáticamente desde Termux."""
        am_bin = shutil.which("am") or shutil.which("termux-am") or f"{PREFIX}/bin/am"
        return [
            am_bin,
            "start",
            "--user", "0",
            "-a", "android.intent.action.MAIN",
            "-c", "android.intent.category.LAUNCHER",
            "-n", "com.termux.x11/com.termux.x11.MainActivity"
        ]

    def cleanup(self, session: Optional[DisplaySession] = None) -> None:
        import subprocess
        display_num = self.config.display_num
        prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
        
        # Matar procesos colgados de termux-x11
        subprocess.run(["pkill", "-x", "termux-x11"], capture_output=True)

        candidate_paths = [
            f"/tmp/.X11-unix/X{display_num}",
            f"/tmp/.X{display_num}-lock",
            f"/tmp/X11-pipe/X{display_num}",
            f"{prefix}/tmp/.X11-unix/X{display_num}",
            f"{prefix}/tmp/.X{display_num}-lock",
            f"{prefix}/tmp/X11-pipe/X{display_num}"
        ]
        for sock in candidate_paths:
            try:
                if os.path.exists(sock):
                    os.unlink(sock)
            except Exception:
                pass

    def get_connection_info(self, host: str = "127.0.0.1") -> Dict[str, str]:
        return {
            "type": BACKEND_TERMUX_X11,
            "protocol": "X11",
            "display": f":{self.config.display_num}",
            "intent": "am start -n com.termux.x11/com.termux.x11.MainActivity",
            "instructions": f"Se ha lanzado automáticamente la app 'Termux:X11' para interactuar con la pantalla :{self.config.display_num}"
        }
