import asyncio
import os
import signal
import time
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from tdm.core.models import DisplayConfig, DisplaySession, DisplayStatus
from tdm.discovery.desktops import discover_desktops
from tdm.discovery.backends import discover_backends
from tdm.discovery.network import discover_network_interfaces
from tdm.backends import create_backend, BaseDisplayBackend
from tdm.runners.session_builder import build_session_script
from tdm.config import TDM_LOGS_DIR
from tdm.logger import log_event
from tdm.constants import (
    DEFAULT_DISPLAY_NUM,
    DEFAULT_RESOLUTION,
    DEFAULT_DPI,
    BACKEND_TERMUX_X11,
    SESSION_MODE_DESKTOP,
    SESSION_MODE_TERMINAL,
)

class DisplayManager:
    """Gestor principal de pantallas de TDM (Controlador de Sesión Única Nativa :0)."""

def get_memory_info() -> Dict[str, Any]:
    """Obtiene la telemetría de memoria RAM del sistema en tiempo real (/proc/meminfo)."""
    try:
        with open("/proc/meminfo", "r") as f:
            mem = {}
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    k = parts[0].strip()
                    v_str = parts[1].strip().split()[0]
                    if v_str.isdigit():
                        mem[k] = int(v_str)
            total_kb = mem.get("MemTotal", 0)
            available_kb = mem.get("MemAvailable", mem.get("MemFree", 0))
            used_kb = max(0, total_kb - available_kb)
            pct = round((used_kb / total_kb) * 100, 1) if total_kb > 0 else 0
            return {
                "total_mb": total_kb // 1024,
                "used_mb": used_kb // 1024,
                "available_mb": available_kb // 1024,
                "percent": pct,
                "formatted": f"{used_kb // 1024} MB / {total_kb // 1024} MB ({pct}%)"
            }
    except Exception:
        return {"total_mb": 0, "used_mb": 0, "available_mb": 0, "percent": 0, "formatted": "N/A"}

