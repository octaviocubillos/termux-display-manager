from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any, List
import time

class DisplayStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    CRASHED = "crashed"
    STOPPING = "stopping"

class BackendType(str, Enum):
    TERMUX_X11 = "termux-x11"
    VNC = "vnc"
    NOVNC = "novnc"
    RDP = "rdp"

@dataclass
class DisplayConfig:
    display_num: int = 0
    desktop_id: str = "xfce"
    backend: str = "termux-x11"
    mode: str = "desktop"
    resolution: str = "1920x1080"
    dpi: int = 96
    depth: int = 24
    audio: bool = True
    virgl: bool = False
    custom_command: Optional[str] = None
    vnc_port: Optional[int] = None
    web_port: Optional[int] = None
    rdp_port: Optional[int] = None
    password: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)

    @property
    def display_str(self) -> str:
        return f":{self.display_num}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class DisplaySession:
    id: str = "display-0"  # e.g., "display-1"
    config: DisplayConfig = field(default_factory=DisplayConfig)
    status: DisplayStatus = DisplayStatus.STOPPED
    server_pid: Optional[int] = None
    session_pid: Optional[int] = None
    bridge_pid: Optional[int] = None  # for websockify / novnc
    started_at: Optional[float] = None
    stopped_at: Optional[float] = None
    error_message: Optional[str] = None
    log_file: Optional[str] = None
    x11_socket: Optional[str] = None
    urls: Dict[str, str] = field(default_factory=dict)
    
    def uptime_seconds(self) -> float:
        if self.status == DisplayStatus.RUNNING and self.started_at:
            return time.time() - self.started_at
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "display": f":{self.config.display_num}",
            "display_num": self.config.display_num,
            "desktop_id": self.config.desktop_id,
            "backend": self.config.backend,
            "status": self.status.value,
            "resolution": self.config.resolution,
            "dpi": self.config.dpi,
            "depth": self.config.depth,
            "audio": self.config.audio,
            "virgl": self.config.virgl,
            "server_pid": self.server_pid,
            "session_pid": self.session_pid,
            "bridge_pid": self.bridge_pid,
            "started_at": self.started_at,
            "uptime_seconds": int(self.uptime_seconds()),
            "error_message": self.error_message,
            "urls": self.urls,
            "ports": {
                "vnc": self.config.vnc_port,
                "novnc": self.config.web_port,
                "rdp": self.config.rdp_port
            }
        }
        return d
