import asyncio
import os
import signal
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List

from tdm.core.manifest import manifest_ledger
from tdm.config import TDM_DIR, PREFIX, HOME

class UninstallerService:
    """Servicio de desinstalación selectiva que elimina únicamente lo instalado mediante TDM."""

    async def perform_uninstall(self, purge_packages: bool = True) -> Dict[str, Any]:
        result = {
            "stopped_processes": [],
            "uninstalled_packages": [],
            "removed_files": [],
            "success": True
        }

        # 1. Detener procesos y servidores activos
        for proc_name in ["tdm.cli.main", "websockify", "Xvnc", "termux-x11", "xrdp"]:
            try:
                subprocess.run(["pkill", "-9", "-f", proc_name], stderr=subprocess.DEVNULL)
                result["stopped_processes"].append(proc_name)
            except Exception:
                pass

        # 2. Desinstalar SOLO los paquetes que TDM registró en el SQLite manifest
        if purge_packages:
            tracked_pkgs = manifest_ledger.get_tdm_installed_packages()
            pkg_names = [p["package_name"] for p in tracked_pkgs if p.get("package_name")]

            if pkg_names:
                print(f"🗑️ [TDM Uninstaller] Desinstalando paquetes instalados por TDM: {', '.join(pkg_names)}")
                try:
                    # Ejecutar pkg uninstall solo para los paquetes de TDM
                    cmd = ["apt-get", "remove", "-y"] + pkg_names
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await proc.communicate()
                    result["uninstalled_packages"] = pkg_names
                except Exception as e:
                    result["package_error"] = str(e)

        # 3. Limpiar sockets temporales X11
        for pattern in ["/tmp/.X*-lock", "/tmp/.X11-unix/X*", "/tmp/X11-pipe/X*", "/tmp/dbus-*"]:
            for f in Path("/tmp").glob(pattern.replace("/tmp/", "")):
                try:
                    f.unlink()
                    result["removed_files"].append(str(f))
                except Exception:
                    pass

        # 4. Eliminar ejecutable global tdm y enlaces .pth
        tdm_bin = Path(f"{PREFIX}/bin/tdm")
        if tdm_bin.exists():
            try:
                tdm_bin.unlink()
                result["removed_files"].append(str(tdm_bin))
            except Exception:
                pass

        for pth in Path(f"{PREFIX}/lib").glob("python*/site-packages/tdm.pth"):
            try:
                pth.unlink()
                result["removed_files"].append(str(pth))
            except Exception:
                pass

        # 5. Limpiar instaladores temporales
        for temp_f in ["/sdcard/Download/tdm-bundle.tar.gz", "/sdcard/Download/install_tdm.sh"]:
            if os.path.exists(temp_f):
                try:
                    os.unlink(temp_f)
                    result["removed_files"].append(temp_f)
                except Exception:
                    pass

        # 6. Borrar directorio ~/.tdm y la base de datos SQLite
        if TDM_DIR.exists():
            try:
                shutil.rmtree(TDM_DIR)
                result["removed_files"].append(str(TDM_DIR))
            except Exception:
                pass

        return result

uninstaller_service = UninstallerService()
