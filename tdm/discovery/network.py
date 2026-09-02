"""
Módulo de Detección de Red, IPs Locales (LAN) y Tailscale Mesh VPN.
Permite identificar automáticamente las interfaces activas para facilitar
el acceso por red local y VPN privada sin configuración manual.
"""

import os
import re
import socket
import subprocess
from typing import Dict, List, Any, Optional
from tdm.constants import PORT_NOVNC_DEFAULT, PORT_VNC_DEFAULT, PORT_RDP_DEFAULT, PORT_PULSEAUDIO
from tdm.core.device import device_manager, get_tailscale_ip, get_primary_lan_ip

def get_tailscale_ip() -> Optional[str]:
    """Detecta si Tailscale está activo y obtiene su IP en el rango 100.64.0.0/10."""
    try:
        res = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=1)
        if res.returncode == 0 and res.stdout.strip():
            ip = res.stdout.strip().splitlines()[0].strip()
            if ip.startswith("100."):
                return ip
    except Exception:
        pass

    try:
        res = subprocess.run(["ip", "-4", "addr", "show"], capture_output=True, text=True, timeout=1)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if "inet 100." in line:
                    match = re.search(r"inet (100\.\d+\.\d+\.\d+)", line)
                    if match:
                        return match.group(1)
    except Exception:
        pass

    return None

def discover_network_interfaces(port: int = 19050) -> Dict[str, Any]:
    """Descubre todas las interfaces de red relevantes para TDM."""
    lan_ip = get_primary_lan_ip() or "127.0.0.1"
    tailscale_ip = get_tailscale_ip()
    device_hash = device_manager.get_or_create_device_hash()

    access_urls = {
        "local": f"http://localhost:{port}",
        "lan": f"http://{lan_ip}:{port}",
        "web": f"https://tdm.oton.cl/{device_hash}/"
    }

    if tailscale_ip:
        access_urls["tailscale"] = f"http://{tailscale_ip}:{port}"

    return {
        "localhost": "127.0.0.1",
        "device_hash": device_hash,
        "lan_ip": lan_ip,
        "tailscale_ip": tailscale_ip,
        "has_tailscale": tailscale_ip is not None,
        "access_urls": access_urls,
        "ports": {
            "pwa_server": port,
            "novnc": PORT_NOVNC_DEFAULT,
            "vnc": PORT_VNC_DEFAULT,
            "rdp": PORT_RDP_DEFAULT,
            "pulseaudio": PORT_PULSEAUDIO
        }
    }

class NetworkDiscovery:
    def get_all_interfaces(self, port: int = 19050) -> Dict[str, Any]:
        return discover_network_interfaces(port)

network_discovery = NetworkDiscovery()
