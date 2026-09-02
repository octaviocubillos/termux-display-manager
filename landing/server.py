#!/usr/bin/env python3
"""
Servidor Web para Landing Page de TDM con Reverse Proxy HTTP/WebSocket en /aabbcc.
Sirve archivos estáticos (install, go, changelog, etc.) y reenvía /aabbcc al runtime TDM.
"""

import asyncio
import os
import sys
import argparse
import mimetypes
import urllib.parse
from pathlib import Path

LANDING_DIR = Path(__file__).resolve().parent

class LandingProxyServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080, target_host: str = "192.168.1.197", target_port: int = 19050):
        self.host = host
        self.port = port
        self.target_host = target_host
        self.target_port = target_port

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

            # 1. ¿Es Reverse Proxy a TDM (/aabbcc o /aabbcc/*)?
            if path == "/aabbcc":
                target = "/aabbcc/" + (f"?{query}" if query else "")
                self.send_redirect(writer, target)
                return

            if path.startswith("/aabbcc/"):
                is_ws = headers.get("upgrade", "").lower() == "websocket"
                if is_ws:
                    await self.proxy_websocket(path, query, headers, reader, writer)
                else:
                    body_bytes = b""
                    if content_length > 0:
                        body_bytes = await reader.readexactly(content_length)
                    await self.proxy_http(method, path, query, headers, body_bytes, writer)
                return

            # 2. Servir Archivos Estáticos de la Landing Page
            await self.serve_static(method, path, writer)

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

    async def proxy_http(self, method: str, path: str, query: str, headers: dict, body_bytes: bytes, writer: asyncio.StreamWriter):
        """Reenvío de peticiones HTTP a la aplicación Web de TDM."""
        if path.startswith("/aabbcc/"):
            target_path = path[7:]
        elif path == "/aabbcc":
            target_path = "/"
        else:
            target_path = path

        if query:
            target_path = f"{target_path}?{query}"

        try:
            up_reader, up_writer = await asyncio.open_connection(self.target_host, self.target_port)
            
            req_lines = [f"{method} {target_path} HTTP/1.1"]
            for k, v in headers.items():
                if k.lower() in ("host", "connection", "accept-encoding"):
                    continue
                req_lines.append(f"{k}: {v}")
            req_lines.append(f"Host: {self.target_host}:{self.target_port}")
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
                json_msg = f'{{"error":"bad_gateway","message":"No se pudo conectar al runtime TDM en http://{self.target_host}:{self.target_port}","detail":"{str(e)}"}}'.encode("utf-8")
                self.send_response(writer, 502, "application/json", json_msg)
            else:
                msg = (
                    f"<html><body style='background:#0f172a;color:#f8fafc;font-family:sans-serif;padding:2rem;text-align:center;'>"
                    f"<h2>⚠️ TDM HTTP-Proxy Gateway (/aabbcc)</h2>"
                    f"<p>No se pudo conectar al runtime TDM en <code>http://{self.target_host}:{self.target_port}</code></p>"
                    f"<p style='color:#94a3b8;font-size:0.85rem;'>Asegúrate de que TDM esté activo en el dispositivo y accesible desde este servidor.</p>"
                    f"<p style='color:#ef4444;font-size:0.8rem;'>Detalle: {e}</p>"
                    f"</body></html>"
                ).encode("utf-8")
                self.send_response(writer, 502, "text/html; charset=utf-8", msg)

    async def proxy_websocket(self, path: str, query: str, headers: dict, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Reenvío bidireccional de WebSockets (noVNC websockify / Terminal PTY)."""
        if path.startswith("/aabbcc/"):
            target_path = path[7:]
        elif path == "/aabbcc":
            target_path = "/"
        else:
            target_path = path

        if query:
            target_path = f"{target_path}?{query}"

        try:
            up_reader, up_writer = await asyncio.open_connection(self.target_host, self.target_port)

            req_lines = [f"GET {target_path} HTTP/1.1"]
            for k, v in headers.items():
                if k.lower() == "host":
                    req_lines.append(f"Host: {self.target_host}:{self.target_port}")
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

    async def serve_static(self, method: str, path: str, writer: asyncio.StreamWriter):
        rel = path.lstrip("/")
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
        status_text = {200: "OK", 403: "Forbidden", 404: "Not Found", 500: "Internal Server Error", 502: "Bad Gateway"}.get(status, "OK")
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

    def send_redirect(self, writer: asyncio.StreamWriter, location: str):
        resp = [
            "HTTP/1.1 301 Moved Permanently",
            f"Location: {location}",
            "Content-Length: 0",
            "Access-Control-Allow-Origin: *",
            "Connection: close",
            "",
            ""
        ]
        writer.write("\r\n".join(resp).encode("utf-8"))

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"🌐 [Landing Page + HTTP-Proxy] Servidor iniciado en http://{self.host}:{self.port}")
        print(f"🔀 [HTTP Reverse Proxy] Ruta /aabbcc -> http://{self.target_host}:{self.target_port}")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TDM Landing Page + Reverse Proxy Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Puerto del servidor (default: 8080)")
    parser.add_argument("--target-host", default=os.environ.get("TDM_TARGET_HOST", "192.168.1.197"), help="Host destino de TDM")
    parser.add_argument("--target-port", type=int, default=int(os.environ.get("TDM_TARGET_PORT", "19050")), help="Puerto destino de TDM (default: 19050)")
    args = parser.parse_args()

    try:
        asyncio.run(LandingProxyServer(args.host, args.port, args.target_host, args.target_port).start())
    except KeyboardInterrupt:
        print("\nServidor detenido.")
