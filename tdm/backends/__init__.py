from typing import Dict, Type
from tdm.backends.base import BaseDisplayBackend
from tdm.backends.termux_x11 import TermuxX11Backend
from tdm.backends.vnc import VNCBackend
from tdm.backends.novnc import NoVNCBackend
from tdm.backends.rdp import XRDPBackend
from tdm.constants import (
    BACKEND_TERMUX_X11,
    BACKEND_NOVNC,
    BACKEND_VNC,
    BACKEND_RDP,
)
from tdm.core.models import DisplayConfig

BACKEND_FACTORIES: Dict[str, Type[BaseDisplayBackend]] = {
    BACKEND_TERMUX_X11: TermuxX11Backend,
    BACKEND_NOVNC: NoVNCBackend,
    BACKEND_VNC: VNCBackend,
    BACKEND_RDP: XRDPBackend,
}

def create_backend(config: DisplayConfig) -> BaseDisplayBackend:
    """Factory unificado para instanciar el adaptador de pantalla adecuado."""
    backend_cls = BACKEND_FACTORIES.get(config.backend, TermuxX11Backend)
    return backend_cls(config)

__all__ = [
    "BaseDisplayBackend",
    "TermuxX11Backend",
    "VNCBackend",
    "NoVNCBackend",
    "XRDPBackend",
    "create_backend",
    "BACKEND_FACTORIES",
]
