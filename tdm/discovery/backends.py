import os
from typing import Dict, List, Any, Optional
from tdm.core.registry import BACKEND_CATALOG, get_backend_entry
from tdm.constants import BACKEND_NOVNC, find_binary

def discover_backends() -> List[Dict[str, Any]]:
    """Descubre qué servidores de pantalla del catálogo están instalados y disponibles."""
    discovered: List[Dict[str, Any]] = []
    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    
    for b in BACKEND_CATALOG:
        entry = dict(b)
        entry["installed"] = False
        entry["executable"] = None
        
        for cand in b["exec_candidates"]:
            path = find_binary(cand)
            if not path:
                for candidate_dir in [f"{prefix}/bin", "/data/data/com.termux/files/usr/bin", "/usr/bin", "/bin"]:
                    direct_p = os.path.join(candidate_dir, cand)
                    if os.path.exists(direct_p) and not os.path.isdir(direct_p):
                        path = direct_p
                        break
            if path:
                entry["installed"] = True
                entry["executable"] = path
                break
                
        # Para noVNC, TDM provee el cliente HTML5 y proxy WebSocket nativos, pero requiere Xvnc (tigervnc)
        if b["id"] == BACKEND_NOVNC:
            xvnc_path = find_binary("Xvnc") or find_binary("vncserver")
            if not xvnc_path:
                for candidate_dir in [f"{prefix}/bin", "/data/data/com.termux/files/usr/bin"]:
                    for cand_name in ["Xvnc", "vncserver"]:
                        direct_p = os.path.join(candidate_dir, cand_name)
                        if os.path.exists(direct_p) and not os.path.isdir(direct_p):
                            xvnc_path = direct_p
                            break
                    if xvnc_path:
                        break
            if xvnc_path:
                entry["installed"] = True
                entry["executable"] = xvnc_path
                entry["description"] += " (Motor WebSockets TDM nativo)"
            else:
                entry["installed"] = False
                entry["executable"] = None

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
        "dbus": bool(find_binary("dbus-daemon") or find_binary("dbus-launch")),
        "pulseaudio": bool(find_binary("pulseaudio") or find_binary("paplay")),
        "virgl": bool(find_binary("virgl_test_server") or find_binary("virglrenderer")),
        "xrandr": bool(find_binary("xrandr")),
        "xdotool": bool(find_binary("xdotool")),
    }
