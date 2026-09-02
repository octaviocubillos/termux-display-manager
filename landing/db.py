#!/usr/bin/env python3
"""
Módulo de Base de Datos SQLite para el Servidor de Landing Page de TDM.
Gestiona el registro de hashes de dispositivos (8 letras), sus IPs locales,
IP de Tailscale y la última IP activa detectada para el Reverse Proxy.
"""

import sqlite3
import json
import time
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "devices.sqlite3"
HASH_REGEX = re.compile(r"^[a-z]{8}$")


class LandingDatabase:
    """Gestor de persistencia SQLite para dispositivos TDM y enrutamiento dinámico."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_hash TEXT PRIMARY KEY,
                    ips TEXT NOT NULL,
                    tailscale_ip TEXT,
                    port INTEGER NOT NULL DEFAULT 19050,
                    last_active_ip TEXT,
                    last_seen REAL NOT NULL,
                    created_at REAL NOT NULL,
                    client_version TEXT,
                    user_agent TEXT
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON devices(last_seen);
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connection_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_hash TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    ip TEXT,
                    created_at REAL NOT NULL
                );
            """)
            conn.commit()

    def register_device(
        self,
        device_hash: str,
        ips: List[str],
        port: int = 19050,
        tailscale_ip: Optional[str] = None,
        client_version: str = "",
        user_agent: str = ""
    ) -> Dict[str, Any]:
        """
        Registra o actualiza un dispositivo con su hash de 8 letras minúsculas.
        """
        device_hash = device_hash.strip().lower()
        if not HASH_REGEX.match(device_hash):
            raise ValueError(f"Hash inválido: '{device_hash}'. Debe constar de exactamente 8 letras minúsculas [a-z].")

        # Filtrar IPs: descartar estrictamente localhost y loopback
        clean_ips = []
        for ip in ips:
            ip_str = str(ip).strip()
            if not ip_str or ip_str.startswith("127.") or ip_str == "localhost":
                continue
            if ip_str not in clean_ips:
                clean_ips.append(ip_str)

        clean_tailscale = None
        if tailscale_ip:
            ts_str = str(tailscale_ip).strip()
            if ts_str and not ts_str.startswith("127.") and ts_str != "localhost":
                clean_tailscale = ts_str

        now = time.time()
        ips_json = json.dumps(clean_ips)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT created_at, last_active_ip FROM devices WHERE device_hash = ?", (device_hash,))
            row = cursor.fetchone()

            if row:
                created_at = row["created_at"]
                last_active_ip = row["last_active_ip"]
                cursor.execute("""
                    UPDATE devices
                    SET ips = ?, tailscale_ip = ?, port = ?, last_seen = ?, client_version = ?, user_agent = ?
                    WHERE device_hash = ?
                """, (ips_json, clean_tailscale, port, now, client_version, user_agent, device_hash))
            else:
                created_at = now
                last_active_ip = None
                cursor.execute("""
                    INSERT INTO devices (device_hash, ips, tailscale_ip, port, last_active_ip, last_seen, created_at, client_version, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (device_hash, ips_json, clean_tailscale, port, None, now, created_at, client_version, user_agent))

            cursor.execute("""
                INSERT INTO connection_events (device_hash, event_type, ip, created_at)
                VALUES (?, 'register', ?, ?)
            """, (device_hash, clean_ips[0] if clean_ips else (clean_tailscale or "unknown"), now))
            conn.commit()

        return {
            "device_hash": device_hash,
            "ips": clean_ips,
            "tailscale_ip": clean_tailscale,
            "port": port,
            "last_active_ip": last_active_ip,
            "last_seen": now,
            "created_at": created_at,
            "url": f"https://tdm.oton.cl/{device_hash}/"
        }

    def get_device(self, device_hash: str) -> Optional[Dict[str, Any]]:
        """Recupera la información de un dispositivo por su hash."""
        device_hash = device_hash.strip().lower()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices WHERE device_hash = ?", (device_hash,))
            row = cursor.fetchone()
            if not row:
                return None

            ips_list = []
            try:
                ips_list = json.loads(row["ips"])
            except Exception:
                pass

            return {
                "device_hash": row["device_hash"],
                "ips": ips_list,
                "tailscale_ip": row["tailscale_ip"],
                "port": row["port"],
                "last_active_ip": row["last_active_ip"],
                "last_seen": row["last_seen"],
                "created_at": row["created_at"],
                "client_version": row["client_version"],
                "user_agent": row["user_agent"],
                "url": f"https://tdm.oton.cl/{row['device_hash']}/"
            }

    def set_last_active_ip(self, device_hash: str, active_ip: str) -> None:
        """Actualiza la IP activa confirmada tras un sondeo TCP exitoso."""
        device_hash = device_hash.strip().lower()
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE devices
                SET last_active_ip = ?, last_seen = ?
                WHERE device_hash = ?
            """, (active_ip, now, device_hash))
            cursor.execute("""
                INSERT INTO connection_events (device_hash, event_type, ip, created_at)
                VALUES (?, 'active_connect', ?, ?)
            """, (device_hash, active_ip, now))
            conn.commit()

    def list_devices(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista dispositivos registrados recientemente."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM devices ORDER BY last_seen DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            devices = []
            for r in rows:
                ips = []
                try:
                    ips = json.loads(r["ips"])
                except Exception:
                    pass
                devices.append({
                    "device_hash": r["device_hash"],
                    "ips_count": len(ips),
                    "has_tailscale": bool(r["tailscale_ip"]),
                    "last_active_ip": r["last_active_ip"],
                    "port": r["port"],
                    "last_seen": r["last_seen"],
                    "created_at": r["created_at"],
                    "client_version": r["client_version"]
                })
            return devices


# Instancia singleton por defecto
landing_db = LandingDatabase()
