"""
Agente autónomo de Termux (TDM Agent).
Se ejecuta dentro de Termux y se conecta vía WebSockets al Hub Central (ej. https://tdm.oton.cl)
para recibir y ejecutar órdenes enviadas desde el Navegador / PWA.
"""

import argparse
import asyncio
import json
import os
import shutil
import ssl
import subprocess
import sys
import urllib.parse
from typing import Dict, Any, Optional

from tdm.constants import PORT_TDM_SERVER
from tdm.server.websocket import WebSocketConnection, WebSocketError
from tdm.core.display_manager import display_manager
from tdm.core.installer import installer_service
from tdm.discovery.desktops import discover_desktops
from tdm.discovery.backends import discover_backends
from tdm.discovery.network import get_primary_lan_ip, get_tailscale_ip
from tdm.version import get_version_info
from tdm.logger import log_event

def get_device_model() -> str:
    """Obtiene el nombre comercial del dispositivo Android."""
    try:
        brand = subprocess.run(["getprop", "ro.product.brand"], capture_output=True, text=True, timeout=0.5).stdout.strip()
        model = subprocess.run(["getprop", "ro.product.model"], capture_output=True, text=True, timeout=0.5).stdout.strip()
        if brand and model:
            return f"{brand.capitalize()} {model}"
        elif model:
            return model
    except Exception:
        pass
    return os.uname().nodename if hasattr(os, "uname") else "Dispositivo Android"

