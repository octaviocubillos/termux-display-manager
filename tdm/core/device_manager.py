import os
import json
import shutil
import asyncio
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from tdm.config import IS_TERMUX, PREFIX
from tdm.logger import log_event

class DeviceManager:
    def __init__(self):
        self._cached_api_installed: Optional[bool] = None

    def is_termux_api_installed(self) -> bool:
        """Verifica si los binarios CLI de termux-api estan disponibles."""
        bin_dir = Path(PREFIX) / "bin"
        return bool(shutil.which("termux-battery-status") or shutil.which("termux-volume") or (bin_dir / "termux-battery-status").exists())

    def is_termux_api_app_installed(self) -> bool:
        """Comprueba si la aplicacion Termux:API esta disponible."""
        if not IS_TERMUX:
            return True
        return self.is_termux_api_installed()

    def get_battery_status(self) -> Dict[str, Any]:
        """Obtiene el estado completo y telemetria de la bateria del dispositivo."""
        # 1. Intentar termux-battery-status
        if shutil.which("termux-battery-status"):
            try:
                out = subprocess.check_output(["termux-battery-status"], text=True, timeout=2).strip()
                if out:
                    data = json.loads(out)
                    pct = int(data.get("percentage", data.get("level", 0)))
                    status_str = str(data.get("status", "UNKNOWN")).upper()
                    is_charging = status_str in ["CHARGING", "FULL"]
                    plugged = str(data.get("plugged", "UNPLUGGED")).upper()
                    if plugged != "UNPLUGGED":
                        is_charging = True
                    return {
                        "percentage": pct,
                        "status": status_str,
                        "health": str(data.get("health", "GOOD")).upper(),
                        "plugged": plugged,
                        "temperature": float(data.get("temperature", 0.0)),
                        "current": data.get("current", 0),
                        "is_charging": is_charging,
                        "source": "termux-api"
                    }
            except Exception as e:
                log_event("device", f"Aviso leyendo termux-battery-status: {e}", level="DEBUG")

        # 2. Fallback mediante sysfs de Linux/Android
        capacity_paths = [
            "/sys/class/power_supply/battery/capacity",
            "/sys/class/power_supply/BAT0/capacity",
            "/sys/class/power_supply/BAT1/capacity"
        ]
        status_paths = [
            "/sys/class/power_supply/battery/status",
            "/sys/class/power_supply/BAT0/status",
            "/sys/class/power_supply/BAT1/status"
        ]
        temp_paths = [
            "/sys/class/power_supply/battery/temp",
            "/sys/class/power_supply/battery/batt_temp"
        ]

        pct = 100
        status_str = "DISCHARGING"
        temp_val = 0.0

        for p in capacity_paths:
            if os.path.exists(p):
                try:
                    pct = int(Path(p).read_text().strip())
                    break
                except Exception:
                    pass

        for p in status_paths:
            if os.path.exists(p):
                try:
                    status_str = Path(p).read_text().strip().upper()
                    break
                except Exception:
                    pass

        for p in temp_paths:
            if os.path.exists(p):
                try:
                    raw_temp = float(Path(p).read_text().strip())
                    temp_val = raw_temp / 10.0 if raw_temp > 100 else raw_temp
                    break
                except Exception:
                    pass

        is_charging = status_str in ["CHARGING", "FULL"]
        return {
            "percentage": pct,
            "status": status_str,
            "health": "GOOD",
            "plugged": "AC" if is_charging else "UNPLUGGED",
            "temperature": temp_val,
            "current": 0,
            "is_charging": is_charging,
            "source": "sysfs"
        }

    def get_volume_info(self) -> Dict[str, Any]:
        """Obtiene el estado del volumen de los canales de audio."""
        if shutil.which("termux-volume"):
            try:
                out = subprocess.check_output(["termux-volume"], text=True, timeout=2).strip()
                if out:
                    streams = json.loads(out)
                    streams_dict = {}
                    music_vol = 50
                    music_max = 100
                    for s in streams:
                        name = s.get("stream", "unknown")
                        vol = int(s.get("volume", 0))
                        max_v = int(s.get("max_volume", 100))
                        pct = int((vol / max_v * 100) if max_v > 0 else 0)
                        streams_dict[name] = {
                            "volume": vol,
                            "max_volume": max_v,
                            "percent": pct
                        }
                        if name == "music":
                            music_vol = vol
                            music_max = max_v

                    return {
                        "music_percent": int((music_vol / music_max * 100) if music_max > 0 else 0),
                        "music_volume": music_vol,
                        "music_max": music_max,
                        "streams": streams_dict,
                        "source": "termux-api"
                    }
            except Exception as e:
                log_event("device", f"Aviso leyendo termux-volume: {e}", level="DEBUG")

        # Fallback PulseAudio o generico
        return {
            "music_percent": 75,
            "music_volume": 75,
            "music_max": 100,
            "streams": {
                "music": {"volume": 75, "max_volume": 100, "percent": 75}
            },
            "source": "fallback"
        }

    def set_volume(self, level_percent: int, stream: str = "music") -> Dict[str, Any]:
        """Ajusta el volumen en porcentaje (0-100) para un stream dado (por defecto 'music')."""
        level_percent = max(0, min(100, int(level_percent)))
        
        # 1. Si termux-volume esta disponible
        if shutil.which("termux-volume"):
            try:
                # Obtener max_volume para el stream
                info = self.get_volume_info()
                stream_info = info.get("streams", {}).get(stream, {})
                max_v = stream_info.get("max_volume", 15)
                target_val = round((level_percent / 100.0) * max_v)
                
                subprocess.run(["termux-volume", stream, str(target_val)], capture_output=True, timeout=2)
                log_event("device", f"Volumen '{stream}' ajustado a {level_percent}% (valor nativo: {target_val}/{max_v})")
                return {
                    "success": True,
                    "stream": stream,
                    "percent": level_percent,
                    "raw_value": target_val,
                    "max_volume": max_v
                }
            except Exception as e:
                log_event("device", f"Error en termux-volume: {e}", level="WARNING")

        # 2. Fallback pactl (PulseAudio) si existe
        if shutil.which("pactl"):
            try:
                subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level_percent}%"], capture_output=True, timeout=1)
                log_event("device", f"Volumen PulseAudio ajustado a {level_percent}%")
                return {"success": True, "stream": "pulseaudio", "percent": level_percent}
            except Exception:
                pass

        return {"success": True, "stream": stream, "percent": level_percent, "message": "Ajustado en software"}

    def set_brightness(self, level: int) -> Dict[str, Any]:
        """Ajusta el brillo de la pantalla del telefono (0 a 255)."""
        level = max(0, min(255, int(level)))
        if shutil.which("termux-brightness"):
            try:
                subprocess.run(["termux-brightness", str(level)], capture_output=True, timeout=2)
                log_event("device", f"Brillo ajustado a {level}/255")
                return {"success": True, "level": level}
            except Exception as e:
                log_event("device", f"Error en termux-brightness: {e}", level="WARNING")

        return {"success": False, "error": "termux-brightness no disponible"}

    def is_app_installed_android(self, package_name: str) -> bool:
        """Comprueba si una app de Android está instalada en el sistema mediante pm."""
        if not IS_TERMUX:
            return True
        try:
            out = subprocess.check_output(["pm", "list", "packages", package_name], text=True, timeout=2).strip()
            if f"package:{package_name}" in out:
                return True
        except Exception:
            pass
        return False

    def is_termux_api_app_installed(self) -> bool:
        """Comprueba si la aplicacion Android Termux:API esta instalada y disponible."""
        if not IS_TERMUX:
            return True
        if self.is_app_installed_android("com.termux.api"):
            return True
        if shutil.which("termux-battery-status"):
            try:
                out = subprocess.check_output(["termux-battery-status"], text=True, timeout=2).strip()
                if out and ("percentage" in out or "level" in out):
                    return True
            except Exception:
                pass
        return False

    def is_termux_x11_package_installed(self) -> bool:
        """Comprueba si el paquete binario termux-x11 esta instalado en Termux."""
        prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
        return bool(shutil.which("termux-x11") or (Path(prefix) / "bin" / "termux-x11").exists())

    def is_termux_x11_app_installed(self) -> bool:
        """Comprueba si la aplicacion APK Termux:X11 esta instalada en Android."""
        if not IS_TERMUX:
            return True
        return self.is_app_installed_android("com.termux.x11")

    def get_companion_status(self) -> Dict[str, Any]:
        """Devuelve el estado de las aplicaciones complementarias recomendadas."""
        x11_pkg = self.is_termux_x11_package_installed()
        x11_app = self.is_termux_x11_app_installed()
        x11_ready = bool(x11_pkg and x11_app)

        api_pkg = self.is_termux_api_installed()
        api_app = self.is_termux_api_app_installed()
        api_ready = bool(api_pkg and api_app)

        needs_setup = not (x11_ready and api_ready)
        needs_pkg_install = not (x11_pkg and api_pkg)

        return {
            "needs_setup": needs_setup,
            "needs_pkg_install": needs_pkg_install,
            "termux_x11": {
                "package_installed": x11_pkg,
                "app_installed": x11_app,
                "ready": x11_ready,
                "apk_url": "https://github.com/termux/termux-x11/releases",
                "apk_name": "Termux:X11 (GitHub Releases)",
                "pkg_command": "pkg install -y x11-repo && pkg install -y termux-x11-nightly"
            },
            "termux_api": {
                "package_installed": api_pkg,
                "app_installed": api_app,
                "ready": api_ready,
                "apk_url": "https://github.com/termux/termux-api/releases",
                "apk_name": "Termux:API (GitHub / F-Droid)",
                "pkg_command": "pkg install -y termux-api"
            }
        }

    def get_full_device_info(self) -> Dict[str, Any]:
        """Devuelve el estado integrado de hardware, bateria, volumen, termux-api y companion apps."""
        companion = self.get_companion_status()
        cli_installed = companion["termux_api"]["package_installed"]
        app_installed = companion["termux_api"]["app_installed"]
        
        return {
            "battery": self.get_battery_status(),
            "volume": self.get_volume_info(),
            "companion": companion,
            "api": {
                "cli_installed": cli_installed,
                "app_installed": app_installed,
                "ready": bool(cli_installed and app_installed),
                "install_pkg_command": "pkg install -y termux-api"
            }
        }

device_manager = DeviceManager()
