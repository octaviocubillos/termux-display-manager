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

        merged_env = {**os.environ, **env}

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                env=merged_env,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
        except Exception as e:
            print(f"[!] Error iniciando servidor gráfico: {e}")
            return False

        bridge_cmd = self.build_bridge_command()
        if bridge_cmd:
            await asyncio.sleep(0.5)
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
