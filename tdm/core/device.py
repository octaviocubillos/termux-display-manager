#!/usr/bin/env python3
"""
Módulo de Identidad de Dispositivo TDM, Registro de Red y Persistencia SQLite.
Genera y almacena el hash único de 8 letras minúsculas en ~/.tdm/manifest.sqlite3,
descubre interfaces IPv4 locales y Tailscale, registra el dispositivo en el Hub
y produce el banner unificado de accesos con garantías de privacidad y HTTPS.
"""

import sqlite3
import secrets
import string
import socket
import subprocess
import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from tdm.config import TDM_DIR
from tdm.version import __version__

MANIFEST_DB_PATH = TDM_DIR / "manifest.sqlite3"
DEFAULT_HUB_URL = "https://tdm.oton.cl"


class DeviceManager:
    """Gestiona la identidad física persistente del dispositivo en SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or MANIFEST_DB_PATH)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_identity (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
            """)
            conn.commit()

    def get_or_create_device_hash(self) -> str:
        """
        Recupera el hash único del dispositivo o genera uno nuevo de 8 letras minúsculas [a-z].
        Persiste el resultado en SQLite para asegurar idempotencia total.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM device_identity WHERE key = 'device_hash'")
            row = cursor.fetchone()
            if row and row["value"]:
                return row["value"]

            # Generar hash de exactamente 8 letras minúsculas
            letters = string.ascii_lowercase
            new_hash = "".join(secrets.choice(letters) for _ in range(8))
            now = time.time()

            cursor.execute("""
                INSERT OR REPLACE INTO device_identity (key, value, updated_at)
                VALUES ('device_hash', ?, ?)
            """, (new_hash, now))
            conn.commit()
            return new_hash

    def get_identity_meta(self, key: str) -> Optional[str]:
        """Consulta un valor de metadatos de identidad."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM device_identity WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None

    def set_identity_meta(self, key: str, value: str):
        """Guarda un valor de metadatos de identidad."""
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO device_identity (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, now))
            conn.commit()


def get_tailscale_ip() -> Optional[str]:
    """Detecta si Tailscale está activo y retorna su dirección IPv4 (rango 100.64.0.0/10)."""
    # 1. Intentar con CLI nativo de Tailscale
    try:
        res = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=1.2)
        if res.returncode == 0 and res.stdout.strip():
            candidate = res.stdout.strip().splitlines()[0].strip()
            if candidate.startswith("100."):
                return candidate
    except Exception:
        pass

    # 2. Inspeccionar interfaces de red con `ip -4 -o addr show`
    try:
        res = subprocess.run(["ip", "-4", "-o", "addr", "show"], capture_output=True, text=True, timeout=1.2)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    ifname = parts[1]
                    ip_str = parts[3].split("/")[0]
                    if "tailscale" in ifname.lower():
                        return ip_str
                    if ip_str.startswith("100."):
                        octets = [int(o) for o in ip_str.split(".") if o.isdigit()]
                        if len(octets) == 4 and octets[0] == 100 and 64 <= octets[1] <= 127:
                            return ip_str
    except Exception:
        pass

    return None


def get_local_ipv4_addresses() -> List[str]:
    """
    Retorna la lista de direcciones IPv4 locales (Wi-Fi, Ethernet, etc.),
    excluyendo estrictamente localhost (127.0.0.1 / 127.0.0.0/8).
    """
    ips: List[str] = []

    # 1. Socket UDP saliente hacia DNS público
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.25)
        s.connect(("8.8.8.8", 80))
        primary = s.getsockname()[0]
        s.close()
        if primary and not primary.startswith("127.") and primary != "localhost":
            ips.append(primary)
    except Exception:
        pass

    # 2. Utilidad `ip -4 -o addr show scope global` (disponible en Termux)
    try:
        res = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope", "global"], capture_output=True, text=True, timeout=1.2)
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    ip_candidate = parts[3].split("/")[0]
                    if ip_candidate and not ip_candidate.startswith("127.") and ip_candidate not in ips:
                        ips.append(ip_candidate)
    except Exception:
        pass

    # 3. Fallback mediante resolución de hostname
    try:
        _, _, host_ips = socket.gethostbyname_ex(socket.gethostname())
        for hip in host_ips:
            if hip and not hip.startswith("127.") and hip not in ips:
                ips.append(hip)
    except Exception:
        pass

    return ips


