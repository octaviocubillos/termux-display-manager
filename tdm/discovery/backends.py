import shutil
from typing import Dict, List, Any, Optional
from tdm.core.registry import BACKEND_CATALOG, get_backend_entry
from tdm.constants import BACKEND_NOVNC

def discover_backends() -> List[Dict[str, Any]]:
    """Descubre qué servidores de pantalla del catálogo están instalados y disponibles."""
    discovered: List[Dict[str, Any]] = []
    
    for b in BACKEND_CATALOG:
        entry = dict(b)
        entry["installed"] = False
        entry["executable"] = None
        
        for cand in b["exec_candidates"]:
            path = shutil.which(cand)
            if path:
                entry["installed"] = True
                entry["executable"] = path
                break
                
        # Soporte para noVNC con motor embebido si python está disponible
        if b["id"] == BACKEND_NOVNC and not entry["installed"]:
            entry["installed"] = True
            entry["executable"] = "builtin-websockify"
            entry["description"] += " (Motor WebSockets TDM activo)"

        discovered.append(entry)
        
    return discovered

def get_backend_by_id(backend_id: str) -> Optional[Dict[str, Any]]:
    backends = discover_backends()
    for b in backends:
        if b["id"] == backend_id:
            return b
    return get_backend_entry(backend_id)

def discover_system_features() -> Dict[str, Any]:
    """Descubre utilidades auxiliares como D-Bus, PulseAudio y aceleración VirGL."""
    return {
        "dbus": bool(shutil.which("dbus-daemon") or shutil.which("dbus-launch")),
        "pulseaudio": bool(shutil.which("pulseaudio") or shutil.which("paplay")),
        "virgl": bool(shutil.which("virgl_test_server") or shutil.which("virglrenderer")),
        "xrandr": bool(shutil.which("xrandr")),
        "xdotool": bool(shutil.which("xdotool")),
    }
