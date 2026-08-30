import os
import shutil
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
from tdm.config import IS_TERMUX, PREFIX, HOME, TDM_RUN_DIR
from tdm.core.registry import get_desktop_entry
from tdm.constants import PORT_PULSEAUDIO

def prepare_environment(display_num: int, desktop_id: str, audio: bool = True, virgl: bool = False) -> Dict[str, str]:
    """Genera y prepara las variables de entorno necesarias para la sesión gráfica."""
    env = os.environ.copy()
    
    # 1. Variables X11 y runtime de sesión
    display_str = f":{display_num}"
    runtime_dir = TDM_RUN_DIR / f"user-{os.getuid()}-display-{display_num}"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    
    env["DISPLAY"] = display_str
    env["XDG_RUNTIME_DIR"] = str(runtime_dir)
    env["HOME"] = HOME
    env["SHELL"] = env.get("SHELL", "/bin/sh" if not IS_TERMUX else f"{PREFIX}/bin/bash")
    
    # 2. Configuración de PATH y XDG Base Directory
    current_path = env.get("PATH", "")
    prefix_bin = f"{PREFIX}/bin"
    if prefix_bin not in current_path:
        env["PATH"] = f"{prefix_bin}:{current_path}"

    env["XDG_DATA_DIRS"] = f"{PREFIX}/share:/usr/local/share:/usr/share"
    env["XDG_CONFIG_DIRS"] = f"{PREFIX}/etc/xdg:/etc/xdg"
    
    # 3. Toolkits gráficos en modo X11 puro
    env["GDK_BACKEND"] = "x11"
    env["QT_QPA_PLATFORM"] = "xcb"
    env["CLUTTER_BACKEND"] = "x11"
    env["SDL_VIDEODRIVER"] = "x11"

    # 4. Soporte de Audio (PulseAudio TCP)
    if audio:
        env["PULSE_SERVER"] = f"127.0.0.1:{PORT_PULSEAUDIO}"
        env["PULSE_LATENCY_MSEC"] = "50"

    # 5. Soporte de Aceleración Gráfica (VirGL / Software fallback)
    if virgl:
        env["GALLIUM_DRIVER"] = "virpipe"
        env["MESA_GL_VERSION_OVERRIDE"] = "3.3"
        env["MESA_GLSL_VERSION_OVERRIDE"] = "330"
    else:
        env["LIBGL_ALWAYS_SOFTWARE"] = "1"
        env["GALLIUM_DRIVER"] = "llvmpipe"

    # 6. Cargar variables específicas del entorno desde el Catálogo Central (Sin hardcoding)
    de_info = get_desktop_entry(desktop_id)
    if de_info and "env_vars" in de_info:
        for k, v in de_info["env_vars"].items():
            env[k] = str(v)

    return env

def start_dbus_session(env: Dict[str, str]) -> Dict[str, str]:
    """Inicia un bus de sesión D-Bus si no existe uno activo."""
    if "DBUS_SESSION_BUS_ADDRESS" in env:
        return env

    dbus_launch = shutil.which("dbus-launch")
    if dbus_launch:
        try:
            output = subprocess.check_output(
                [dbus_launch, "--sh-syntax"],
                env=env,
                stderr=subprocess.DEVNULL
            ).decode()
            for line in output.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.split(";")[0].strip().strip("'\"")
                    if k in ["DBUS_SESSION_BUS_ADDRESS", "DBUS_SESSION_BUS_PID"]:
                        env[k] = v
        except Exception:
            pass
            
    return env
