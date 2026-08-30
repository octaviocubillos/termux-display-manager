"""
Módulo de Verificación y Aplicación de Actualizaciones de TDM (Termux Display Manager).
Soporta consulta remota de versión y descarga/instalación autónoma del paquete tdm-bundle.tar.gz.
"""

import asyncio
import json
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional

from tdm.version import __version__, __version_code__, get_version_info
from tdm.config import HOME, PREFIX
from tdm.core.installer import installer_service

DEFAULT_HUB_URL = "https://tdm.oton.cl"

def parse_version_str(ver_str: str) -> tuple:
    """Convierte cadenas de versión como 'v1.2.0' o '1.2.0' a tupla de enteros."""
    cleaned = ver_str.lstrip("v").strip()
    try:
        return tuple(int(x) for x in cleaned.split(".") if x.isdigit())
    except Exception:
        return (0, 0, 0)

def check_for_updates(hub_url: Optional[str] = None) -> Dict[str, Any]:
    """Consulta al servidor Hub si existe una versión más reciente de TDM."""
    if not hub_url:
        cfg_file = Path(HOME) / ".tdm" / "config" / "agent.json"
        if cfg_file.exists():
            try:
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                hub_url = cfg.get("hub")
            except Exception:
                pass
    if not hub_url:
        hub_url = DEFAULT_HUB_URL

    hub_url = hub_url.rstrip("/")
    version_url = f"{hub_url}/api/version"

    local_info = get_version_info()
    current_ver = local_info.get("version", __version__)
    current_code = local_info.get("version_code", __version_code__)

    result = {
        "current_version": current_ver,
        "current_version_code": current_code,
        "latest_version": current_ver,
        "latest_version_code": current_code,
        "update_available": False,
        "hub_url": hub_url,
        "download_url": f"{hub_url}/tdm-bundle.tar.gz"
    }

    try:
        req = urllib.request.Request(
            version_url,
            headers={"User-Agent": f"TDM-Updater/{current_ver}"}
        )
        with urllib.request.urlopen(req, timeout=2.5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                remote_ver = data.get("version", current_ver)
                remote_code = data.get("version_code", current_code)

                is_newer = False
                if remote_code and current_code:
                    is_newer = int(remote_code) > int(current_code)
                else:
                    is_newer = parse_version_str(remote_ver) > parse_version_str(current_ver)

                result["latest_version"] = remote_ver
                result["latest_version_code"] = remote_code
                result["update_available"] = is_newer
                if "download_url" in data:
                    result["download_url"] = data["download_url"]
    except Exception:
        pass

    return result

async def perform_update(hub_url: Optional[str] = None) -> Dict[str, Any]:
    """Descarga e instala la última versión de TDM transmitiendo logs en tiempo real."""
    if not hub_url:
        cfg_file = Path(HOME) / ".tdm" / "config" / "agent.json"
        if cfg_file.exists():
            try:
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                hub_url = cfg.get("hub")
            except Exception:
                pass
    if not hub_url:
        hub_url = DEFAULT_HUB_URL

    hub_url = hub_url.rstrip("/")
    bundle_url = f"{hub_url}/tdm-bundle.tar.gz"

    installer_service.logs.clear()
    installer_service._broadcast_log("=====================================================")
    installer_service._broadcast_log(f"🔄 [TDM Update] Iniciando actualización (Versión actual: v{__version__})")
    installer_service._broadcast_log(f"🌐 Servidor de origen: {hub_url}")
    installer_service._broadcast_log("=====================================================")

    installer_service._broadcast_log("⬇️  Descargando paquete de actualización...")

    loop = asyncio.get_running_loop()

    def download_bundle():
        req = urllib.request.Request(
            bundle_url,
            headers={"User-Agent": f"TDM-Updater/{__version__}"}
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            if response.status != 200:
                raise RuntimeError(f"Error HTTP {response.status} al descargar paquete.")
            return response.read()

    try:
        data = await loop.run_in_executor(None, download_bundle)
        size_kb = len(data) // 1024
        installer_service._broadcast_log(f"📦 Paquete descargado con éxito ({size_kb} KB).")
    except Exception as e:
        installer_service._broadcast_log(f"❌ Error al conectar con el servidor: {e}")
        return {"success": False, "error": str(e), "current_version": __version__}

    # Descomprimir
    installer_service._broadcast_log("🛠️  Aplicando actualización en el sistema...")
    target_dir = Path(HOME) / "termux-display-manager"
    target_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        def extract_tar():
            with tarfile.open(tmp_path, "r:gz") as tar:
                tar.extractall(path=target_dir)
        await loop.run_in_executor(None, extract_tar)
        installer_service._broadcast_log("✓ Archivos del núcleo TDM actualizados correctamente.")
    except Exception as e:
        installer_service._broadcast_log(f"❌ Error al descomprimir actualización: {e}")
        return {"success": False, "error": str(e), "current_version": __version__}
    finally:
        if os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except Exception: pass

    # Actualizar enlace .pth en Python
    try:
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        pth_path = Path(f"{PREFIX}/lib/python{py_ver}/site-packages/tdm.pth")
        if pth_path.parent.exists():
            pth_path.write_text(str(target_dir))
    except Exception:
        pass

    # Actualizar binario ejecutable tdm
    bin_path = Path(f"{PREFIX}/bin/tdm")
    if bin_path.parent.exists():
        wrapper = "#!/data/data/com.termux/files/usr/bin/bash\n"
        wrapper += f'export PYTHONPATH="{target_dir}:$PYTHONPATH"\n'
        wrapper += 'exec python3 -m tdm.cli.main "$@"\n'
        try:
            bin_path.write_text(wrapper)
            bin_path.chmod(0o755)
        except Exception:
            pass

    # Recargar versión
    new_ver = __version__
    try:
        sys.path.insert(0, str(target_dir))
        import importlib
        import tdm.version
        importlib.reload(tdm.version)
        new_ver = tdm.version.__version__
    except Exception:
        pass

    installer_service._broadcast_log(f"🎉 ¡TDM Backend actualizado con éxito a v{new_ver}!")
    installer_service._broadcast_log("=====================================================")
    installer_service._broadcast_log("✅ Actualización completada y operativa.")
    installer_service._broadcast_log("=====================================================")

    return {
        "success": True,
        "old_version": __version__,
        "new_version": new_ver,
        "message": f"Actualizado a v{new_ver}"
    }
