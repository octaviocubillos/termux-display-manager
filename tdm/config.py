import os
import sys
import json
from pathlib import Path

# Detección de entorno
IS_TERMUX = "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux")
IS_ANDROID = os.path.exists("/system/bin/app_process") or os.path.exists("/system/bin/linker64")

# Directorios base
PREFIX = os.environ.get("PREFIX", "/usr" if not IS_TERMUX else "/data/data/com.termux/files/usr")
HOME = os.environ.get("HOME") or ("/data/data/com.termux/files/home" if IS_TERMUX else str(Path.home()))
TDM_SYSTEM_DIR = Path(PREFIX) / "opt" / "termux-display-manager"
TDM_DIR = Path(HOME) / ".tdm"
TDM_CONFIG_FILE = TDM_DIR / "config.json"
TDM_LOGS_DIR = TDM_DIR / "logs"
TDM_RUN_DIR = TDM_DIR / "run"

# Crear directorios si no existen
TDM_DIR.mkdir(parents=True, exist_ok=True)
TDM_LOGS_DIR.mkdir(parents=True, exist_ok=True)
TDM_RUN_DIR.mkdir(parents=True, exist_ok=True)

# Configuración por defecto
DEFAULT_CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 19050,
        "allow_remote": True,
    },
    "defaults": {
        "resolution": "1920x1080",
        "dpi": 96,
        "depth": 24,
        "audio": True,
        "virgl": False,
    },
    "ports": {
        "vnc_base": 5900,
        "novnc_base": 19052,
        "rdp_base": 3389,
        "pulseaudio_tcp": 19055,
    },
    "custom_desktops": []
}

def load_config() -> dict:
    if TDM_CONFIG_FILE.exists():
        try:
            with open(TDM_CONFIG_FILE, "r", encoding="utf-8") as f:
                user_conf = json.load(f)
                conf = DEFAULT_CONFIG.copy()
                conf.update(user_conf)
                return conf
        except Exception:
            pass
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG

def save_config(conf: dict) -> None:
    try:
        with open(TDM_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(conf, f, indent=2)
    except Exception as e:
        sys.stderr.write(f"Error guardando config TDM: {e}\n")

def get_user_shell() -> str:
    """
    Obtiene el shell preferido del usuario.
    Por defecto usa bash (el shell nativo de Termux y Linux), a menos que el usuario
    lo haya cambiado explícitamente vía ~/.termux/shell, TDM config o variable $SHELL válida.
    """
    import shutil

    # 1. Configuración explícita en ~/.termux/shell
    custom_shell_file = Path(HOME) / ".termux" / "shell"
    if custom_shell_file.exists():
        try:
            candidate = custom_shell_file.read_text(encoding="utf-8").strip()
            if candidate and os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return candidate
        except Exception:
            pass

    # 2. Configuración en config.json de TDM
    try:
        conf = load_config()
        custom_tdm_shell = conf.get("shell") or conf.get("defaults", {}).get("shell")
        if custom_tdm_shell and os.path.exists(custom_tdm_shell) and os.access(custom_tdm_shell, os.X_OK):
            return custom_tdm_shell
    except Exception:
        pass

    # 3. Variable de entorno $SHELL si fue configurada por el usuario (y no es sh restrictivo de Android)
    env_shell = os.environ.get("SHELL", "").strip()
    if env_shell and env_shell not in ("/bin/sh", "/system/bin/sh") and os.path.exists(env_shell) and os.access(env_shell, os.X_OK):
        return env_shell

    # 4. Fallback por defecto: bash
    bash_candidates = [
        f"{PREFIX}/bin/bash",
        shutil.which("bash"),
        "/bin/bash",
        "/usr/bin/bash"
    ]
    for b in bash_candidates:
        if b and os.path.exists(b) and os.access(b, os.X_OK):
            return b

    # 5. Último recurso si no existe bash
    fallback_sh = shutil.which("sh") or f"{PREFIX}/bin/sh" or "/bin/sh"
    return fallback_sh
