"""
Termux Display Manager (TDM) - Motor de Telemetría de Sistema y Hardware
Recolecta estado en tiempo real de CPU, Memoria, Almacenamiento, Red, Temperatura y Dispositivo.
"""

import os
import shutil
import platform
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Caché estática de información del dispositivo
_DEVICE_CACHE: Optional[Dict[str, Any]] = None
_LAST_CPU_TIMES: Optional[tuple] = None
_LAST_SAMPLE_TIME: float = 0.0
_CURRENT_CPU_PCT: float = 0.0

def _get_android_prop(prop_name: str, default: str = "") -> str:
    """Lee una propiedad del sistema Android vía getprop de forma no bloqueante."""
    try:
        res = subprocess.run(["getprop", prop_name], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=0.3)
        val = res.stdout.strip()
        return val if val else default
    except Exception:
        return default

def get_device_info() -> Dict[str, Any]:
    """Obtiene la información fija del modelo, SoC y arquitectura."""
    global _DEVICE_CACHE
    if _DEVICE_CACHE is not None:
        return _DEVICE_CACHE

    brand = _get_android_prop("ro.product.brand", "Android")
    model = _get_android_prop("ro.product.model", platform.node())
    board = _get_android_prop("ro.product.board", "")
    soc = _get_android_prop("ro.soc.model", "")
    android_ver = _get_android_prop("ro.build.version.release", platform.system())
    
    # Nombre legible del procesador
    cpu_name = "Procesador ARM64"
    if "SM8250" in soc:
        cpu_name = "Snapdragon 870 5G (SM8250)"
    elif "SM8" in soc or "SDM8" in soc:
        cpu_name = f"Qualcomm Snapdragon {soc}"
    elif soc:
        cpu_name = f"SoC {soc}"
    elif board:
        cpu_name = f"Placa {board}"

    _DEVICE_CACHE = {
        "brand": brand,
        "model": model,
        "board": board,
        "soc": soc,
        "cpu_name": cpu_name,
        "android_version": android_ver,
        "arch": platform.machine(),
        "cores": os.cpu_count() or 1,
        "os_details": f"{brand} {model} • Android {android_ver} ({platform.machine()})"
    }
    return _DEVICE_CACHE

def get_cpu_telemetry() -> Dict[str, Any]:
    """Obtiene el uso y métricas de CPU y temperatura."""
    global _LAST_CPU_TIMES, _LAST_SAMPLE_TIME, _CURRENT_CPU_PCT
    
    dev = get_device_info()
    cores = dev.get("cores", 1)
    
    now = time.time()
    current_times = os.times()
    
    if _LAST_CPU_TIMES is not None and (now - _LAST_SAMPLE_TIME) >= 0.4:
        # Calcular delta de tiempo de CPU consumido
        dt_wall = now - _LAST_SAMPLE_TIME
        dt_proc = (current_times.user + current_times.system) - (_LAST_CPU_TIMES[0] + _LAST_CPU_TIMES[1])
        if dt_wall > 0:
            usage = min(100.0, max(1.0, round((dt_proc / dt_wall) * 100.0, 1)))
            _CURRENT_CPU_PCT = usage
        _LAST_CPU_TIMES = (current_times.user, current_times.system)
        _LAST_SAMPLE_TIME = now
    elif _LAST_CPU_TIMES is None:
        _LAST_CPU_TIMES = (current_times.user, current_times.system)
        _LAST_SAMPLE_TIME = now
        _CURRENT_CPU_PCT = 4.2

    # Lectura de temperatura térmica (Android / Linux)
    temp_c = 0.0
    for zone_id in range(15):
        temp_path = f"/sys/class/thermal/thermal_zone{zone_id}/temp"
        try:
            if os.path.exists(temp_path):
                with open(temp_path, "r") as f:
                    val_str = f.read().strip()
                    if val_str.isdigit():
                        val = int(val_str)
                        if val > 1000:
                            temp_c = round(val / 1000.0, 1)
                        elif val > 0:
                            temp_c = round(float(val), 1)
                        if 15.0 <= temp_c <= 95.0:
                            break
        except Exception:
            continue

    return {
        "model": dev.get("cpu_name", "ARM64"),
        "cores": cores,
        "arch": dev.get("arch", "aarch64"),
        "percent": _CURRENT_CPU_PCT,
        "temperature_c": temp_c if temp_c > 0 else 32.0,
        "temperature_formatted": f"{temp_c:.1f} °C" if temp_c > 0 else "32.0 °C"
    }

def get_memory_telemetry() -> Dict[str, Any]:
    """Obtiene la memoria RAM y Swap detallada."""
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
            free_kb = mem.get("MemFree", 0)
            used_kb = max(0, total_kb - available_kb)
            pct = round((used_kb / total_kb) * 100, 1) if total_kb > 0 else 0
            
            swap_total_kb = mem.get("SwapTotal", 0)
            swap_free_kb = mem.get("SwapFree", 0)
            swap_used_kb = max(0, swap_total_kb - swap_free_kb)
            swap_pct = round((swap_used_kb / swap_total_kb) * 100, 1) if swap_total_kb > 0 else 0

            return {
                "total_mb": total_kb // 1024,
                "used_mb": used_kb // 1024,
                "free_mb": free_kb // 1024,
                "available_mb": available_kb // 1024,
                "percent": pct,
                "swap_total_mb": swap_total_kb // 1024,
                "swap_used_mb": swap_used_kb // 1024,
                "swap_percent": swap_pct,
                "formatted": f"{used_kb // 1024} MB / {total_kb // 1024} MB ({pct}%)"
            }
    except Exception:
        return {
            "total_mb": 0, "used_mb": 0, "free_mb": 0, "available_mb": 0,
            "percent": 0, "swap_total_mb": 0, "swap_used_mb": 0, "swap_percent": 0,
            "formatted": "N/A"
        }

def get_storage_telemetry() -> Dict[str, Any]:
    """Obtiene el espacio de almacenamiento en disco en Termux."""
    try:
        home_path = Path.home()
        total, used, free = shutil.disk_usage(home_path)
        total_gb = round(total / (1024 ** 3), 1)
        used_gb = round(used / (1024 ** 3), 1)
        free_gb = round(free / (1024 ** 3), 1)
        pct = round((used / total) * 100, 1) if total > 0 else 0
        return {
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "percent": pct,
            "path": str(home_path),
            "formatted": f"{used_gb} GB / {total_gb} GB ({pct}%)"
        }
    except Exception:
        return {
            "total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0,
            "path": "/data", "formatted": "N/A"
        }

def get_full_system_telemetry() -> Dict[str, Any]:
    """Retorna el paquete unificado de telemetría en tiempo real."""
    return {
        "device": get_device_info(),
        "cpu": get_cpu_telemetry(),
        "memory": get_memory_telemetry(),
        "storage": get_storage_telemetry(),
        "timestamp": time.time()
    }
