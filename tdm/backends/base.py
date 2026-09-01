import asyncio
import os
import shutil
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from tdm.core.models import DisplayConfig, DisplaySession, DisplayStatus

class BaseDisplayBackend(ABC):
    """Clase base abstracta para los servidores de pantalla (Termux:X11, VNC, noVNC, RDP)."""
    
    def __init__(self, config: DisplayConfig):
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self.bridge_process: Optional[asyncio.subprocess.Process] = None

    @abstractmethod
    def build_server_command(self) -> Tuple[list, Dict[str, str]]:
        """Devuelve el comando y variables de entorno para iniciar el servidor de pantalla."""
        pass

    def build_bridge_command(self) -> Optional[list]:
        """Comando opcional para proxy/puente adicional (ej. websockify)."""
        return None

    @abstractmethod
    def cleanup(self, session: Optional[DisplaySession] = None) -> None:
        """Limpia sockets, archivos lock o procesos temporales al detener el display."""
        pass

    @abstractmethod
    def get_connection_info(self, host: str = "127.0.0.1") -> Dict[str, str]:
        """Devuelve URLs e instrucciones de conexión para el cliente."""
        pass

    def get_connection_urls(self, host: str = "127.0.0.1") -> Dict[str, str]:
        return self.get_connection_info(host)

    async def start(self) -> bool:
        """Inicia el proceso del backend gráfico y su puente si corresponde."""
        cmd, env = self.build_server_command()
        self.cleanup(None)

        if not cmd or not cmd[0]:
            print("[!] Comando de servidor gráfico vacío.")
            return False

        server_bin = shutil.which(cmd[0]) or cmd[0]
        if not os.path.exists(server_bin) and not shutil.which(cmd[0]):
            if "termux-x11" in str(cmd[0]) and shutil.which("pkg"):
                print("[*] Servidor termux-x11 no detectado. Instalando automáticamente 'termux-x11-nightly'...")
                import subprocess
                subprocess.run(["pkg", "install", "-y", "x11-repo"], capture_output=True)
                subprocess.run(["pkg", "install", "-y", "termux-x11-nightly"], capture_output=True)
                server_bin = shutil.which("termux-x11") or f"{PREFIX}/bin/termux-x11"
            elif "Xvnc" in str(cmd[0]) and shutil.which("pkg"):
                print("[*] Servidor VNC no detectado. Instalando automáticamente 'tigervnc'...")
                import subprocess
                subprocess.run(["pkg", "install", "-y", "tigervnc"], capture_output=True)
                server_bin = shutil.which("Xvnc") or f"{PREFIX}/bin/Xvnc"

        if not os.path.exists(server_bin) and not shutil.which(cmd[0]):
            print(f"[!] Servidor gráfico '{cmd[0]}' no está instalado en el sistema.")
            if "termux-x11" in str(cmd[0]):
                print("💡 Para instalarlo en Termux ejecuta: pkg install -y x11-repo termux-x11-nightly")
                print("💡 O inicia en modo navegador web con: tdm start -b novnc")
            elif "Xvnc" in str(cmd[0]):
                print("💡 Para instalarlo en Termux ejecuta: pkg install -y tigervnc")
            return False

        merged_env = {**os.environ, **env}

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                env=merged_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
        except Exception as e:
            print(f"[!] Error iniciando servidor gráfico: {e}")
            return False

        # Verificar si el proceso murió inmediatamente tras iniciar
        await asyncio.sleep(0.4)
        if self.process.returncode is not None:
            output = ""
            try:
                out_bytes = await asyncio.wait_for(self.process.stdout.read(2048), timeout=0.2)
                output = out_bytes.decode(errors="replace").strip()
            except Exception:
                pass
            print(f"[!] Servidor gráfico {cmd[0]} finalizó inesperadamente (código {self.process.returncode}): {output}")
            return False

        bridge_cmd = self.build_bridge_command()
        if bridge_cmd:
            await asyncio.sleep(0.3)
            try:
                self.bridge_process = await asyncio.create_subprocess_exec(
                    *bridge_cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
            except Exception as e:
                print(f"[!] Error iniciando puente/proxy: {e}")

        return True

    async def stop(self) -> bool:
        """Detiene los procesos del servidor y proxy."""
        if self.bridge_process:
            try:
                self.bridge_process.terminate()
                await self.bridge_process.wait()
            except Exception:
                pass
            self.bridge_process = None

        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception:
                pass
            self.process = None

        self.cleanup(None)
        return True