class TDMAgent:
    """Cliente agente que conecta Termux con el Hub Web."""

    def __init__(self, hub_url: str, token: str):
        self.hub_url = hub_url.rstrip("/")
        self.token = token
        self.ws: Optional[WebSocketConnection] = None
        self.running = True

    def get_system_info(self) -> Dict[str, Any]:
        """Obtiene información enriquecida sobre el entorno Termux actual."""
        version_info = get_version_info()
        lan_ip = get_primary_lan_ip() or "127.0.0.1"
        ts_ip = get_tailscale_ip()
        model = get_device_model()

        return {
            "version": version_info.get("version", "1.0.0"),
            "model": model,
            "hostname": os.uname().nodename if hasattr(os, "uname") else "termux",
            "is_termux": os.path.exists("/data/data/com.termux"),
            "lan_ip": lan_ip,
            "tailscale_ip": ts_ip,
            "port": PORT_TDM_SERVER,
            "desktops": discover_desktops(),
            "backends": discover_backends(),
            "status": display_manager.get_status()
        }

    async def run(self):
        """Bucle principal de conexión y reconexión con backoff exponencial."""
        print(f"🤖 [TDM Agent] Iniciando agente para Hub: {self.hub_url} | Token: {self.token}")
        
        parsed = urllib.parse.urlparse(self.hub_url)
        is_ssl = parsed.scheme in ["https", "wss"]
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if is_ssl else 80)
        
        if not parsed.port and str(PORT_TDM_SERVER) in self.hub_url:
            port = PORT_TDM_SERVER

        path = f"/ws/agent/{self.token}"

        ssl_ctx = None
        if is_ssl:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

        retry_delay = 2
        while self.running:
            try:
                print(f"🔌 Conectando con {host}:{port}{path}...")
                self.ws = await WebSocketConnection.client_connect(
                    host=host,
                    port=port,
                    path=path,
                    ssl_context=ssl_ctx,
                    extra_headers={"User-Agent": "TDMAgent/1.0", "X-TDM-Token": self.token}
                )
                print("🟢 ¡Conectado al Hub exitosamente!")
                log_event("agent", f"Conectado al Hub {self.hub_url} con token {self.token}")
                retry_delay = 2

                # Enviar info inicial del sistema
                sys_info = self.get_system_info()
                await self.ws.send_json({
                    "type": "agent_ready",
                    "token": self.token,
                    "device_info": sys_info,
                    "info": sys_info
                })

                # Suscribir logs de instalación para enviarlos por WebSocket
                def forward_log(log_line: str):
                    if self.ws and not self.ws.closed:
                        asyncio.create_task(self.ws.send_json({
                            "type": "log",
                            "line": log_line
                        }))
                
                installer_service.subscribe(forward_log)

                # Escuchar comandos
                while not self.ws.closed:
                    msg = await self.ws.recv_json()
                    if msg is None:
                        break
                    asyncio.create_task(self.handle_command(msg))

            except (ConnectionRefusedError, WebSocketError, OSError) as e:
                print(f"⚠️ Error de conexión ({e}). Reintentando en {retry_delay}s...")
                log_event("agent", f"Error de conexión: {e}. Reintentando en {retry_delay}s...", level="WARN")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 30)
            except Exception as e:
                print(f"❌ Error inesperado en agente: {e}")
                log_event("agent", f"Error inesperado: {e}", level="ERROR")
                await asyncio.sleep(5)

    async def handle_command(self, msg: Dict[str, Any]):
        """Procesa y ejecuta comandos recibidos desde la Web / PWA."""
        cmd_type = msg.get("type")
        req_id = msg.get("req_id")
        data = msg.get("data", {})

        print(f"📥 [Comando recibido] Tipo: {cmd_type} (req_id: {req_id})")
        log_event("agent", f"Comando recibido: {cmd_type} (req_id: {req_id})")

        try:
            if cmd_type == "ping":
                await self.ws.send_json({"type": "pong", "req_id": req_id})

            elif cmd_type == "get_status":
                status = display_manager.get_status()
                await self.ws.send_json({
                    "type": "response",
                    "req_id": req_id,
                    "result": status
                })

            elif cmd_type == "screen_start":
                session_dict = await display_manager.start_screen(
                    backend=data.get("backend", "termux-x11"),
                    mode=data.get("mode", "desktop"),
                    desktop_id=data.get("desktop"),
                    resolution=data.get("resolution", "1080x2400"),
                    dpi=data.get("dpi", 140),
                    audio=data.get("audio", True),
                    virgl=data.get("virgl", True)
                )
                await self.ws.send_json({
                    "type": "response",
                    "req_id": req_id,
                    "result": session_dict
                })

            elif cmd_type == "screen_stop":
                stopped = await display_manager.stop_screen()
                await self.ws.send_json({
                    "type": "response",
                    "req_id": req_id,
                    "result": {"stopped": stopped}
                })

            elif cmd_type == "install_desktop":
                desktop = data.get("desktop") or data.get("target")
                success = await installer_service.install_desktop(desktop)
                await self.ws.send_json({
                    "type": "response",
                    "req_id": req_id,
                    "result": {"success": success, "target": desktop, "desktop": desktop}
                })

            elif cmd_type == "install_server":
                server = data.get("server") or data.get("target")
                success = await installer_service.install_server(server)
                await self.ws.send_json({
                    "type": "response",
                    "req_id": req_id,
                    "result": {"success": success, "target": server, "server": server}
                })

            elif cmd_type == "install_package":
                action = data.get("action")
                target = data.get("target")
                if action == "desktop":
                    success = await installer_service.install_desktop(target)
                else:
                    success = await installer_service.install_server(target)
                
                await self.ws.send_json({
                    "type": "response",
                    "req_id": req_id,
                    "result": {"success": success, "target": target}
                })

            elif cmd_type == "check_update":
                from tdm.core.updater import check_for_updates
                hub_url = data.get("hub") or self.hub_url
                upd_info = check_for_updates(hub_url)
                await self.ws.send_json({
                    "type": "response",
                    "req_id": req_id,
                    "result": upd_info
                })

            elif cmd_type == "update":
                from tdm.core.updater import perform_update
                hub_url = data.get("hub") or self.hub_url
                res = await perform_update(hub_url)
                await self.ws.send_json({
                    "type": "response",
                    "req_id": req_id,
                    "result": res
                })

            elif cmd_type == "exec":
                command = data.get("command")
                if not command:
                    return
                
                print(f"⚡ Ejecutando comando remoto: {command}")
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )

                async def stream_output():
                    while True:
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        decoded = line.decode("utf-8", errors="ignore").rstrip()
                        if self.ws and not self.ws.closed:
                            await self.ws.send_json({
                                "type": "exec_log",
                                "req_id": req_id,
                                "data": decoded
                            })
                    await proc.wait()
                    if self.ws and not self.ws.closed:
                        await self.ws.send_json({
                            "type": "exec_done",
                            "req_id": req_id,
                            "returncode": proc.returncode
                        })

                asyncio.create_task(stream_output())

            elif cmd_type in ["uninstall", "delete_device"]:
                print("🗑️ [TDM Agent] Solicitud de desinstalación remota recibida.")
                log_event("agent", "Solicitud de desinstalación remota recibida. Limpiando y finalizando...")
                if self.ws and not self.ws.closed:
                    await self.ws.send_json({
                        "type": "response",
                        "req_id": req_id,
                        "result": {"uninstalled": True}
                    })
                    await self.ws.close()
                self.running = False
                asyncio.create_task(self._perform_self_uninstall())

        except Exception as e:
            print(f"❌ Error procesando comando {cmd_type}: {e}")
            if self.ws and not self.ws.closed:
                await self.ws.send_json({
                    "type": "error",
                    "req_id": req_id,
                    "error": str(e)
                })

    async def _perform_self_uninstall(self):
        """Detiene todo el entorno gráfico, desactiva wake-lock y elimina los directorios de TDM."""
        await asyncio.sleep(0.5)
        try:
            # 1. Detener pantalla y procesos gráficos
            await display_manager.stop_screen()
            
            # 2. Desactivar Wake-Lock
            prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
            home = os.environ.get("HOME", "/data/data/com.termux/files/home")
            wake_unlock = shutil.which("termux-wake-unlock") or f"{prefix}/bin/termux-wake-unlock"
            if os.path.exists(wake_unlock):
                subprocess.run([wake_unlock], capture_output=True)

            # 3. Eliminar binario tdm y módulos
            tdm_bin = Path(f"{prefix}/bin/tdm")
            if tdm_bin.exists():
                try: tdm_bin.unlink()
                except Exception: pass

            for pth in Path(f"{prefix}/lib").glob("python*/site-packages/tdm.pth"):
                try: pth.unlink()
                except Exception: pass

            # 4. Eliminar directorios ~/.tdm y ~/termux-display-manager
            shutil.rmtree(f"{home}/.tdm", ignore_errors=True)
            shutil.rmtree(f"{home}/termux-display-manager", ignore_errors=True)

            # 5. Terminar procesos
            subprocess.run(["pkill", "-9", "-f", "tdm.cli.main"], capture_output=True)
            subprocess.run(["pkill", "-9", "-f", "tdm.agent.client"], capture_output=True)
        except Exception as e:
            print(f"Error durante auto-desinstalación: {e}")

