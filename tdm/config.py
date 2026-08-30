import os
import sys
import json
from pathlib import Path

# Detección de entorno
IS_TERMUX = "com.termux" in os.environ.get("PREFIX", "") or os.path.exists("/data/data/com.termux")
IS_ANDROID = os.path.exists("/system/bin/app_process") or os.path.exists("/system/bin/linker64")

# Directorios base
PREFIX = os.environ.get("PREFIX", "/usr" if not IS_TERMUX else "/data/data/com.termux/files/usr")
HOME = os.environ.get("HOME", str(Path.home()))
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
        "vnc_base": 19053,
        "novnc_base": 19052,
        "rdp_base": 19054,
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
