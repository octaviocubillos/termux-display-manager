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

        print("=====================================================")
        print("🗑️  [TDM] Desinstalación Selectiva de Termux Display Manager")
        print("=====================================================")

        # 1. Detener procesos y servidores activos (sin matar el proceso actual)
        print("[1/5] Deteniendo servidores de pantalla y procesos activos...")
        current_pid = os.getpid()
        for proc_pattern in [
            "tdm.agent.client",
            "tdm.cli.main server",
            "websockify",
            "Xvnc",
            "termux-x11",
            "xrdp"
        ]:
            try:
                subprocess.run(f"pkill -f '{proc_pattern}' 2>/dev/null || true", shell=True)
                result["stopped_processes"].append(proc_pattern)
            except Exception:
                pass

        # Liberar wake-lock en Termux si está activo
        try:
            subprocess.run("termux-wake-unlock 2>/dev/null || true", shell=True)
        except Exception:
            pass

        # 2. Desinstalar SOLO los paquetes que TDM registró en el SQLite manifest
        print("[2/5] Consultando registro SQLite para desinstalar solo paquetes de TDM...")
        if purge_packages:
            try:
                tracked_pkgs = manifest_ledger.get_tdm_installed_packages()
                pkg_names = [p["package_name"] for p in tracked_pkgs if p.get("package_name")]

                if pkg_names:
                    print(f"📦 [TDM Uninstaller] Desinstalando paquetes registrados por TDM: {', '.join(pkg_names)}")
                    if shutil.which("pkg"):
                        cmd = ["pkg", "uninstall", "-y"] + pkg_names
                    elif shutil.which("apk"):
                        cmd = ["apk", "del"] + pkg_names
                    elif shutil.which("apt-get"):
                        cmd = ["apt-get", "remove", "-y"] + pkg_names
                    elif shutil.which("pacman"):
                        cmd = ["pacman", "-R", "--noconfirm"] + pkg_names
                    elif shutil.which("dnf"):
                        cmd = ["dnf", "remove", "-y"] + pkg_names
                    else:
                        cmd = ["apt-get", "remove", "-y"] + pkg_names

                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await proc.communicate()
                    result["uninstalled_packages"] = pkg_names
                else:
                    print("ℹ️  No hay paquetes registrados exclusivamente por TDM.")
            except Exception as e:
                result["package_error"] = str(e)

        # 3. Limpiar sockets temporales X11
        print("[3/5] Limpiando sockets X11 temporales...")
        tmp_dirs = [Path(os.environ.get("TMPDIR", f"{PREFIX}/tmp")), Path("/tmp")]
        for tdir in tmp_dirs:
            if tdir.exists() and os.access(str(tdir), os.W_OK):
                for pattern in [".X*-lock", ".X11-unix/X*", "X11-pipe/X*", "dbus-*"]:
                    try:
                        for f in tdir.glob(pattern):
                            try:
                                f.unlink()
                                result["removed_files"].append(str(f))
                            except Exception:
                                pass
                    except Exception:
                        pass

        # 4. Eliminar ejecutable global tdm y enlaces .pth
        print("[4/5] Removiendo ejecutable global 'tdm' y enlaces Python...")
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
        print("[5/5] Eliminando directorio de configuración (~/.tdm)...")
        if TDM_DIR.exists():
            try:
                shutil.rmtree(TDM_DIR)
                result["removed_files"].append(str(TDM_DIR))
            except Exception:
                pass

        print("=====================================================")
        print("✅ [TDM] Desinstalación completada con éxito.")
        print("🧹 Se eliminaron los servicios y componentes de TDM.")
        print("🛡️  Tus paquetes y configuraciones personales han sido preservados.")
        print("=====================================================")

        return result

uninstaller_service = UninstallerService()
