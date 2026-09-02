import os
import json
import shutil
import asyncio
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
from tdm.config import HOME, PREFIX, IS_TERMUX, TDM_DIR
from tdm.logger import log_event

GPU_CONFIG_FILE = Path(HOME) / ".tdm" / "config" / "gpu.json"

class GPUManager:
    def __init__(self):
        self._cached_info: Optional[Dict[str, Any]] = None
        self.server_process: Optional[asyncio.subprocess.Process] = None

    def get_gpu_info(self) -> Dict[str, Any]:
        """Obtiene informacion de la GPU y del controlador 3D instalado."""
        if GPU_CONFIG_FILE.exists():
            try:
                with open(GPU_CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                log_event("gpu", f"Error leyendo {GPU_CONFIG_FILE}: {e}", level="WARNING")

        # Deteccion al vuelo si aun no existe archivo de configuracion
        gpu_model = "GPU Generica"
        gpu_vendor = "Generico"
        
        kgsl_model = Path("/sys/class/kgsl/kgsl-3d0/gpu_model")
        if kgsl_model.exists():
            try:
                gpu_model = kgsl_model.read_text().strip()
                gpu_vendor = "Qualcomm"
            except Exception:
                pass
        
        if gpu_vendor == "Generico" and shutil.which("getprop"):
            try:
                soc = subprocess.check_output(["getprop", "ro.soc.model"], text=True, timeout=1).strip()
                hw = subprocess.check_output(["getprop", "ro.hardware"], text=True, timeout=1).strip()
                combined = f"{soc} {hw}".lower()
                if any(k in combined for k in ["qcom", "adreno", "sm8", "sm7", "sm6", "kona", "lahaina"]):
                    gpu_vendor = "Qualcomm"
                    gpu_model = f"Qualcomm Adreno ({soc or hw})"
                elif any(k in combined for k in ["mali", "exynos", "mtk", "mediatek", "dimensity", "tensor"]):
                    gpu_vendor = "ARM"
                    gpu_model = f"ARM Mali ({soc or hw})"
            except Exception:
                pass

        has_freedreno = os.path.exists(f"{PREFIX}/lib/libvulkan_freedreno.so") or os.path.exists(f"{PREFIX}/share/vulkan/icd.d/freedreno_icd.aarch64.json")
        has_virgl = bool(shutil.which("virgl_test_server_android") or shutil.which("virgl_test_server"))
        
        return {
            "gpu_model": gpu_model,
            "gpu_vendor": gpu_vendor,
            "driver_type": "turnip_zink" if has_freedreno else ("virgl" if has_virgl else "llvmpipe"),
            "driver_name": "Mesa Turnip + Zink" if has_freedreno else ("VirGL Renderer Android" if has_virgl else "Software llvmpipe"),
            "virgl_supported": has_virgl,
            "installed": bool(has_freedreno or has_virgl)
        }

    def is_3d_installed(self) -> bool:
        """Comprueba si el controlador 3D o VirGL esta instalado."""
        info = self.get_gpu_info()
        if info.get("installed", False):
            return True
        if shutil.which("virgl_test_server_android") or shutil.which("virgl_test_server"):
            return True
        if os.path.exists(f"{PREFIX}/share/vulkan/icd.d/freedreno_icd.aarch64.json"):
            return True
        return False

    async def start_3d_services(self, display_num: int = 0) -> bool:
        """Inicia el servidor de aceleracion 3D VirGL en segundo plano si esta disponible."""
        virgl_bin = shutil.which("virgl_test_server_android") or shutil.which("virgl_test_server")
        if not virgl_bin:
            log_event("gpu", "Servidor VirGL no instalado, usando renderizado estandar.")
            return False

        # Detener servidor previo si existiera
        await self.stop_3d_services()

        cmd = [virgl_bin]
        if "virgl_test_server_android" in virgl_bin:
            cmd.extend(["--angle-vulkan"])

        try:
            log_event("gpu", f"Iniciando servidor 3D ({virgl_bin})...")
            self.server_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                cwd=HOME if os.path.exists(HOME) else None
            )
            await asyncio.sleep(0.3)
            log_event("gpu", f"Servidor 3D iniciado con PID {self.server_process.pid}.")
            return True
        except Exception as e:
            log_event("gpu", f"No se pudo iniciar servidor 3D: {e}", level="WARNING")
            self.server_process = None
            return False

    async def stop_3d_services(self):
        """Detiene de forma segura cualquier instancia activa del servidor 3D VirGL."""
        if self.server_process:
            try:
                self.server_process.terminate()
                await asyncio.sleep(0.2)
                if self.server_process.returncode is None:
                    self.server_process.kill()
            except Exception:
                pass
            self.server_process = None

        # Matar procesos huerfanos
        try:
            for proc_name in ["virgl_test_server_android", "virgl_test_server"]:
                subprocess.run(["pkill", "-9", "-x", proc_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

gpu_manager = GPUManager()
