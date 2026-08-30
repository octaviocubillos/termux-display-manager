"""
Servidor HTTP Asíncrono de Alto Rendimiento para TDM (Termux Display Manager).
Implementación pura sin dependencias externas (Zero-Dependency) basada en asyncio.
Soporta API REST, archivos estáticos Web/PWA y WebSockets nativos RFC 6455.
"""

import asyncio
import json
import mimetypes
import os
import secrets
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional

from tdm.server.websocket import WebSocketConnection
from tdm.server.hub import hub_manager
from tdm.core.display_manager import display_manager
from tdm.core.installer import installer_service
from tdm.core.uninstaller import uninstaller_service
from tdm.discovery.network import network_discovery
from tdm.version import get_version_info

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
PROTOTYPE_DIR = BASE_DIR.parent / "web-prototype"

class AsyncHTTPServer:
    """Servidor HTTP y WebSocket asíncrono para el panel Web / PWA y Hub de TDM."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9050, is_hub: bool = False):
        self.is_hub = is_hub
        self.host = host
        self.port = port
        self.server: Optional[asyncio.AbstractServer] = None
        self.running = False

    async def start(self):
        """Inicia el servidor asíncrono."""
        self.running = True
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        
        # Auto-descubrimiento de interfaces de red
        net_info = network_discovery.get_all_interfaces()
        
        print("\n" + "=" * 55)
        print(f"🚀 [TDM Server] Servidor Web y WebSocket Activo")
        print("=" * 55)
        print("🌐 Direcciones de Acceso:")
        print(f"  • Local:        http://localhost:{self.port}")
        if net_info.get("lan_ip"):
            print(f"  • Red LAN:      http://{net_info['lan_ip']}:{self.port}")
        if net_info.get("tailscale_ip"):
            print(f"  • Tailscale:    http://{net_info['tailscale_ip']}:{self.port} 🔒")
        print("=" * 55 + "\n")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Detiene el servidor."""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Procesa conexiones entrantes (HTTP o WebSocket Upgrade)."""
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                return

            line_str = request_line.decode("utf-8", errors="ignore").strip()
            if not line_str:
                writer.close()
                return

            parts = line_str.split()
            if len(parts) < 2:
                writer.close()
                return

            method = parts[0].upper()
            full_path = parts[1]

            # Parsear URL y Query Params
            parsed_url = urllib.parse.urlparse(full_path)
            path = parsed_url.path
            query_params = urllib.parse.parse_qs(parsed_url.query)

            # Leer Cabeceras
            headers = {}
            content_length = 0
            while True:
                header_line = await reader.readline()
                if not header_line or header_line == b"\r\n" or header_line == b"\n":
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

            # Verificar si es una petición WebSocket Upgrade
            if headers.get("upgrade", "").lower() == "websocket":
                await self.handle_websocket_upgrade(path, headers, reader, writer)
                return

            # Leer cuerpo HTTP (POST / PUT)
            body_bytes = b""
            if content_length > 0:
                body_bytes = await reader.readexactly(content_length)

            # Enrutar Petición HTTP
            await self.route_request(method, path, headers, query_params, body_bytes, writer)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            try:
                self.send_json_response(writer, {"error": str(e)}, status_code=500)
            except Exception:
                pass
        finally:
            try:
                if not writer.is_closing():
                    writer.close()
                    await writer.wait_closed()
            except Exception:
                pass

    async def handle_websocket_upgrade(self, path: str, headers: dict, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Gestiona el handshake y ciclo de vida de WebSockets."""
        ws = await WebSocketConnection.server_handshake(reader, writer, headers)
        if not ws:
            return

        # 1. Conexión de Agente Termux: /ws/agent/{token}
        if path.startswith("/ws/agent/"):
            token = path.split("/ws/agent/")[1].strip()
            print(f"🔌 [Hub] Agente de Termux conectado con token '{token}'")
            session = hub_manager.get_or_create_session(token)
            session.agent_ws = ws

            await hub_manager.register_agent(token, ws)

            try:
                while not ws.closed:
                    msg = await ws.recv_json()
                    if msg is None:
                        break
                    # Reenviar mensajes del agente a los navegadores vinculados
                    await session.broadcast_to_clients(msg)
            finally:
                await hub_manager.unregister_agent(token)
                await ws.close()
            return

        # 2. Conexión de Cliente Web / PWA: /ws/client/{token}
        elif path.startswith("/ws/client/"):
            token = path.split("/ws/client/")[1].strip()
            print(f"💻 [Hub] Cliente Web conectado con token '{token}'")
            session = hub_manager.get_or_create_session(token)

            await hub_manager.register_client(token, ws)

            try:
                while not ws.closed:
                    msg = await ws.recv_json()
                    if msg is None:
                        break
                    
                    # Si es orden de eliminación de sesión / dispositivo
                    if msg.get("type") in ["delete_device", "delete_session"]:
                        await hub_manager.delete_session(session.token)
                        await ws.send_json({
                            "type": "response",
                            "req_id": msg.get("req_id"),
                            "result": {"deleted": True}
                        })
                        continue

                    # Reenviar comando del navegador al agente Termux de esta sesión
                    sent = await session.send_to_agent(msg)
                    if not sent:
                        await ws.send_json({
                            "type": "error",
                            "req_id": msg.get("req_id"),
                            "error": "El dispositivo Termux no está conectado o no responde."
                        })
            finally:
                await hub_manager.unregister_client(token, ws)
                await ws.close()
            return

        # 3. Conexión WebSocket Local: /ws o /ws/local
        elif path in ["/ws", "/ws/local"]:
            try:
                def on_local_log(line):
                    asyncio.create_task(ws.send_json({"type": "log", "line": line}))
                
                installer_service.subscribe(on_local_log)
                await ws.send_json({"type": "connected", "message": "Canal local WebSocket activo"})

                while not ws.closed:
                    msg = await ws.recv_json()
                    if msg is None:
                        break
                    if msg.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
            finally:
                installer_service.unsubscribe(on_local_log)
                await ws.close()
            return

        else:
            await ws.close()

    async def route_request(self, method: str, path: str, headers: dict, query_params: dict, body_bytes: bytes, writer: asyncio.StreamWriter):
        host_hdr = headers.get("x-forwarded-host") or headers.get("host", f"localhost:{self.port}")
        proto = "https" if (headers.get("x-forwarded-proto") == "https" or headers.get("x-forwarded-ssl") == "on") else "http"
        base_url = f"{proto}://{host_hdr}"

        # 1. Generador de Script de Instalación / Bootstrap para Termux (/go, /setup, /install)
        if path in ["/go", "/setup", "/setup.sh", "/install", "/install.sh", "/get"]:
            token = query_params.get("token", [None])[0] or query_params.get("t", [None])[0]
            session = hub_manager.get_or_create_session(token)
            script_content = hub_manager.generate_setup_script(base_url, session.token)
            self.send_text_response(writer, script_content, content_type="text/x-shellscript")
            return

        # 2. Generar nuevo Token de Emparejamiento
        if path == "/api/token/new" and method == "GET":
            session = hub_manager.get_or_create_session()
            setup_cmd = f'apt-get update -y && apt-get install -y -o Dpkg::Options::="--force-confold" openssl curl && curl -sSL {base_url}/go?t={session.token} | bash'
            self.send_json_response(writer, {
                "token": session.token,
                "setup_cmd": setup_cmd,
                "base_url": base_url
            })
            return

        # 3. Consultar Estado de Emparejamiento
        if path.startswith("/api/token/status/") and method == "GET":
            token = path.split("/api/token/status/")[1].strip()
            session = hub_manager.get_session(token)
            if not session:
                self.send_json_response(writer, {"token": token, "exists": False, "agent_connected": False})
            else:
                self.send_json_response(writer, {
                    "token": token,
                    "exists": True,
                    "agent_connected": session.is_agent_connected,
                    "device_info": session.device_info
                })
            return

        # 4. PWA: Manifest y Service Worker
        if path in ["/manifest.json", "/manifest.webmanifest"]:
            manifest_file = WEB_DIR / "manifest.json"
            if not manifest_file.exists():
                manifest_file = PROTOTYPE_DIR / "manifest.json"
            if manifest_file.exists():
                self.send_file_response(writer, manifest_file, content_type="application/manifest+json")
                return

        if path in ["/service-worker.js", "/sw.js"]:
            sw_file = WEB_DIR / "service-worker.js"
            if not sw_file.exists():
                sw_file = PROTOTYPE_DIR / "service-worker.js"
            if sw_file.exists():
                self.send_file_response(writer, sw_file, content_type="application/javascript")
                return

        # 5. Iconos PWA
        if path.startswith("/icons/"):
            icon_name = path.split("/icons/")[1]
            icon_file = WEB_DIR / "icons" / icon_name
            if not icon_file.exists():
                icon_file = PROTOTYPE_DIR / "icons" / icon_name
            if icon_file.exists():
                self.send_file_response(writer, icon_file, content_type="image/png")
                return

        # 6. Bundle descargable autónomo (/tdm-bundle.tar.gz)
        if path in ["/tdm-bundle.tar.gz", "/download/tdm-bundle.tar.gz"]:
            bundle_file = WEB_DIR / "tdm-bundle.tar.gz"
            if not bundle_file.exists():
                bundle_file = PROTOTYPE_DIR / "tdm-bundle.tar.gz"
            if bundle_file.exists():
                self.send_file_response(writer, bundle_file, content_type="application/gzip")
                return

        # 7. Endpoint Estado General: /api/status
        if path == "/api/status" and method == "GET":
            status_data = display_manager.get_status()
            self.send_json_response(writer, status_data)
            return

        # 8. Endpoint de Red: /api/system/network
        if path == "/api/system/network" and method == "GET":
            net_data = network_discovery.get_all_interfaces(self.port)
            self.send_json_response(writer, net_data)
            return

        # 9. Control de Pantalla: /api/screen/start y /api/screen/stop
        if path == "/api/screen/start" and method == "POST":
            try:
                req_data = json.loads(body_bytes.decode("utf-8") or "{}")
                session_dict = await display_manager.start_screen(
                    backend=req_data.get("backend", "termux-x11"),
                    mode=req_data.get("mode", "desktop"),
                    desktop_id=req_data.get("desktop"),
                    resolution=req_data.get("resolution", "1080x2400"),
                    dpi=req_data.get("dpi", 140),
                    audio=req_data.get("audio", True),
                    virgl=req_data.get("virgl", True)
                )
                self.send_json_response(writer, session_dict)
            except Exception as e:
                self.send_json_response(writer, {"error": str(e)}, status_code=400)
            return

        if path == "/api/screen/stop" and method == "POST":
            stopped = await display_manager.stop_screen()
            self.send_json_response(writer, {"stopped": stopped})
            return

        # 10. Instalador de Componentes: /api/install/desktop y /api/install/server
        if path == "/api/install/desktop" and method == "POST":
            req_data = json.loads(body_bytes.decode("utf-8") or "{}")
            target = req_data.get("desktop") or req_data.get("target")
            success = await installer_service.install_desktop(target)
            self.send_json_response(writer, {"success": success, "target": target, "message": f"Instalación de {target} iniciada"})
            return

        if path == "/api/install/server" and method == "POST":
            req_data = json.loads(body_bytes.decode("utf-8") or "{}")
            target = req_data.get("server") or req_data.get("target")
            success = await installer_service.install_server(target)
            self.send_json_response(writer, {"success": success, "target": target, "message": f"Instalación de servidor {target} iniciada"})
            return

        # 11. Archivos Estáticos Web (HTML, CSS, JS)
        if path in ["/", "/index.html"]:
            index_file = WEB_DIR / "index.html"
            if not index_file.exists():
                index_file = PROTOTYPE_DIR / "index.html"
            if index_file.exists():
                self.send_file_response(writer, index_file, content_type="text/html")
                return

        # Fallback 404
        self.send_json_response(writer, {"error": "Ruta no encontrada", "path": path}, status_code=404)

    def send_json_response(self, writer: asyncio.StreamWriter, data: Any, status_code: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        headers = [
            f"HTTP/1.1 {status_code} OK",
            "Content-Type: application/json; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Access-Control-Allow-Origin: *",
            "Connection: close",
            "\r\n"
        ]
        writer.write("\r\n".join(headers).encode("utf-8") + body)

    def send_text_response(self, writer: asyncio.StreamWriter, text: str, content_type: str = "text/plain", status_code: int = 200):
        body = text.encode("utf-8")
        headers = [
            f"HTTP/1.1 {status_code} OK",
            f"Content-Type: {content_type}; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Access-Control-Allow-Origin: *",
            "Connection: close",
            "\r\n"
        ]
        writer.write("\r\n".join(headers).encode("utf-8") + body)

    def send_file_response(self, writer: asyncio.StreamWriter, file_path: Path, content_type: str = "text/plain", status_code: int = 200):
        try:
            with open(file_path, "rb") as f:
                body = f.read()
            headers = [
                f"HTTP/1.1 {status_code} OK",
                f"Content-Type: {content_type}",
                f"Content-Length: {len(body)}",
                "Access-Control-Allow-Origin: *",
                "Connection: close",
                "\r\n"
            ]
            writer.write("\r\n".join(headers).encode("utf-8") + body)
        except Exception:
            self.send_json_response(writer, {"error": "Error leyendo archivo"}, status_code=500)
