#!/usr/bin/env python3
"""
Servidor Web para Landing Page de TDM con Reverse Proxy Dinámico HTTP/WebSocket
basado en Hashes de 8 letras y SQLite, además de soporte legacy para /aabbcc.
Sirve archivos estáticos y protege scripts de instalación contra navegadores.
"""

import asyncio
import os
import sys
import json
import time
import re
import argparse
import mimetypes
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

LANDING_DIR = Path(__file__).resolve().parent
if str(LANDING_DIR) not in sys.path:
    sys.path.insert(0, str(LANDING_DIR))

try:
    from landing.db import landing_db, LandingDatabase, HASH_REGEX
except ImportError:
    from db import landing_db, LandingDatabase, HASH_REGEX

DEVICE_ROUTE_REGEX = re.compile(r"^/([a-z]{8})(?:/(.*))?$")


class LandingProxyServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        target_host: str = "192.168.1.197",
        target_port: int = 19050,
        db: Optional[LandingDatabase] = None
    ):
        self.host = host
        self.port = port
        self.target_host = target_host
        self.target_port = target_port
        self.db = db or landing_db
        self.active_targets: Dict[str, Dict[str, Any]] = {}

    async def find_active_target(self, device: Dict[str, Any]) -> Optional[Tuple[str, int]]:
        """
        Determina la IP activa del dispositivo probando secuencialmente:
        1. 127.0.0.1 (mismo host)
        2. IPs locales (LAN / Wi-Fi)
        3. IP de Tailscale (si existe)
        Caché en memoria por 15 segundos para no penalizar peticiones continuas.
        """
        dev_hash = device["device_hash"]
        now = time.time()
        cached = self.active_targets.get(dev_hash)
        if cached and (now - cached["ts"] < 15.0):
            return (cached["host"], cached["port"])

        port = int(device.get("port", 19050))
        candidates: List[str] = []

        # 1. Prioridad: IPs reales reportadas por el dispositivo en su red local
        for ip in device.get("ips", []):
            if ip and ip not in candidates:
                candidates.append(ip)

        # 2. IP de Tailscale (si está disponible)
        ts_ip = device.get("tailscale_ip")
        if ts_ip and ts_ip not in candidates:
            candidates.append(ts_ip)

        # 3. Fallback a 127.0.0.1 solo si no hay IPs o como último recurso
        if "127.0.0.1" not in candidates:
            candidates.append("127.0.0.1")

        async def probe(h: str, p: int) -> bool:
            try:
                r, w = await asyncio.wait_for(asyncio.open_connection(h, p), timeout=0.6)
                # Enviar sondeo HTTP para verificar que el servidor TDM realmente responde
                w.write(b"HEAD / HTTP/1.0\r\nHost: probe\r\n\r\n")
                await w.drain()
                resp = await asyncio.wait_for(r.read(16), timeout=0.6)
                w.close()
                await w.wait_closed()
                return bool(resp and resp.startswith(b"HTTP/"))
            except Exception:
                return False

        for candidate in candidates:
            if await probe(candidate, port):
                self.active_targets[dev_hash] = {"host": candidate, "port": port, "ts": now}
                try:
                    self.db.set_last_active_ip(dev_hash, candidate)
                except Exception:
                    pass
                return (candidate, port)

        return None

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            line = await reader.readline()
            if not line:
                writer.close()
                return

            line_str = line.decode("utf-8", errors="ignore").strip()
            parts = line_str.split()
            if len(parts) < 2:
                writer.close()
                return

            method = parts[0].upper()
            full_path = parts[1]

            parsed_url = urllib.parse.urlparse(full_path)
            path = parsed_url.path
            query = parsed_url.query

            headers = {}
            content_length = 0
            while True:
                header_line = await reader.readline()
                if not header_line or header_line in (b"\r\n", b"\n"):
                    break
                h_str = header_line.decode("utf-8", errors="ignore").strip()
                if ":" in h_str:
                    k, v = h_str.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            if "content-length" in headers:
                try:
                    content_length = int(headers["content-length"])
                except ValueError:
                    content_length = 0

            body_bytes = b""
            if content_length > 0:
                body_bytes = await reader.readexactly(content_length)

            # -------------------------------------------------------------
            # 1. API Endpoints del Landing Page
            # -------------------------------------------------------------
            if path == "/api/register" and method == "POST":
                await self.handle_api_register(headers, body_bytes, writer)
                return

            if path == "/api/devices" and method == "GET":
                devices = self.db.list_devices()
                resp = json.dumps({"success": True, "count": len(devices), "devices": devices}).encode("utf-8")
                self.send_response(writer, 200, "application/json", resp)
                return

            if path.startswith("/api/device/") and method == "GET":
                req_hash = path[len("/api/device/"):].strip().lower()
                dev = self.db.get_device(req_hash)
                if dev:
                    resp = json.dumps({"success": True, "device": dev}).encode("utf-8")
                    self.send_response(writer, 200, "application/json", resp)
                else:
                    self.send_response(writer, 404, "application/json", b'{"success": false, "error": "device_not_found"}')
                return

            if path == "/api/version" and method in ("GET", "HEAD"):
                try:
                    from tdm.version import get_version_info
                    vdata = get_version_info()
                except Exception:
                    vdata = {"version": "0.0.86", "version_code": 86}
                vdata["download_url"] = "https://tdm.oton.cl/tdm-bundle.tar.gz"
                vdata["hub_url"] = "https://tdm.oton.cl"
                resp = json.dumps(vdata).encode("utf-8")
                self.send_response(writer, 200, "application/json", resp)
                return

            # -------------------------------------------------------------
            # 2. Reverse Proxy Dinámico por Hash de 8 letras (/<hash>/...)
            # -------------------------------------------------------------
            route_match = DEVICE_ROUTE_REGEX.match(path)
            if route_match:
                device_hash = route_match.group(1).lower()
                sub_path_raw = route_match.group(2)

                # Redirigir /<hash> a /<hash>/ para mantener consistencia de rutas relativas
                if sub_path_raw is None:
                    target_redirect = f"/{device_hash}/" + (f"?{query}" if query else "")
                    self.send_redirect(writer, target_redirect, cookie_device=device_hash)
                    return

                device = self.db.get_device(device_hash)
                if not device:
                    self.send_not_found_device(writer, device_hash)
                    return

                target = await self.find_active_target(device)
                if not target:
                    self.send_unreachable_device(writer, device_hash, device)
                    return

                target_host, target_port = target
                target_path = "/" + sub_path_raw if sub_path_raw else "/"

                is_ws = headers.get("upgrade", "").lower() == "websocket"
                if is_ws:
                    await self.proxy_websocket(target_host, target_port, target_path, query, headers, reader, writer)
                else:
                    await self.proxy_http(target_host, target_port, method, target_path, query, headers, body_bytes, writer, device_hash=device_hash)
                return

            # -------------------------------------------------------------
            # 2.5 Fallback Inteligente: Enrutar llamadas a /api, /ws, /novnc, etc. al dispositivo según Referer o Cookie
            # -------------------------------------------------------------
            fallback_hash = None
            cookie_hdr = headers.get("cookie", "")
            if "tdm_device=" in cookie_hdr:
                for c in cookie_hdr.split(";"):
                    c = c.strip()
                    if c.startswith("tdm_device="):
                        val = c.split("=", 1)[1].strip().lower()
                        if HASH_REGEX.match(val) and self.db.get_device(val):
                            fallback_hash = val
                            break

            if not fallback_hash and headers.get("referer"):
                ref = headers["referer"]
                ref_candidates = re.findall(r"/([a-z]{8})(?:/|$|\?)", ref)
                for cand in ref_candidates:
                    if self.db.get_device(cand.lower()):
                        fallback_hash = cand.lower()
                        break

            if fallback_hash and not path.startswith("/api/register") and not path.startswith("/api/devices") and not path.startswith("/api/device/"):
                if (
                    path.startswith("/api/")
                    or path.startswith("/ws/")
                    or path.startswith("/novnc/")
                    or path.startswith("/terminal/")
                    or path.startswith("/websockify")
                    or path in ("/sw.js", "/manifest.json")
                ):
                    device = self.db.get_device(fallback_hash)
                    if device:
                        target = await self.find_active_target(device)
                        if target:
                            target_host, target_port = target
                            target_path = path
                            is_ws = headers.get("upgrade", "").lower() == "websocket"
                            if is_ws:
                                await self.proxy_websocket(target_host, target_port, target_path, query, headers, reader, writer)
                            else:
                                await self.proxy_http(target_host, target_port, method, target_path, query, headers, body_bytes, writer, device_hash=fallback_hash)
                            return

            # -------------------------------------------------------------
            # 3. Reverse Proxy Legacy (/aabbcc y /aabbcc/*)
            # -------------------------------------------------------------
            if path == "/aabbcc":
                target = "/aabbcc/" + (f"?{query}" if query else "")
                self.send_redirect(writer, target)
                return

            if path.startswith("/aabbcc/"):
                target_path = path[7:] or "/"
                is_ws = headers.get("upgrade", "").lower() == "websocket"
                if is_ws:
                    await self.proxy_websocket(self.target_host, self.target_port, target_path, query, headers, reader, writer)
                else:
                    await self.proxy_http(self.target_host, self.target_port, method, target_path, query, headers, body_bytes, writer, device_hash="legacy")
                return

            # -------------------------------------------------------------
            # 4. Servir Archivos Estáticos de la Landing Page
            # -------------------------------------------------------------
            await self.serve_static(method, path, headers, writer)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            try:
                self.send_response(writer, 500, "text/plain", f"Error interno: {e}".encode("utf-8"))
            except Exception:
                pass
        finally:
            try:
                if not writer.is_closing():
                    writer.close()
                    await writer.wait_closed()
            except Exception:
                pass

    async def handle_api_register(self, headers: dict, body_bytes: bytes, writer: asyncio.StreamWriter):
        """Registra o actualiza un dispositivo TDM vía POST JSON."""
        try:
            data = json.loads(body_bytes.decode("utf-8"))
            dev_hash = data.get("hash", "").strip().lower()
            ips = data.get("ips", [])
            tailscale_ip = data.get("tailscale_ip")
            port = int(data.get("port", 19050))
            version = data.get("version", "")
            ua = headers.get("user-agent", "")

            if not dev_hash or not HASH_REGEX.match(dev_hash):
                self.send_response(
                    writer, 400, "application/json",
                    b'{"success":false,"error":"invalid_hash","message":"El hash debe tener exactamente 8 letras minusculas [a-z]"}'
                )
                return

            registered = self.db.register_device(
                device_hash=dev_hash,
                ips=ips,
                port=port,
                tailscale_ip=tailscale_ip,
                client_version=version,
                user_agent=ua
            )
            resp = json.dumps({"success": True, "device": registered}).encode("utf-8")
            self.send_response(writer, 200, "application/json", resp)
        except Exception as e:
            err = json.dumps({"success": False, "error": str(e)}).encode("utf-8")
            self.send_response(writer, 400, "application/json", err)

    async def proxy_http(
        self,
        target_host: str,
        target_port: int,
        method: str,
        target_path: str,
        query: str,
        headers: dict,
        body_bytes: bytes,
        writer: asyncio.StreamWriter,
        device_hash: Optional[str] = None
    ):
        """Reenvío de peticiones HTTP a la aplicación Web de TDM."""
        full_target = target_path
        if query:
            full_target = f"{full_target}?{query}"

        try:
            up_reader, up_writer = await asyncio.open_connection(target_host, target_port)

            req_lines = [f"{method} {full_target} HTTP/1.1"]
            for k, v in headers.items():
                if k.lower() in ("host", "connection", "accept-encoding"):
                    continue
                req_lines.append(f"{k}: {v}")
            req_lines.append(f"Host: {target_host}:{target_port}")
            req_lines.append("Connection: close")
            req_data = "\r\n".join(req_lines).encode("utf-8") + b"\r\n\r\n" + body_bytes

            up_writer.write(req_data)
            await up_writer.drain()

            while True:
                chunk = await up_reader.read(65536)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()

            up_writer.close()
            await up_writer.wait_closed()
        except Exception as e:
            if target_path.startswith("/api") or "application/json" in headers.get("accept", ""):
                json_msg = f'{{"error":"bad_gateway","message":"No se pudo conectar al runtime TDM en http://{target_host}:{target_port}","detail":"{str(e)}"}}'.encode("utf-8")
                self.send_response(writer, 502, "application/json", json_msg)
            else:
                self.send_unreachable_device(writer, device_hash or "desconocido", {"last_active_ip": target_host, "port": target_port}, detail=str(e))

    async def proxy_websocket(
        self,
        target_host: str,
        target_port: int,
        target_path: str,
        query: str,
        headers: dict,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """Reenvío bidireccional de WebSockets (noVNC websockify / Terminal PTY)."""
        full_target = target_path
        if query:
            full_target = f"{full_target}?{query}"

        try:
            up_reader, up_writer = await asyncio.open_connection(target_host, target_port)

            req_lines = [f"GET {full_target} HTTP/1.1"]
            for k, v in headers.items():
                if k.lower() == "host":
                    req_lines.append(f"Host: {target_host}:{target_port}")
                else:
                    req_lines.append(f"{k}: {v}")
            req_data = "\r\n".join(req_lines).encode("utf-8") + b"\r\n\r\n"

            up_writer.write(req_data)
            await up_writer.drain()

            async def pipe(r, w):
                try:
                    while True:
                        data = await r.read(65536)
                        if not data:
                            break
                        w.write(data)
                        await w.drain()
                except Exception:
                    pass
                finally:
                    try:
                        if not w.is_closing():
                            w.close()
                    except Exception:
                        pass

            await asyncio.gather(pipe(reader, up_writer), pipe(up_reader, writer))
        except Exception:
            pass

    def send_not_found_device(self, writer: asyncio.StreamWriter, device_hash: str):
        """Responde con aviso amigable cuando un hash de 8 letras no existe en SQLite."""
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[TDM] Dispositivo no encontrado</title>
    <style>
        body {{ background: #0b1120; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 1.5rem; box-sizing: border-box; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2.2rem; max-width: 540px; width: 100%; box-shadow: 0 10px 30px rgba(0,0,0,0.6); text-align: center; }}
        .tag {{ display: inline-block; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; background: rgba(234,179,8,0.15); color: #eab308; padding: 0.3rem 0.75rem; border-radius: 9999px; margin-bottom: 1rem; border: 1px solid rgba(234,179,8,0.3); }}
        h1 {{ font-size: 1.35rem; color: #f8fafc; margin: 0 0 0.75rem; font-weight: 600; }}
        p {{ font-size: 0.95rem; color: #94a3b8; line-height: 1.6; margin: 0.5rem 0 1.5rem; }}
        code {{ display: block; background: #0f172a; color: #38bdf8; padding: 0.9rem; border-radius: 8px; font-family: ui-monospace, monospace; font-size: 0.85rem; word-break: break-all; border: 1px solid #334155; }}
        .btn {{ display: inline-block; margin-top: 1.5rem; color: #38bdf8; text-decoration: none; font-size: 0.88rem; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="tag">[TDM] Dispositivo Inexistente</div>
        <h1>Identificador no Registrado</h1>
        <p>El código <strong>{device_hash}</strong> no corresponde a ningún dispositivo TDM registrado en el sistema.</p>
        <p>Para registrar tu teléfono Android, abre Termux y ejecuta:</p>
        <code>tdm register</code>
        <a class="btn" href="/">← Volver al inicio</a>
    </div>
</body>
</html>""".encode("utf-8")
        self.send_response(writer, 404, "text/html; charset=utf-8", html)

    def send_unreachable_device(self, writer: asyncio.StreamWriter, device_hash: str, device: dict, detail: str = ""):
        """Responde cuando el dispositivo está registrado pero ninguna IP responde."""
        ips = device.get("ips", [])
        ips_str = ", ".join(ips) if ips else "Ninguna IP local reportada"
        ts_ip = device.get("tailscale_ip")
        ts_info = f" • Tailscale: {ts_ip}" if ts_ip else ""

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[TDM] Dispositivo Inaccesible</title>
    <style>
        body {{ background: #0b1120; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 1.5rem; box-sizing: border-box; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2.2rem; max-width: 580px; width: 100%; box-shadow: 0 10px 30px rgba(0,0,0,0.6); text-align: left; }}
        .tag {{ display: inline-block; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; background: rgba(239,68,68,0.15); color: #ef4444; padding: 0.3rem 0.75rem; border-radius: 9999px; margin-bottom: 1rem; border: 1px solid rgba(239,68,68,0.3); }}
        h1 {{ font-size: 1.35rem; color: #f8fafc; margin: 0 0 0.75rem; font-weight: 600; text-align: center; }}
        p {{ font-size: 0.95rem; color: #94a3b8; line-height: 1.6; margin: 0.5rem 0 1.2rem; }}
        .box {{ background: #0f172a; padding: 1rem; border-radius: 8px; border: 1px solid #334155; margin-bottom: 1.2rem; font-size: 0.88rem; }}
        .box ul {{ margin: 0.5rem 0 0; padding-left: 1.2rem; color: #cbd5e1; }}
        .box li {{ margin-bottom: 0.3rem; }}
        code {{ color: #38bdf8; font-family: ui-monospace, monospace; }}
        .center {{ text-align: center; }}
        .btn {{ display: inline-block; color: #94a3b8; text-decoration: none; font-size: 0.88rem; border-bottom: 1px dashed #475569; padding-bottom: 2px; }}
        .btn:hover {{ color: #38bdf8; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="center"><div class="tag">[TDM] Dispositivo Inaccesible</div></div>
        <h1>No se pudo conectar con el dispositivo ({device_hash})</h1>
        <p>El identificador es válido, pero el servicio TDM en tu teléfono no responde en las IPs registradas (LAN: <code>{ips_str}</code>{ts_info}).</p>
        
        <div class="box">
            <strong>⚠️ Condición de Acceso Web:</strong>
            <ul>
                <li>Tu equipo actual (PC, tablet o laptop) debe estar conectado a la <strong>misma red Wi-Fi/local</strong> del teléfono.</li>
                <li>O bien, tener activo <strong>Tailscale</strong> en ambos dispositivos si estás fuera de casa.</li>
                <li>Verifica que el servicio TDM esté iniciado en Termux ejecutando: <code>tdm service restart</code>.</li>
            </ul>
        </div>
        
        <div class="center">
            <a class="btn" href="javascript:location.reload()">Reintentar Conexión</a> &nbsp;|&nbsp; 
            <a class="btn" href="/">Volver a Inicio</a>
        </div>
    </div>
</body>
</html>""".encode("utf-8")
        self.send_response(writer, 502, "text/html; charset=utf-8", html)

    async def serve_static(self, method: str, path: str, headers: dict, writer: asyncio.StreamWriter):
        rel = path.lstrip("/")

        # Proteger scripts contra visualización en navegadores web
        script_targets = ("install", "install.sh", "setup", "setup.sh", "get", "clean", "clean.sh", "reset", "go")
        if rel in script_targets:
            ua = headers.get("user-agent", "").lower()
            accept = headers.get("accept", "").lower()
            sec_fetch = headers.get("sec-fetch-mode", "").lower()

            has_browser_ua = any(b in ua for b in (
                "mozilla", "chrome", "safari", "webkit", "edge", "opera", "firefox", "msie", "trident", "android"
            ))
            is_browser = (
                has_browser_ua
                or "text/html" in accept
                or sec_fetch in ("navigate", "nested-navigate")
                or not any(ua.startswith(tool) for tool in ("curl", "wget", "tdm"))
            )

            if is_browser:
                forbidden_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[TDM] Acceso Restringido</title>
    <style>
        body {{ background: #0b1120; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 1.5rem; box-sizing: border-box; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2.2rem; max-width: 520px; width: 100%; box-shadow: 0 10px 30px rgba(0,0,0,0.6); text-align: center; }}
        .tag {{ display: inline-block; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; background: rgba(239,68,68,0.15); color: #ef4444; padding: 0.3rem 0.75rem; border-radius: 9999px; margin-bottom: 1rem; border: 1px solid rgba(239,68,68,0.3); }}
        h1 {{ font-size: 1.35rem; color: #f8fafc; margin: 0 0 0.75rem; font-weight: 600; }}
        p {{ font-size: 0.95rem; color: #94a3b8; line-height: 1.6; margin: 0.5rem 0 1.5rem; }}
        code {{ display: block; background: #0f172a; color: #38bdf8; padding: 0.9rem; border-radius: 8px; font-family: ui-monospace, monospace; font-size: 0.85rem; word-break: break-all; border: 1px solid #334155; user-select: all; }}
        .btn {{ display: inline-block; margin-top: 1.75rem; color: #94a3b8; text-decoration: none; font-size: 0.88rem; border-bottom: 1px dashed #475569; padding-bottom: 2px; }}
        .btn:hover {{ color: #38bdf8; border-bottom-color: #38bdf8; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="tag">[TDM] Acceso Restringido</div>
        <h1>Visualización Bloqueada</h1>
        <p>Este script está protegido contra visualización en navegadores web y consolas externas. Debe ejecutarse exclusivamente dentro de la consola de <strong>Termux en Android</strong>:</p>
        <code>curl -sSL https://tdm.oton.cl/{rel} | bash</code>
        <a class="btn" href="/">Volver a la página principal</a>
    </div>
</body>
</html>""".encode("utf-8")
                self.send_response(writer, 403, "text/html; charset=utf-8", forbidden_html)
                return

        if not rel or rel == "index.html":
            target_file = LANDING_DIR / "index.html"
        elif rel in ("install", "install.sh", "setup", "setup.sh", "get"):
            target_file = LANDING_DIR / "install.sh"
        elif rel in ("clean", "clean.sh", "reset"):
            target_file = LANDING_DIR / "clean.sh"
        elif rel == "go":
            target_file = LANDING_DIR / "go"
        elif rel in ("changelog", "changelog/", "changelog.html", "changelog/index.html"):
            target_file = LANDING_DIR / "changelog" / "index.html"
        else:
            target_file = LANDING_DIR / rel

        resolved = target_file.resolve()
        landing_res = LANDING_DIR.resolve()

        if landing_res not in resolved.parents and resolved != landing_res:
            self.send_response(writer, 403, "text/plain", b"403 Prohibido")
            return

        if not resolved.is_file():
            self.send_response(writer, 404, "text/plain", b"404 No Encontrado")
            return

        ext = resolved.suffix.lower()
        content_type, _ = mimetypes.guess_type(str(resolved))
        if not content_type:
            if ext in (".sh", ""):
                content_type = "text/plain; charset=utf-8"
            elif ext == ".gz":
                content_type = "application/gzip"
            else:
                content_type = "application/octet-stream"

        try:
            content = resolved.read_bytes()
            self.send_response(writer, 200, content_type, content)
        except Exception as e:
            self.send_response(writer, 500, "text/plain", f"Error: {e}".encode("utf-8"))

    def send_response(self, writer: asyncio.StreamWriter, status: int, ctype: str, body: bytes):
        status_text = {200: "OK", 400: "Bad Request", 403: "Forbidden", 404: "Not Found", 500: "Internal Server Error", 502: "Bad Gateway"}.get(status, "OK")
        resp = [
            f"HTTP/1.1 {status} {status_text}",
            f"Content-Type: {ctype}",
            f"Content-Length: {len(body)}",
            "Access-Control-Allow-Origin: *",
            "Connection: close",
            "",
            ""
        ]
        writer.write("\r\n".join(resp).encode("utf-8") + body)

    def send_redirect(self, writer: asyncio.StreamWriter, location: str, cookie_device: Optional[str] = None):
        resp = [
            "HTTP/1.1 301 Moved Permanently",
            f"Location: {location}",
            "Content-Length: 0",
            "Access-Control-Allow-Origin: *",
            "Connection: close",
        ]
        if cookie_device:
            resp.append(f"Set-Cookie: tdm_device={cookie_device}; Path=/; SameSite=Lax; Max-Age=86400")
        resp.extend(["", ""])
        writer.write("\r\n".join(resp).encode("utf-8"))

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"🌐 [Landing Page + HTTP-Proxy] Servidor iniciado en http://{self.host}:{self.port}")
        print(f"🔀 [Dynamic Reverse Proxy] Rutas /<hash>/ -> SQLite Activo con detección LAN/Tailscale")
        print(f"🔀 [HTTP Reverse Proxy Legacy] Ruta /aabbcc -> http://{self.target_host}:{self.target_port}")
        async with server:
            await server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TDM Landing Page + Reverse Proxy Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Puerto del servidor (default: 8080)")
    parser.add_argument("--target-host", default=os.environ.get("TDM_TARGET_HOST", "192.168.1.197"), help="Host destino legacy")
    parser.add_argument("--target-port", type=int, default=int(os.environ.get("TDM_TARGET_PORT", "19050")), help="Puerto destino legacy (default: 19050)")
    args = parser.parse_args()

    try:
        asyncio.run(LandingProxyServer(args.host, args.port, args.target_host, args.target_port).start())
    except KeyboardInterrupt:
        print("\nServidor detenido.")
