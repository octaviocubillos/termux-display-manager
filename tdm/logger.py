"""
Sistema unificado de logging para Termux Display Manager (TDM).
Escribe automáticamente en ~/.tdm/logs/ con marcas de tiempo y niveles.
"""

import time
from pathlib import Path
from tdm.config import TDM_LOGS_DIR

def get_timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")

def log_event(component: str, message: str, level: str = "INFO"):
    """Escribe un evento estructurado en ~/.tdm/logs/tdm.log y en el log del componente."""
    try:
        TDM_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        ts = get_timestamp()
        formatted = f"[{ts}] [{level.upper()}] [{component.upper()}]: {message}\n"

        # 1. Log global
        global_log = TDM_LOGS_DIR / "tdm.log"
        with open(global_log, "a", encoding="utf-8", errors="ignore") as f:
            f.write(formatted)

        # 2. Log específico del componente
        comp_map = {
            "agent": "agent.log",
            "server": "server.log",
            "hub": "server.log",
            "display": "session-display-0.log",
            "session": "session-display-0.log",
            "installer": "installer.log",
        }
        spec_name = comp_map.get(component.lower())
        if spec_name:
            with open(TDM_LOGS_DIR / spec_name, "a", encoding="utf-8", errors="ignore") as f:
                f.write(formatted)
    except Exception:
        pass
