import asyncio
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from tdm.config import TDM_DIR, TDM_LOGS_DIR

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if not SCRIPTS_DIR.exists():
    SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"

class InstallerStatus:
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class PackageInstaller:
    """Motor de instalación asíncrono para ejecutar scripts desde el backend y emitir logs al frontend."""
    
    def __init__(self):
        self.status: str = InstallerStatus.IDLE
        self.current_task: Optional[str] = None
        self.logs: List[str] = []
        self.listeners: List[Callable[[str], None]] = []
        self.process: Optional[asyncio.subprocess.Process] = None

    def subscribe(self, callback: Callable[[str], None]):
        """Suscribe un listener (ej. WebSocket) para recibir logs en tiempo real."""
        if callback not in self.listeners:
            self.listeners.append(callback)

    def unsubscribe(self, callback: Callable[[str], None]):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _broadcast_log(self, line: str):
        self.logs.append(line)
        for listener in self.listeners:
            try:
                listener(line)
            except Exception:
                pass

    async def run_script(self, script_name: str, args: List[str] = None) -> bool:
        """Ejecuta un script de instalación ubicado en el backend y transmite los logs."""
        if self.status == InstallerStatus.RUNNING:
            raise RuntimeError("Ya hay una instalación en progreso.")

        script_path = SCRIPTS_DIR / script_name
        if not script_path.exists():
            raise FileNotFoundError(f"Script no encontrado: {script_path}")

        # Intentar permisos de ejecución si es posible
        try:
            os.chmod(script_path, 0o755)
        except Exception:
            pass

        self.status = InstallerStatus.RUNNING
        self.current_task = script_name + (" " + " ".join(args) if args else "")
        self.logs.clear()
        
        self._broadcast_log(f"[*] Iniciando ejecución de {script_name}...")

        bash_bin = shutil.which("bash") or "/data/data/com.termux/files/usr/bin/bash"
        cmd = [bash_bin, str(script_path)] + (args or [])

        prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
        env = {
            **os.environ,
            "PATH": f"{prefix}/bin:" + os.environ.get("PATH", ""),
            "PYTHONPATH": f"{TDM_DIR.parent}:" + os.environ.get("PYTHONPATH", ""),
        }

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env
            )

            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                decoded = line.decode(errors="replace").rstrip()
                self._broadcast_log(decoded)

            await self.process.wait()
            success = (self.process.returncode == 0)
            
            if success:
                self.status = InstallerStatus.COMPLETED
                self._broadcast_log(f"[✓] Tarea {script_name} completada con éxito.")
            else:
                self.status = InstallerStatus.FAILED
                self._broadcast_log(f"[✗] Tarea {script_name} finalizó con error (código {self.process.returncode}).")

            return success

        except Exception as e:
            self.status = InstallerStatus.FAILED
            self._broadcast_log(f"[!] Error ejecutando instalador: {e}")
            return False
        finally:
            self.process = None

    async def install_desktop(self, desktop: str) -> bool:
        return await self.run_script("install_desktop.sh", [desktop])

    async def install_server(self, server: str) -> bool:
        return await self.run_script("install_server.sh", [server])

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "current_task": self.current_task,
            "log_lines_count": len(self.logs),
            "recent_logs": self.logs[-20:] if self.logs else []
        }

# Instancia global del instalador
installer_service = PackageInstaller()