def save_agent_config(hub_url: str, token: str):
    try:
        cfg_dir = Path.home() / ".tdm" / "config"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        cfg_file = cfg_dir / "agent.json"
        cfg_file.write_text(json.dumps({"hub": hub_url, "token": token}, indent=2), encoding="utf-8")
    except Exception:
        pass

def load_agent_config() -> Dict[str, str]:
    try:
        cfg_file = Path.home() / ".tdm" / "config" / "agent.json"
        if cfg_file.exists():
            return json.loads(cfg_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def acquire_wake_lock():
    try:
        wake_lock_bin = shutil.which("termux-wake-lock") or "/data/data/com.termux/files/usr/bin/termux-wake-lock"
        if os.path.exists(wake_lock_bin) or shutil.which("termux-wake-lock"):
            subprocess.run([wake_lock_bin], capture_output=True, timeout=1)
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description="Cliente Agente de TDM para Termux")
    parser.add_argument("--hub", type=str, default=None, help="URL del Hub Central")
    parser.add_argument("--token", type=str, default=None, help="Token único de emparejamiento")

    args = parser.parse_args()
    saved = load_agent_config()

    hub_url = args.hub or saved.get("hub") or "https://tdm.oton.cl"
    token = args.token or saved.get("token")

    if not token:
        print("❌ Error: Se requiere un token (--token o configurado previamente en ~/.tdm/config/agent.json)")
        sys.exit(1)

    save_agent_config(hub_url, token)
    acquire_wake_lock()

    agent = TDMAgent(hub_url=hub_url, token=token)

    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("\n👋 Agente detenido por el usuario.")

if __name__ == "__main__":
    from pathlib import Path
    main()
