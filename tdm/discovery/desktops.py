import shutil
import os
from typing import Dict, List, Any, Optional
from tdm.core.registry import DESKTOP_CATALOG, get_desktop_entry

def discover_desktops(custom_list: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Descubre qué entornos de escritorio del catálogo están instalados en el sistema."""
    discovered: List[Dict[str, Any]] = []
    
    for de in DESKTOP_CATALOG:
        entry = dict(de)
        entry["installed"] = False
        entry["executable"] = None
        
        for cand in de["exec_candidates"]:
            path = shutil.which(cand)
            if path:
                entry["installed"] = True
                entry["executable"] = path
                break
                
        discovered.append(entry)
        
    # Evaluar entradas personalizadas
    if custom_list:
        for custom in custom_list:
            c_id = custom.get("id", "custom")
            c_cmd = custom.get("command", "")
            first_cmd = c_cmd.split()[0] if c_cmd else ""
            path = shutil.which(first_cmd) if first_cmd else None
            
            discovered.append({
                "id": c_id,
                "name": custom.get("name", "Custom Application"),
                "type": "custom",
                "description": custom.get("description", "Aplicación personalizada"),
                "exec_candidates": [c_cmd],
                "executable": path or c_cmd,
                "installed": bool(path or os.path.exists(first_cmd)),
                "packages": [],
                "icon": custom.get("icon", "app"),
                "env_vars": custom.get("env_vars", {})
            })
            
    return discovered

def get_desktop_by_id(desktop_id: str, custom_list: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    desktops = discover_desktops(custom_list)
    for d in desktops:
        if d["id"] == desktop_id:
            return d
    return get_desktop_entry(desktop_id)