def get_primary_lan_ip() -> Optional[str]:
    """Obtiene la IP principal de la red local."""
    ips = get_local_ipv4_addresses()
    return ips[0] if ips else None


def register_device_to_hub(hub_url: str = DEFAULT_HUB_URL, port: int = 19050) -> Dict[str, Any]:
    """
    Descubre IPs locales y Tailscale y registra el dispositivo en el Landing Hub.
    """
    device_mgr = DeviceManager()
    dev_hash = device_mgr.get_or_create_device_hash()
    lan_ips = get_local_ipv4_addresses()
    tailscale_ip = get_tailscale_ip()

    payload = {
        "hash": dev_hash,
        "ips": lan_ips,
        "tailscale_ip": tailscale_ip,
        "port": port,
        "version": __version__
    }

    url = f"{hub_url.rstrip('/')}/api/register"
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": f"TDM-Client/{__version__}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=3.5) as response:
            res_body = response.read().decode("utf-8")
            result = json.loads(res_body)
            device_mgr.set_identity_meta("last_hub_registration", str(time.time()))
            device_mgr.set_identity_meta("hub_url", hub_url)
            return {
                "success": True,
                "registered": True,
                "device_hash": dev_hash,
                "url": f"{hub_url.rstrip('/')}/{dev_hash}/",
                "lan_ips": lan_ips,
                "tailscale_ip": tailscale_ip,
                "hub_response": result
            }
    except Exception as e:
        return {
            "success": False,
            "registered": False,
            "device_hash": dev_hash,
            "url": f"{hub_url.rstrip('/')}/{dev_hash}/",
            "lan_ips": lan_ips,
            "tailscale_ip": tailscale_ip,
            "error": str(e)
        }


def format_access_banner(port: int = 19050, hub_url: str = DEFAULT_HUB_URL) -> str:
    """
    Produce el banner explicativo con los accesos disponibles, destacando HTTPS,
    sus beneficios, la garantía absoluta de privacidad y la condición de acceso en la misma red.
    """
    device_mgr = DeviceManager()
    dev_hash = device_mgr.get_or_create_device_hash()
    lan_ips = get_local_ipv4_addresses()
    tailscale_ip = get_tailscale_ip()

    primary_lan = lan_ips[0] if lan_ips else "No detectada"
    ts_text = f"http://{tailscale_ip}:{port}" if tailscale_ip else "No detectado (Opcional)"
    central_url = f"{hub_url.rstrip('/')}/{dev_hash}/"

    banner = f"""
==================================================================
[TDM] ¡Servicio Web Activo e Identificado con Éxito!
==================================================================
Accesos al Panel Web de TDM:
• Local (en este teléfono):   http://127.0.0.1:{port}
• Red Local (Wi-Fi):          http://{primary_lan}:{port}
• Tailscale (VPN privada):    {ts_text}
• Acceso Central (HTTPS):     {central_url}

🔒 BENEFICIOS DEL ACCESO CENTRAL HTTPS:
• Conexión Cifrada SSL/TLS: Elimina las advertencias de "Sitio no seguro" del navegador.
• Soporte Completo PWA: Permite instalar TDM como App nativa en PC, Mac o Tablet.
• Portapapeles Bidireccional: Copiar y pegar fluido (la API del navegador exige HTTPS).
• Experiencia Inmersiva: Desbloquea bloqueo de puntero (Pointer Lock), teclado completo
  y pantalla completa para el control fluido de escritorios remotos (noVNC/X11).

🛡️ PRIVACIDAD TOTAL Y CERO RECOLECCIÓN:
• 100% Privado y Local: Ninguna información personal, archivo ni historial se comparte
  con servidores externos.
• Todo el procesamiento, escritorios gráficos y datos residen exclusivamente en tu teléfono.
• El dominio actúa solo como puente TLS seguro hacia tu red privada.

⚠️  CONDICIÓN DE ACCESO CENTRAL:
Para ingresar mediante {central_url} tu equipo (PC, Mac o Tablet)
debe estar conectado a la MISMA RED WI-FI/LOCAL de este teléfono o tener activa tu red TAILSCALE.
=================================================================="""
    return banner.strip()


# Instancia singleton por defecto
device_manager = DeviceManager()
