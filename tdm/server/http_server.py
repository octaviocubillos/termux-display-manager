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
import shutil
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional

from tdm.constants import PORT_TDM_SERVER, PORT_VNC_DEFAULT
from tdm.server.websocket import WebSocketConnection
from tdm.server.hub import hub_manager
from tdm.core.display_manager import display_manager
from tdm.core.installer import installer_service
from tdm.core.uninstaller import uninstaller_service
from tdm.discovery.network import network_discovery
from tdm.version import get_version_info
from tdm.cli.main import execute_cli_command
from tdm.config import get_user_shell

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

class AsyncHTTPServer:
    """Servidor HTTP y WebSocket asíncrono para el panel Web / PWA y Hub de TDM."""

    def __init__(self, host: str = "0.0.0.0", port: int = PORT_TDM_SERVER, is_hub: bool = False):
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
        if net_info.get("web"):
            print(f"  • Web:          {net_info['web']}")
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

        # 3. Conexión WebSocket Local Bidireccional (Telemetría + RPC): /ws o /ws/local
        elif path in ["/ws", "/ws/local"]:
            await self.handle_local_ws(ws)
            return

        # 4. Puente Nativo WebSocket <-> VNC RFB (/websockify, /ws/vnc)
        elif path in ["/websockify", "/ws/vnc", "/ws/novnc"] or path.startswith("/websockify"):
            await self.handle_vnc_bridge(ws)
            return

        # 5. Puente Interactivo WebSocket <-> Termux PTY (/ws/terminal, /terminal/ws, /ws/pty)
        elif path in ["/ws/terminal", "/terminal/ws", "/ws/pty"] or path.startswith("/ws/terminal"):
            await self.handle_terminal_pty_ws(ws)
            return

        else:
            await ws.close()

    async def handle_local_ws(self, ws: WebSocketConnection):
        """Gestiona el canal bidireccional WebSocket para telemetría en tiempo real y comandos RPC."""
        def on_local_log(line):
            asyncio.create_task(ws.send_json({"type": "log", "line": line}))

        def on_local_progress(prog):
            asyncio.create_task(ws.send_json({"type": "progress", "data": prog}))

        installer_service.subscribe(on_local_log)
        installer_service.subscribe_progress(on_local_progress)

        # Enviar estado inicial y confirmación de conexión inmediatamente
        try:
            initial_status = display_manager.get_status()
            await ws.send_json({
                "type": "connected",
                "message": "Canal local WebSocket activo",
                "status": initial_status,
                "version": get_version_info()
            })
        except Exception:
            pass

        # Tarea de emisión periódica de telemetría a través del WebSocket (cada 2.5s)
        async def telemetry_stream():
            try:
                while not ws.closed:
                    await asyncio.sleep(2.5)
                    if ws.closed:
                        break
                    st = display_manager.get_status()
                    await ws.send_json({"type": "status_update", "data": st})
            except Exception:
                pass

        stream_task = asyncio.create_task(telemetry_stream())

        try:
            while not ws.closed:
                msg = await ws.recv_json()
                if msg is None:
                    break

                req_type = msg.get("type") or msg.get("action")
                req_id = msg.get("id") or msg.get("req_id")

                # 1. Ping / Latencia (calculado por WebSocket)
                if req_type == "ping":
                    await ws.send_json({
                        "type": "pong",
                        "id": req_id,
                        "t0": msg.get("t0"),
                        "server_time": time.time()
                    })

                # 2. Consultar Estado
                elif req_type in ["get_status", "status"]:
                    res = await execute_cli_command(["status"])
                    await ws.send_json({
                        "type": "status_response",
                        "id": req_id,
                        "data": res.get("data", display_manager.get_status())
                    })

                # 3. Iniciar Pantalla (Delegado al CLI: tdm start)
                elif req_type in ["start_screen", "screen_start"]:
                    payload = msg.get("payload") or msg.get("data") or {}
                    cmd_args = ["start", "--backend", payload.get("backend", "termux-x11"), "--mode", payload.get("mode", "desktop")]
                    if payload.get("desktop"):
                        cmd_args.extend(["--desktop", payload.get("desktop")])
                    if payload.get("resolution"):
                        cmd_args.extend(["--resolution", payload.get("resolution")])
                    if payload.get("dpi"):
                        cmd_args.extend(["--dpi", str(payload.get("dpi"))])
                    if not payload.get("audio", True):
                        cmd_args.append("--no-audio")
                    if not payload.get("virgl", False):
                        cmd_args.append("--no-virgl")

                    res = await execute_cli_command(cmd_args)
                    await ws.send_json({
                        "type": "action_result",
                        "action": "start_screen",
                        "id": req_id,
                        "success": res.get("success", False),
                        "data": res.get("data"),
                        "error": res.get("error")
                    })
                    st = display_manager.get_status()
                    await ws.send_json({"type": "status_update", "data": st})

                # 4. Apagar Pantalla (Delegado al CLI: tdm stop)
                elif req_type in ["stop_screen", "screen_stop"]:
                    res = await execute_cli_command(["stop"])
                    await ws.send_json({
                        "type": "action_result",
                        "action": "stop_screen",
                        "id": req_id,
                        "success": res.get("success", False),
                        "stopped": res.get("stopped", True),
                        "message": "Pantalla apagada correctamente"
                    })
                    st = display_manager.get_status()
                    await ws.send_json({"type": "status_update", "data": st})

                # 5. Apagar Todo (Delegado al CLI: tdm service stop)
                elif req_type in ["stop_service", "shutdown", "stop_all"]:
                    res = await execute_cli_command(["service", "stop"])
                    await ws.send_json({
                        "type": "action_result",
                        "action": "stop_service",
                        "id": req_id,
                        "success": True,
                        "message": "Entorno y procesos gráficos apagados al 100%. Gestor TDM activo."
                    })
                    st = display_manager.get_status()
                    await ws.send_json({"type": "status_update", "data": st})

                # 6. Cambiar factor de escala del escritorio (Delegado al CLI: tdm scale)
                elif req_type in ["set_desktop_scale", "scale_desktop"]:
                    payload = msg.get("payload") or msg.get("data") or {}
                    scale_factor = str(payload.get("scale", 2))
                    res = await execute_cli_command(["scale", scale_factor])
                    await ws.send_json({
                        "type": "action_result",
                        "action": "set_desktop_scale",
                        "id": req_id,
                        **res
                    })

                # 7. Instalar Entorno de Escritorio (Delegado al CLI: tdm install --desktop)
                elif req_type in ["install_desktop", "install"]:
                    payload = msg.get("payload") or msg.get("data") or {}
                    target = payload.get("desktop") or payload.get("target") or msg.get("desktop")
                    res = await execute_cli_command(["install", "--desktop", str(target)])
                    await ws.send_json({
                        "type": "action_result",
                        "action": "install_desktop",
                        "id": req_id,
                        "success": res.get("success", False),
                        "target": target,
                        "message": f"Instalación de {target} finalizada"
                    })
                    st = display_manager.get_status()
                    await ws.send_json({"type": "status_update", "data": st})

                # 8. Desinstalar Entorno de Escritorio (Delegado al CLI: tdm uninstall --desktop)
                elif req_type in ["uninstall_desktop", "uninstall_de", "purge_desktop"]:
                    payload = msg.get("payload") or msg.get("data") or {}
                    target = payload.get("desktop") or payload.get("target") or msg.get("desktop") or "all"
                    res = await execute_cli_command(["uninstall", "--desktop", str(target)])
                    await ws.send_json({
                        "type": "action_result",
                        "action": "uninstall_desktop",
                        "id": req_id,
                        "success": res.get("success", False),
                        "target": target,
                        "message": f"Desinstalación de entorno finalizada"
                    })
                    st = display_manager.get_status()
                    await ws.send_json({"type": "status_update", "data": st})

                # 9. Cancelar / Abortar Instalación (Delegado al CLI: tdm cancel-install)
                elif req_type in ["cancel_install", "install_cancel", "abort_install"]:
                    res = await execute_cli_command(["cancel-install"])
                    await ws.send_json({
                        "type": "action_result",
                        "action": "cancel_install",
                        "id": req_id,
                        "success": True,
                        "data": res.get("data")
                    })
                    st = display_manager.get_status()
                    await ws.send_json({"type": "status_update", "data": st})

                # 10. Obtener Versión (Delegado al CLI: tdm version)
                elif req_type in ["get_version", "version"]:
                    res = await execute_cli_command(["version"])
                    await ws.send_json({
                        "type": "version_response",
                        "id": req_id,
                        "data": res.get("data", get_version_info())
                    })
                    await ws.send_json({
                        "type": "version_response",
                        "id": req_id,
                        "data": get_version_info()
                    })

        finally:
            stream_task.cancel()
            installer_service.unsubscribe(on_local_log)
            installer_service.unsubscribe_progress(on_local_progress)
            await ws.close()

    async def handle_vnc_bridge(self, ws: WebSocketConnection, target_host: str = "127.0.0.1", target_port: int = PORT_VNC_DEFAULT):
        """Puente nativo asíncrono WebSocket (noVNC RFC 6455) a TCP (TigerVNC RFB) sin dependencias externas."""
        try:
            if display_manager.active_session and display_manager.active_session.config.vnc_port:
                target_port = display_manager.active_session.config.vnc_port
        except Exception:
            pass

        try:
            tcp_reader, tcp_writer = await asyncio.open_connection(target_host, target_port)
        except Exception as e:
            print(f"[!] Error conectando puente VNC TCP {target_host}:{target_port} -> {e}")
            await ws.close()
            return

        async def tcp_to_ws():
            try:
                while not ws.closed:
                    data = await tcp_reader.read(65536)
                    if not data:
                        break
                    await ws.send_binary(data)
            except Exception:
                pass
            finally:
                await ws.close()

        async def ws_to_tcp():
            try:
                while not ws.closed:
                    opcode, payload = await ws.recv_frame()
                    if opcode == 0x8 or ws.closed:
                        break
                    if opcode in (0x1, 0x2) and payload:
                        tcp_writer.write(payload)
                        await tcp_writer.drain()
            except Exception:
                pass
            finally:
                try:
                    tcp_writer.close()
                    await tcp_writer.wait_closed()
                except Exception:
                    pass

        try:
            await asyncio.gather(tcp_to_ws(), ws_to_tcp())
        finally:
            await ws.close()

    async def handle_terminal_pty_ws(self, ws: WebSocketConnection):
        """Puente interactivo WebSocket <-> Termux PTY (Terminal bash interactivo con xterm.js)."""
        import termios
        import struct
        import fcntl
        import os
        import subprocess

        try:
            master_fd, slave_fd = os.openpty()
        except (AttributeError, OSError):
            try:
                import pty
                master_fd, slave_fd = pty.openpty()
            except Exception as e:
                print(f"[!] Error abriendo pseudo-terminal (pty): {e}")
                await ws.close()
                return

        prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
        home = os.environ.get("HOME", "/data/data/com.termux/files/home")

        # Determinar el shell del usuario (bash por defecto a menos que se haya configurado otro)
        shell_bin = get_user_shell()

        env = {
            **os.environ,
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "LANG": os.environ.get("LANG", "en_US.UTF-8"),
            "PATH": f"{prefix}/bin:" + os.environ.get("PATH", "/usr/bin:/bin"),
            "SHELL": shell_bin,
            "HOME": home,
            "PREFIX": prefix
        }

        # Establecer tamaño inicial del terminal (cols=90, rows=28)
        try:
            winsize = struct.pack("HHHH", 28, 90, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            pass

        proc = subprocess.Popen(
            [shell_bin, "-l"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=home if os.path.exists(home) else "/",
            env=env,
            preexec_fn=os.setsid,
            close_fds=True
        )
        os.close(slave_fd)

        loop = asyncio.get_event_loop()
        output_queue = asyncio.Queue()

        def on_pty_readable():
            try:
                data = os.read(master_fd, 4096)
                if data:
                    loop.call_soon_threadsafe(output_queue.put_nowait, data)
                else:
                    loop.call_soon_threadsafe(output_queue.put_nowait, None)
            except Exception:
                loop.call_soon_threadsafe(output_queue.put_nowait, None)

        loop.add_reader(master_fd, on_pty_readable)

        async def pty_to_ws():
            try:
                while not ws.closed:
                    data = await output_queue.get()
                    if data is None:
                        break
                    await ws.send_binary(data)
            except Exception:
                pass

        async def ws_to_pty():
            try:
                while not ws.closed:
                    try:
                        opcode, payload = await ws.recv_frame()
                    except Exception:
                        break
                    if opcode == 0x08 or ws.closed:
                        break
                    elif opcode in (0x01, 0x02):
                        if opcode == 0x01 and payload:
                            try:
                                text_str = payload.decode("utf-8")
                                if text_str.startswith("{") and text_str.endswith("}"):
                                    cmd = json.loads(text_str)
                                    if cmd.get("type") == "resize":
                                        cols = int(cmd.get("cols", 80))
                                        rows = int(cmd.get("rows", 24))
                                        winsize = struct.pack("HHHH", rows, cols, 0, 0)
                                        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
                                        continue
                            except Exception:
                                pass
                        if payload:
                            os.write(master_fd, payload)
            except Exception:
                pass

        writer_task = asyncio.create_task(pty_to_ws())
        reader_task = asyncio.create_task(ws_to_pty())

        try:
            done, pending = await asyncio.wait([writer_task, reader_task], return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
        finally:
            try:
                loop.remove_reader(master_fd)
            except Exception:
                pass
            try:
                os.close(master_fd)
            except Exception:
                pass
            try:
                proc.terminate()
            except Exception:
                pass
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

        # 4. Endpoints de Estado y Red
        if path == "/api/status" and method in ["GET", "HEAD"]:
            status_data = display_manager.get_status()
            self.send_json_response(writer, status_data)
            return

        if path == "/api/system/network" and method in ["GET", "HEAD"]:
            net_data = network_discovery.get_all_interfaces(self.port)
            self.send_json_response(writer, net_data)
            return

        if path in ["/api/system/check", "/api/system/stats"] and method in ["GET", "HEAD"]:
            from tdm.discovery.desktops import discover_desktops
            from tdm.discovery.backends import discover_backends
            from tdm.core.telemetry import get_full_system_telemetry
            telemetry = get_full_system_telemetry()
            check_data = {
                "desktops": discover_desktops(),
                "backends": discover_backends(),
                "network": network_discovery.get_all_interfaces(self.port),
                **telemetry,
                "version": get_version_info()
            }
            self.send_json_response(writer, check_data)
            return

        # 5. Control de Pantalla (Delegado al CLI: tdm start / tdm stop / tdm scale)
        if path == "/api/screen/start" and method == "POST":
            req_data = json.loads(body_bytes.decode("utf-8") or "{}")
            cmd_args = ["start", "--backend", req_data.get("backend", "termux-x11"), "--mode", req_data.get("mode", "desktop")]
            if req_data.get("desktop"):
                cmd_args.extend(["--desktop", req_data.get("desktop")])
            if req_data.get("resolution"):
                cmd_args.extend(["--resolution", req_data.get("resolution")])
            if req_data.get("dpi"):
                cmd_args.extend(["--dpi", str(req_data.get("dpi"))])
            if not req_data.get("audio", True):
                cmd_args.append("--no-audio")
            if not req_data.get("virgl", False):
                cmd_args.append("--no-virgl")

            res = await execute_cli_command(cmd_args)
            if res.get("success"):
                self.send_json_response(writer, res.get("data", {}))
            else:
                self.send_json_response(writer, {"error": res.get("error", "Error al iniciar pantalla")}, status_code=400)
            return

        if path == "/api/screen/stop" and method == "POST":
            res = await execute_cli_command(["stop"])
            self.send_json_response(writer, {"stopped": res.get("stopped", True), "message": "Pantalla apagada correctamente"})
            return

        # Endpoints específicos para noVNC Web
        if path == "/api/novnc/status" and method == "GET":
            info = display_manager.get_novnc_info()
            self.send_json_response(writer, info)
            return

        if path == "/api/novnc/url" and method == "GET":
            info = display_manager.get_novnc_info()
            self.send_json_response(writer, {"url": info["urls"]["direct"], "urls": info["urls"]})
            return

        if path == "/api/novnc/start" and method == "POST":
            req_data = json.loads(body_bytes.decode("utf-8") or "{}")
            cmd_args = ["start", "--backend", "novnc", "--mode", req_data.get("mode", "desktop")]
            if req_data.get("desktop"):
                cmd_args.extend(["--desktop", req_data.get("desktop")])
            if req_data.get("resolution"):
                cmd_args.extend(["--resolution", req_data.get("resolution")])
            if req_data.get("dpi"):
                cmd_args.extend(["--dpi", str(req_data.get("dpi"))])
            if not req_data.get("audio", True):
                cmd_args.append("--no-audio")
            if not req_data.get("virgl", False):
                cmd_args.append("--no-virgl")

            res = await execute_cli_command(cmd_args)
            if res.get("success"):
                self.send_json_response(writer, res.get("data", {}))
            else:
                self.send_json_response(writer, {"error": res.get("error", "Error al iniciar noVNC")}, status_code=400)
            return

        if path == "/api/screen/scale" and method == "POST":
            req_data = json.loads(body_bytes.decode("utf-8") or "{}")
            scale_factor = str(req_data.get("scale", 2))
            res = await execute_cli_command(["scale", scale_factor])
            self.send_json_response(writer, res)
            return

        if path == "/api/novnc/stop" and method == "POST":
            res = await execute_cli_command(["stop"])
            self.send_json_response(writer, {"stopped": res.get("stopped", True), "message": "Sesión noVNC apagada correctamente"})
            return

        if path in ["/api/service/stop", "/api/system/shutdown"] and method == "POST":
            res = await execute_cli_command(["service", "stop"])
            self.send_json_response(writer, {
                "stopped": True,
                "message": "Entorno y procesos gráficos apagados al 100%. Gestor TDM activo."
            })
            return

        if path in ["/api/service/restart", "/api/system/restart"] and method == "POST":
            self.send_json_response(writer, {
                "success": True,
                "message": "Reiniciando demonio TDM en segundo plano..."
            })
            await writer.drain()
            try:
                loop = asyncio.get_event_loop()
                loop.call_later(0.5, lambda: os.execv(sys.executable, [sys.executable] + sys.argv))
            except Exception:
                pass
            return

        # 6. Instalador de Componentes (Delegado al CLI: tdm install / uninstall / cancel)
        if path == "/api/install/desktop" and method == "POST":
            req_data = json.loads(body_bytes.decode("utf-8") or "{}")
            target = str(req_data.get("desktop") or req_data.get("target"))
            res = await execute_cli_command(["install", "--desktop", target])
            self.send_json_response(writer, {"success": res.get("success", False), "target": target, "message": f"Instalación de {target} iniciada"})
            return

        if path in ["/api/install/cancel", "/api/install/abort"] and method == "POST":
            res = await execute_cli_command(["cancel-install"])
            self.send_json_response(writer, {"success": True, "data": res.get("data")})
            return

        if path == "/api/uninstall/desktop" and method == "POST":
            req_data = json.loads(body_bytes.decode("utf-8") or "{}")
            target = str(req_data.get("desktop") or req_data.get("target") or "all")
            res = await execute_cli_command(["uninstall", "--desktop", target])
            self.send_json_response(writer, {"success": res.get("success", False), "target": target, "message": f"Desinstalación de {target} finalizada"})
            return

        # 7. Permisos de Android para Termux:X11 (Delegado al CLI: tdm permissions)
        if path in ["/api/system/permissions", "/api/permissions"] and method in ["POST", "GET"]:
            res = await execute_cli_command(["permissions"])
            self.send_json_response(writer, res)
            return

        # 8. Diagnóstico y Depuración del Sistema
        if path == "/api/debug/system" and method == "GET":
            prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
            usr_bin = f"{prefix}/bin"
            files_in_bin = []
            if os.path.exists(usr_bin):
                try:
                    files_in_bin = [f for f in os.listdir(usr_bin) if any(k in f for k in ["i3", "xfce", "x11", "vnc", "plasma", "mate", "lxqt", "openbox", "termux"])]
                except Exception as e:
                    files_in_bin = [str(e)]
            
            from tdm.constants import find_binary
            checks = {
                "i3": find_binary("i3"),
                "xfce4-session": find_binary("xfce4-session"),
                "startxfce4": find_binary("startxfce4"),
                "termux-x11": find_binary("termux-x11"),
                "Xvnc": find_binary("Xvnc"),
            }
            
            self.send_json_response(writer, {
                "prefix": prefix,
                "path_env": os.environ.get("PATH", ""),
                "sys_path": sys.path,
                "files_in_bin": sorted(files_in_bin),
                "checks": checks,
                "installed_desktop": display_manager.get_installed_desktop()
            })
            return

        if path == "/api/install/server" and method == "POST":
            req_data = json.loads(body_bytes.decode("utf-8") or "{}")
            target = req_data.get("server") or req_data.get("target")
            success = await installer_service.install_server(target)
            self.send_json_response(writer, {"success": success, "target": target, "message": f"Instalación de servidor {target} iniciada"})
            return

        if path == "/api/install/package" and method == "POST":
            req_data = json.loads(body_bytes.decode("utf-8") or "{}")
            action = req_data.get("action", "desktop")
            target = req_data.get("target") or req_data.get("desktop") or req_data.get("server")
            if action == "desktop":
                success = await installer_service.install_desktop(target)
            else:
                success = await installer_service.install_server(target)
            self.send_json_response(writer, {"success": success, "target": target, "action": action})
            return

        if path in ["/api/install/cancel", "/api/install/abort"] and method == "POST":
            res = await installer_service.cancel_and_revert()
            self.send_json_response(writer, {"success": True, **res})
            return

        if path == "/api/install/minimal" and method == "POST":
            res = await execute_cli_command(["install", "--minimal"])
            self.send_json_response(writer, res)
            return

        # 7. Endpoint de Versionado y Actualización
        if path == "/api/version" and method in ["GET", "HEAD"]:
            from tdm.version import get_version_info
            self.send_json_response(writer, get_version_info())
            return

        if path in ["/api/update/check", "/api/update"] and method in ["GET", "HEAD"]:
            from tdm.core.updater import check_for_updates
            self.send_json_response(writer, check_for_updates())
            return

        if path == "/api/update" and method == "POST":
            try:
                req_data = json.loads(body_bytes.decode("utf-8") or "{}")
                hub_url = req_data.get("hub")
                from tdm.core.updater import perform_update
                result = await perform_update(hub_url=hub_url)
                self.send_json_response(writer, result)
            except Exception as e:
                self.send_json_response(writer, {"success": False, "error": str(e)}, status_code=400)
            return

        # 8. Archivos Estáticos Web / PWA (HTML, CSS, JS, Iconos, noVNC)
        if method in ["GET", "HEAD"]:
            # Normalizar ruta estática
            rel_path = path.lstrip("/")
            if not rel_path or rel_path == "index.html":
                target_file = WEB_DIR / "index.html"
            else:
                target_file = WEB_DIR / rel_path

            # Comprobar si existe dentro de WEB_DIR y evitar path traversal
            try:
                resolved_file = target_file.resolve()
                resolved_web_dir = WEB_DIR.resolve()
                if resolved_web_dir in resolved_file.parents or resolved_file == resolved_web_dir:
                    if resolved_file.is_dir():
                        if (resolved_file / "index.html").is_file():
                            resolved_file = resolved_file / "index.html"
                        elif (resolved_file / "vnc.html").is_file():
                            resolved_file = resolved_file / "vnc.html"
                    if resolved_file.is_file():
                        ext = resolved_file.suffix.lower()
                        mime_map = {
                            ".html": "text/html; charset=utf-8",
                            ".htm": "text/html; charset=utf-8",
                            ".js": "application/javascript; charset=utf-8",
                            ".mjs": "application/javascript; charset=utf-8",
                            ".css": "text/css; charset=utf-8",
                            ".json": "application/json; charset=utf-8",
                            ".webmanifest": "application/manifest+json",
                            ".svg": "image/svg+xml",
                            ".png": "image/png",
                            ".jpg": "image/jpeg",
                            ".jpeg": "image/jpeg",
                            ".gif": "image/gif",
                            ".ico": "image/x-icon",
                            ".webp": "image/webp",
                            ".woff2": "font/woff2",
                            ".woff": "font/woff",
                            ".ttf": "font/ttf",
                            ".tar.gz": "application/gzip",
                            ".wasm": "application/wasm",
                        }
                        content_type = mime_map.get(ext)
                        if not content_type:
                            guessed, _ = mimetypes.guess_type(str(resolved_file))
                            content_type = guessed or "application/octet-stream"

                        self.send_file_response(writer, resolved_file, content_type=content_type, send_body=(method == "GET"))
                        return
            except Exception:
                pass

        # Fallback 404
        self.send_json_response(writer, {"error": "Ruta no encontrada", "path": path}, status_code=404, send_body=(method != "HEAD"))

    def send_json_response(self, writer: asyncio.StreamWriter, data: Any, status_code: int = 200, send_body: bool = True):
        body = json.dumps(data, indent=2).encode("utf-8")
        headers = [
            f"HTTP/1.1 {status_code} OK",
            "Content-Type: application/json; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Access-Control-Allow-Origin: *",
            "Cache-Control: no-cache, no-store, must-revalidate",
            "Pragma: no-cache",
            "Expires: 0",
            "Connection: close",
            "\r\n"
        ]
        payload = "\r\n".join(headers).encode("utf-8")
        if send_body:
            payload += body
        writer.write(payload)

    def send_text_response(self, writer: asyncio.StreamWriter, text: str, content_type: str = "text/plain", status_code: int = 200, send_body: bool = True):
        body = text.encode("utf-8")
        headers = [
            f"HTTP/1.1 {status_code} OK",
            f"Content-Type: {content_type}; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Access-Control-Allow-Origin: *",
            "Cache-Control: no-cache, no-store, must-revalidate",
            "Connection: close",
            "\r\n"
        ]
        payload = "\r\n".join(headers).encode("utf-8")
        if send_body:
            payload += body
        writer.write(payload)

    def send_file_response(self, writer: asyncio.StreamWriter, file_path: Path, content_type: str = "text/plain", status_code: int = 200, send_body: bool = True):
        try:
            file_size = file_path.stat().st_size
            fname = file_path.name.lower()
            ext = file_path.suffix.lower()

            if fname in ["index.html", "sw.js", "manifest.json"] or ext in [".html", ".htm", ".json"]:
                cache_header = "Cache-Control: no-cache, no-store, must-revalidate, max-age=0"
            else:
                cache_header = "Cache-Control: public, max-age=86400"

            headers = [
                f"HTTP/1.1 {status_code} OK",
                f"Content-Type: {content_type}",
                f"Content-Length: {file_size}",
                "Access-Control-Allow-Origin: *",
                cache_header,
                "Connection: close",
                "\r\n"
            ]
            header_payload = "\r\n".join(headers).encode("utf-8")
            if send_body:
                with open(file_path, "rb") as f:
                    body = f.read()
                writer.write(header_payload + body)
            else:
                writer.write(header_payload)
        except Exception:
            self.send_json_response(writer, {"error": "Error leyendo archivo"}, status_code=500, send_body=send_body)
