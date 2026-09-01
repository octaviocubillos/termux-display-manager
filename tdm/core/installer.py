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

        self.active_target: Optional[str] = None

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

        working_dir = str(Path.home()) if Path.home().exists() else "/data/data/com.termux/files/home"

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=working_dir,
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

    async def cancel_and_revert(self) -> Dict[str, Any]:
        """Cancela el proceso activo de instalación, mata procesos bloqueados y purga paquetes parciales."""
        self._broadcast_log("\n⚠️ [TDM] Cancelación solicitada por el usuario.")
        self._broadcast_log("[*] Deteniendo subprocesos de instalación...")
        
        # 1. Matar el proceso principal y subprocesos hijos
        if self.process:
            try:
                self.process.terminate()
                await asyncio.sleep(0.5)
                if self.process.returncode is None:
                    self.process.kill()
            except Exception:
                pass
            self.process = None

        # 2. Matar cualquier proceso apt/dpkg/pkg bloqueado y configurar dpkg
        prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
        try:
            import subprocess
            subprocess.run("pkill -9 -f 'apt-get|dpkg|pkg' 2>/dev/null || true", shell=True)
            subprocess.run("dpkg --configure -a 2>/dev/null || true", shell=True)
        except Exception:
            pass

        # 3. Si se estaba instalando un entorno específico, revertir y purgarlo
        target = self.active_target
        if target:
            self._broadcast_log(f"[*] Revirtiendo instalación y limpiando paquetes de {target}...")
            uninstall_script = SCRIPTS_DIR / "uninstall_desktop.sh"
            if uninstall_script.exists():
                try:
                    bash_bin = shutil.which("bash") or f"{prefix}/bin/bash"
                    proc = await asyncio.create_subprocess_exec(
                        bash_bin, str(uninstall_script), target,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT
                    )
                    while True:
                        line = await proc.stdout.readline()
                        if not line:
                            break
                        self._broadcast_log(line.decode(errors="replace").rstrip())
                    await proc.wait()
                except Exception as e:
                    self._broadcast_log(f"[!] Error revirtiendo: {e}")

        self.status = InstallerStatus.IDLE
        self.current_task = None
        self.active_target = None
        self._broadcast_log("[✓] Instalación cancelada y estado revertido al 100%.\n")
        return {"cancelled": True, "reverted": True}

    async def install_desktop(self, desktop: str) -> bool:
        # Antes de cambiar de entorno, apagar todas las pantallas y procesos gráficos manteniendo TDM activo
        try:
            from tdm.core.display_manager import display_manager
            self._broadcast_log("[*] Deteniendo sesiones y procesos gráficos activos antes del cambio de entorno...")
            await display_manager.stop_screen()
        except Exception as e:
            self._broadcast_log(f"[*] Limpiando procesos de pantalla: {e}")
        self.active_target = desktop
        return await self.run_script("install_desktop.sh", [desktop])

    async def uninstall_desktop(self, desktop: Optional[str] = None) -> bool:
        try:
            from tdm.core.display_manager import display_manager
            self._broadcast_log("[*] Deteniendo sesiones y procesos gráficos activos antes de la desinstalación...")
            await display_manager.stop_screen()
        except Exception as e:
            self._broadcast_log(f"[*] Limpiando procesos de pantalla: {e}")
        target = desktop if desktop else "all"
        self.active_target = target
        return await self.run_script("uninstall_desktop.sh", [target])

    async def install_server(self, server: str) -> bool:
        self.active_target = server
        return await self.run_script("install_server.sh", [server])

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "current_task": self.current_task,
            "active_target": self.active_target,
            "log_lines_count": len(self.logs),
            "recent_logs": self.logs[-20:] if self.logs else []
        }

# Instancia global del instalador
installer_service = PackageInstaller()