class DisplayManager:
    """Orquestador principal de pantalla y ciclo de vida de escritorios."""

    def __init__(self):
        self.active_session: Optional[DisplaySession] = None
        self.active_backend_obj: Optional[BaseDisplayBackend] = None

    def get_installed_desktop(self) -> Dict[str, Any]:
        """Detecta y devuelve el entorno de escritorio nativo instalado en el sistema."""
        desktops = discover_desktops()
        # Buscar el primer escritorio completo instalado
        for d in desktops:
            if d.get("installed") and d.get("id") != "terminal":
                return d
                
        # Fallback a modo terminal si no hay DE completo
        return {
            "id": "terminal",
            "name": "Modo Terminal X11",
            "installed": True,
            "executable": "xterm"
        }

    def get_status(self) -> Dict[str, Any]:
        """Devuelve el estado completo del sistema, memoria RAM, escritorio instalado, pantalla activa y red."""
        installed_de = self.get_installed_desktop()
        backends = discover_backends()
        network = discover_network_interfaces()
        from tdm.core.telemetry import (
            get_device_info,
            get_cpu_telemetry,
            get_memory_telemetry,
            get_storage_telemetry
        )
        dev_info = get_device_info()
        cpu_info = get_cpu_telemetry()
        mem_info = get_memory_telemetry()
        storage_info = get_storage_telemetry()
        
        session_dict = None
        if self.active_session and self.active_session.status == DisplayStatus.RUNNING:
            session_dict = self.active_session.to_dict()

        from tdm.version import get_version_info
        ver_info = get_version_info()

        return {
            "installed_desktop": installed_de,
            "available_backends": backends,
            "network": network,
            "device": dev_info,
            "cpu": cpu_info,
            "memory": mem_info,
            "storage": storage_info,
            "version": ver_info,
            "is_screen_active": bool(self.active_session and self.active_session.status == DisplayStatus.RUNNING),
            "active_screen": session_dict
        }

    async def start_screen(
        self,
        backend: str = BACKEND_TERMUX_X11,
        mode: str = SESSION_MODE_DESKTOP,
        desktop_id: Optional[str] = None,
        resolution: str = DEFAULT_RESOLUTION,
        dpi: int = DEFAULT_DPI,
        audio: bool = True,
        virgl: bool = True,
        backend_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Inicia o conmuta la salida de pantalla para el escritorio nativo."""
        backend = backend_id or backend

        # 1. Si hay una pantalla activa, detenerla primero limpiamente
        if self.active_session and self.active_session.status == DisplayStatus.RUNNING:
            await self.stop_screen()

        if not desktop_id:
            installed_de = self.get_installed_desktop()
            desktop_id = installed_de["id"] if mode == SESSION_MODE_DESKTOP else "terminal"

        config = DisplayConfig(
            display_num=DEFAULT_DISPLAY_NUM,
            desktop_id=desktop_id,
            backend=backend,
            resolution=resolution,
            dpi=dpi,
            audio=audio,
            virgl=virgl
        )

        session = DisplaySession(
            id=f"screen-{DEFAULT_DISPLAY_NUM}",
            config=config,
            status=DisplayStatus.STARTING,
            started_at=time.time(),
            log_file=str(TDM_LOGS_DIR / f"screen-{DEFAULT_DISPLAY_NUM}.log")
        )

        log_event("display", f"Iniciando pantalla en backend '{backend}' con entorno '{desktop_id}' ({resolution})")
        # 2. Instanciar el backend correspondiente mediante Factory
        backend_obj = create_backend(config)
        self.active_backend_obj = backend_obj

        # 3. Iniciar el servidor gráfico del backend
        success = await backend_obj.start()
        if not success:
            session.status = DisplayStatus.FAILED
            session.error_message = f"Fallo al iniciar el servidor {backend}"
            log_event("display", f"ERROR: Fallo al iniciar servidor {backend}", level="ERROR")
            return session.to_dict()

        # 4. Construir y lanzar la sesión de escritorio (ej. openbox o xfce4) sobre el Display
        session_script = build_session_script(config.display_num, config.desktop_id, config.custom_command)
        session_proc = await self._launch_desktop_session(session_script, session.log_file)

        session.server_pid = backend_obj.process.pid if backend_obj.process else os.getpid()
        session.session_pid = session_proc.pid if session_proc else None
        session.status = DisplayStatus.RUNNING
        session.urls = backend_obj.get_connection_urls()

        self.active_session = session
        log_event("display", f"Pantalla activa en Display :{config.display_num} (PID Servidor: {session.server_pid}, PID Sesión: {session.session_pid})")
        return session.to_dict()

    async def stop_screen(self) -> bool:
        """Detiene completamente cualquier servidor gráfico, entorno de escritorio y cierra la app UI."""
        log_event("display", "Iniciando proceso de detención completa de pantalla y entorno gráfico...")
        # 1. Matar procesos del backend activo
        if self.active_backend_obj:
            try:
                await self.active_backend_obj.stop()
            except Exception:
                pass
            self.active_backend_obj = None

        # 2. Matar procesos del grupo de la sesión si existe
        if self.active_session and self.active_session.session_pid:
            try:
                pgid = os.getpgid(self.active_session.session_pid)
                os.killpg(pgid, signal.SIGKILL)
            except Exception:
                pass

        # 3. Matar forzosamente todos los procesos de entornos de escritorio, servidores y apps gráficas
        target_names = {
            "termux-x11", "Xvnc", "vncserver", "xrdp", "xrdp-sesman", "websockify",
            "xfce4-session", "xfce4-panel", "xfce4-power-manager", "xfce4-notifyd",
            "xfwm4", "xfdesktop", "thunar", "wrapper-2.0", "xfconfd", "xfsettingsd",
            "startplasma-x11", "plasmashell", "kwin_x11", "plasma-session", "kded5", "klauncher", "ksmserver", "kaccess",
            "mate-session", "mate-panel", "marco", "caja", "mate-settings-daemon",
            "startlxqt", "lxqt-session", "pcmanfm-qt", "lxqt-panel", "lxqt-globalkeysd", "lxqt-notificationd",
            "openbox", "openbox-session", "tint2", "i3", "i3bar", "i3status",
            "xterm", "qterminal", "mate-terminal", "xfce4-terminal",
            "pulseaudio", "virgl_test_server"
        }

        current_pid = os.getpid()
        try:
            entries = os.listdir("/proc")
        except Exception:
            entries = []

        for entry in entries:
            if not entry.isdigit():
                continue
            pid = int(entry)
            if pid == current_pid or pid == 1:
                continue
            try:
                comm = ""
                cmdline = ""
                environ_str = ""
                
                comm_file = f"/proc/{pid}/comm"
                cmd_file = f"/proc/{pid}/cmdline"
                env_file = f"/proc/{pid}/environ"

                if os.path.exists(comm_file):
                    with open(comm_file, "r", errors="ignore") as f:
                        comm = f.read().strip()
                if os.path.exists(cmd_file):
                    with open(cmd_file, "rb") as f:
                        cmdline = f.read().decode("utf-8", errors="ignore").replace("\x00", " ")
                if os.path.exists(env_file):
                    with open(env_file, "rb") as f:
                        environ_str = f.read().decode("utf-8", errors="ignore")

                # No matar el agente de TDM, ni el servidor CLI ni procesos del sistema
                if any(safe in cmdline for safe in ["tdm.cli.main", "tdm.agent.client", "tdm hub", "tdm server"]):
                    continue

                should_kill = False

                # A. Si el proceso tiene DISPLAY=:0 o DISPLAY=: en sus variables de entorno
                if "DISPLAY=:" in environ_str:
                    should_kill = True

                # B. Si el binario o comando coincide con un entorno de escritorio o servidor gráfico
                elif comm in target_names or comm.startswith("xfce4-") or comm.startswith("mate-") or comm.startswith("lxqt-") or comm.startswith("plasma-"):
                    should_kill = True

                # C. Si es un script de inicio de sesión
                elif any(runner in cmdline for runner in ["session-display", "startxfce4", "startplasma", "startlxqt", "launch_x11"]):
                    should_kill = True

                if should_kill:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except Exception:
                        pass
            except Exception:
                pass

        # 4. Barrido de respaldo con pkill por patrones
        patterns = [
            "xfce4", "xfwm4", "xfdesktop", "thunar", "wrapper-2.0", "xfsettingsd",
            "plasmashell", "startplasma", "kwin_x11", "mate-session", "startlxqt",
            "openbox", "i3", "termux-x11", "Xvnc", "virgl_test_server"
        ]
        for pat in patterns:
            try:
                subprocess.run(["pkill", "-9", "-f", pat], capture_output=True)
            except Exception:
                pass

        # 5. Enviar señal / comando para cerrar la app Android Termux:X11
        for cmd in [
            ["am", "broadcast", "-a", "com.termux.x11.ACTION_STOP"],
            ["am", "force-stop", "com.termux.x11"],
            ["termux-am", "broadcast", "-a", "com.termux.x11.ACTION_STOP"]
        ]:
            try:
                subprocess.run(cmd, capture_output=True, timeout=1)
            except Exception:
                pass

        # 6. Limpiar sockets y archivos temporales de X11 en todas las rutas posibles
        self._cleanup_x11_sockets(DEFAULT_DISPLAY_NUM)

        if self.active_session:
            self.active_session.status = DisplayStatus.STOPPED
            self.active_session = None

        log_event("display", "Pantalla y entorno gráfico detenidos y liberados con éxito.")
        return True

    async def _launch_desktop_session(self, script_path: Path, log_file: str) -> Optional[asyncio.subprocess.Process]:
        """Ejecuta el script runner en segundo plano para inicializar D-Bus y el gestor de ventanas."""
        try:
            with open(log_file, "a") as f_out:
                bash_bin = shutil.which("bash") or "/data/data/com.termux/files/usr/bin/bash" or "sh"
                proc = await asyncio.create_subprocess_exec(
                    bash_bin, str(script_path),
                    stdout=f_out,
                    stderr=asyncio.subprocess.STDOUT,
                    preexec_fn=os.setsid if hasattr(os, "setsid") else None
                )
                # Breve pausa para asegurar arranque del WM
                await asyncio.sleep(0.3)
                return proc
        except Exception as e:
            print(f"Error lanzando sesión de escritorio: {e}")
            return None

    def _cleanup_x11_sockets(self, display_num: int):
        """Elimina archivos socket huérfanos /tmp/.X11-unix/X0 y lockfiles en /tmp y $PREFIX/tmp."""
        prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
        candidate_paths = [
            f"/tmp/.X{display_num}-lock",
            f"/tmp/.X11-unix/X{display_num}",
            f"/tmp/X11-pipe/X{display_num}",
            f"{prefix}/tmp/.X{display_num}-lock",
            f"{prefix}/tmp/.X11-unix/X{display_num}",
            f"{prefix}/tmp/X11-pipe/X{display_num}"
        ]
        for p in candidate_paths:
            try:
                path_obj = Path(p)
                if path_obj.exists():
                    path_obj.unlink(missing_ok=True)
            except Exception:
                pass

# Instancia Singleton global
display_manager = DisplayManager()
