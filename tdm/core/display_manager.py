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
                
        # Si no hay ningún entorno instalado
        return {
            "id": None,
            "name": "Ninguno",
            "installed": False,
            "executable": None
        }

    def detect_running_graphical_session(self) -> Optional[Dict[str, Any]]:
        """
        Escanea el sistema para detectar si hay servidores gráficos o entornos de escritorio activos,
        incluso si se iniciaron de forma externa o antes de reiniciar el servicio TDM.
        """
        current_pid = os.getpid()
        graphical_procs = []
        detected_backend = None
        detected_desktop = None
        detected_desktop_name = None
        detected_display = ":0"

        backend_signatures = {
            "termux-x11": "termux-x11",
            "Xvnc": "vnc",
            "vncserver": "vnc",
            "tigervnc": "vnc",
            "xrdp": "rdp",
            "websockify": "novnc"
        }

        desktop_signatures = {
            "xfce4-session": ("xfce4", "XFCE4"),
            "xfwm4": ("xfce4", "XFCE4"),
            "startxfce4": ("xfce4", "XFCE4"),
            "plasmashell": ("kde", "KDE Plasma"),
            "startplasma-x11": ("kde", "KDE Plasma"),
            "kwin_x11": ("kde", "KDE Plasma"),
            "kwin": ("kde", "KDE Plasma"),
            "mate-session": ("mate", "MATE Desktop"),
            "startlxqt": ("lxqt", "LXQt"),
            "lxqt-session": ("lxqt", "LXQt"),
            "i3": ("i3", "i3 WM"),
            "openbox": ("openbox", "Openbox"),
            "openbox-session": ("openbox", "Openbox"),
        }

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
                comm_file = f"/proc/{pid}/comm"
                cmd_file = f"/proc/{pid}/cmdline"
                env_file = f"/proc/{pid}/environ"

                comm = ""
                cmdline = ""
                environ_str = ""

                if os.path.exists(comm_file):
                    with open(comm_file, "r", errors="ignore") as f:
                        comm = f.read().strip()
                if os.path.exists(cmd_file):
                    with open(cmd_file, "rb") as f:
                        cmdline = f.read().decode("utf-8", errors="ignore").replace("\x00", " ")
                if os.path.exists(env_file):
                    with open(env_file, "rb") as f:
                        environ_str = f.read().decode("utf-8", errors="ignore")

                # Ignorar servidor TDM
                if any(safe in cmdline for safe in ["tdm.cli.main", "tdm.agent.client", "tdm.server.service"]):
                    continue

                is_graphical = False

                for b_proc, b_type in backend_signatures.items():
                    if b_proc == comm or b_proc in cmdline:
                        is_graphical = True
                        if not detected_backend:
                            detected_backend = b_type

                for d_proc, (d_id, d_name) in desktop_signatures.items():
                    if d_proc == comm or d_proc in cmdline:
                        is_graphical = True
                        if not detected_desktop:
                            detected_desktop = d_id
                            detected_desktop_name = d_name

                if "DISPLAY=:" in environ_str:
                    is_graphical = True
                    for chunk in environ_str.split("\x00"):
                        if chunk.startswith("DISPLAY="):
                            detected_display = chunk.split("=")[1]
                            break

                if is_graphical:
                    graphical_procs.append({
                        "pid": pid,
                        "comm": comm,
                        "cmd": cmdline[:60]
                    })
            except Exception:
                continue

        prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
        for disp in range(3):
            sock1 = f"/tmp/.X11-unix/X{disp}"
            sock2 = f"{prefix}/tmp/.X11-unix/X{disp}"
            pipe = f"/tmp/X11-pipe/X{disp}"
            if os.path.exists(sock1) or os.path.exists(sock2) or os.path.exists(pipe):
                # Solo marcar backend si hay sockets reales y procesos gráficos
                if graphical_procs and not detected_backend:
                    detected_backend = "termux-x11"
                detected_display = f":{disp}"

        # Requiere al menos un backend gráfico activo O un entorno de escritorio activo
        if detected_backend or detected_desktop:
            if not detected_backend:
                detected_backend = "termux-x11"
            if not detected_desktop:
                installed = self.get_installed_desktop()
                detected_desktop = installed.get("id")
                detected_desktop_name = installed.get("name")

            return {
                "id": "detected-screen-0",
                "status": DisplayStatus.RUNNING.value,
                "backend": detected_backend,
                "desktop": detected_desktop,
                "desktop_name": detected_desktop_name or (detected_desktop.upper() if detected_desktop else "Ninguno"),
                "display": detected_display,
                "resolution": "Nativo / Detectado",
                "dpi": 96,
                "audio": True,
                "virgl": True,
                "process_count": len(graphical_procs),
                "processes": [p["comm"] for p in graphical_procs if p["comm"]][:5]
            }

        return None

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
        
        detected = self.detect_running_graphical_session()
        is_screen_active = bool(detected or (self.active_session and self.active_session.status == DisplayStatus.RUNNING))

        session_dict = None
        if self.active_session and self.active_session.status == DisplayStatus.RUNNING:
            session_dict = self.active_session.to_dict()
        elif detected:
            session_dict = {
                "id": f"detected-screen-{detected['display'].replace(':', '')}",
                "status": "running",
                "backend": detected["backend"],
                "desktop": detected["desktop_id"],
                "desktop_name": detected["desktop_name"],
                "display": detected["display"],
                "resolution": "Nativo / Detectado",
                "dpi": 96,
                "audio": True,
                "virgl": True,
                "process_count": detected["process_count"],
                "processes": detected["processes"]
            }

        from tdm.version import get_version_info
        from tdm.core.installer import installer_service
        from tdm.core.updater import get_cached_update_info
        ver_info = get_version_info()
        installer_info = installer_service.get_status()
        update_info = get_cached_update_info()

        return {
            "installed_desktop": installed_de,
            "available_backends": backends,
            "network": network,
            "device": dev_info,
            "cpu": cpu_info,
            "memory": mem_info,
            "storage": storage_info,
            "version": ver_info,
            "is_screen_active": is_screen_active,
            "active_screen": session_dict,
            "installer": installer_info,
            "update": update_info
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
        session_script = build_session_script(config.display_num, config.desktop_id, config.custom_command, backend=config.backend)
        session_proc = await self._launch_desktop_session(session_script, session.log_file)

        session.server_pid = backend_obj.process.pid if backend_obj.process else os.getpid()
        session.session_pid = session_proc.pid if session_proc else None
        session.status = DisplayStatus.RUNNING
        session.urls = backend_obj.get_connection_urls()

        self.active_session = session
        log_event("display", f"Pantalla activa en Display :{config.display_num} (PID Servidor: {session.server_pid}, PID Sesión: {session.session_pid})")
        return session.to_dict()

    async def stop_screen(self) -> bool:
        """Detiene completamente cualquier servidor gráfico, entorno de escritorio y deja Termux totalmente limpio."""
        log_event("display", "Iniciando proceso de apagado total y limpieza absoluta de procesos gráficos...")
        
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
            "termux-x11", "Xvnc", "vncserver", "tigervnc", "xrdp", "xrdp-sesman", "websockify",
            "xfce4-session", "xfce4-panel", "xfce4-power-manager", "xfce4-notifyd", "xfce4-appfinder",
            "xfwm4", "xfdesktop", "thunar", "Thunar", "wrapper-2.0", "xfconfd", "xfsettingsd",
            "startplasma-x11", "plasmashell", "kwin_x11", "kwin", "plasma-session", "kded5", "kded6",
            "klauncher", "ksmserver", "kaccess", "mate-session", "mate-panel", "marco", "caja",
            "mate-settings-daemon", "startlxqt", "lxqt-session", "pcmanfm-qt", "lxqt-panel",
            "lxqt-globalkeysd", "lxqt-notificationd", "openbox", "openbox-session", "tint2",
            "i3", "i3bar", "i3status", "xterm", "qterminal", "mate-terminal", "xfce4-terminal",
            "pulseaudio", "virgl_test_server", "virgl_test_server_android", "xorg-xsetroot", "xsetroot"
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

                # No matar el agente de TDM, ni el servidor CLI ni procesos esenciales
                if any(safe in cmdline for safe in ["tdm.cli.main", "tdm.agent.client", "tdm.server.service", "tdm hub", "tdm server"]):
                    continue

                should_kill = False

                # A. Si el proceso tiene DISPLAY=:0 o DISPLAY=: en sus variables de entorno
                if "DISPLAY=:" in environ_str:
                    should_kill = True

                # B. Si el binario o comando coincide con un entorno de escritorio o servidor gráfico
                elif comm in target_names or comm.startswith("xfce4-") or comm.startswith("mate-") or comm.startswith("lxqt-") or comm.startswith("plasma-"):
                    should_kill = True

                # C. Si es un script de inicio de sesión o binario gráfico
                elif any(runner in cmdline for runner in ["session-display", "startxfce4", "startplasma", "startlxqt", "launch_x11", "Xvnc", "termux-x11"]):
                    should_kill = True

                if should_kill:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except Exception:
                        pass
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except Exception:
                        pass
            except Exception:
                pass

        # 4. Barrido de respaldo con pkill por patrones
        patterns = [
            "xfce4", "xfwm4", "xfdesktop", "thunar", "wrapper-2.0", "xfsettingsd",
            "plasmashell", "startplasma", "kwin", "mate-session", "mate-panel", "startlxqt", "lxqt",
            "openbox", "i3", "termux-x11", "Xvnc", "xrdp", "websockify", "virgl_test_server",
            "pulseaudio", "session-display"
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
            ["termux-am", "broadcast", "-a", "com.termux.x11.ACTION_STOP"],
            ["termux-am", "force-stop", "com.termux.x11"]
        ]:
            try:
                subprocess.run(cmd, capture_output=True, timeout=1)
            except Exception:
                pass

        # 6. Limpiar sockets y archivos temporales de X11 en todos los displays (0 a 9)
        for disp_num in range(10):
            self._cleanup_x11_sockets(disp_num)

        # 7. Limpiar scripts de sesión temporales
        try:
            for p in TDM_RUN_DIR.glob("session-display-*.sh"):
                p.unlink(missing_ok=True)
        except Exception:
            pass

        if self.active_session:
            self.active_session.status = DisplayStatus.STOPPED
            self.active_session = None

        log_event("display", "Apagado total completado. Termux quedó completamente limpio de procesos gráficos.")
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
