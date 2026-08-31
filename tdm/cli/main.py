"""
Punto de entrada principal para Termux Display Manager (TDM) CLI.
Soporta comandos locales, servidor HTTP/PWA, Hub Central y Agente Remoto.
"""

import argparse
import asyncio
import sys
import os
import shutil
import subprocess
from pathlib import Path

from tdm import __version__
from tdm.core.display_manager import display_manager
from tdm.core.installer import installer_service
from tdm.server.http_server import AsyncHTTPServer
from tdm.discovery.desktops import discover_desktops
from tdm.discovery.backends import discover_backends
from tdm.discovery.network import discover_network_interfaces
from tdm.constants import (
    PORT_TDM_SERVER,
    BACKEND_TERMUX_X11,
    DEFAULT_RESOLUTION,
    DEFAULT_DPI,
    SESSION_MODE_DESKTOP,
    SESSION_MODE_TERMINAL,
)

def print_banner():
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║             Termux Display Manager (TDM) v{__version__}             ║
║     Gestor de Pantallas, PWA y Servidores para Android       ║
╚══════════════════════════════════════════════════════════════╝
""")

async def handle_status():
    status = display_manager.get_status()
    de = status["installed_desktop"]
    net = status.get("network", discover_network_interfaces())
    
    print(f"🎨 Entorno Nativo Instalado: {de['name']} ({de.get('executable', 'N/A')})")
    
    if status["is_screen_active"]:
        scr = status["active_screen"]
        print(f"🟢 Estado de Pantalla: ACTIVA")
        print(f"  • Display:      {scr['display']}")
        print(f"  • Salida:       {scr['backend']}")
        print(f"  • Resolución:   {scr['resolution']}")
        print(f"  • PID Servidor: #{scr.get('server_pid')}")
        print(f"  • Audio/VirGL:  {'Sí' if scr.get('audio') else 'No'} / {'Sí' if scr.get('virgl') else 'No'}")
        if scr.get("urls"):
            print(f"  • Conexión:     {scr['urls']}")
    else:
        print("🔴 Estado de Pantalla: APAGADA (Sin servidor gráfico en ejecución)")

    print("\n🌐 Conectividad y URLs de Acceso:")
    print(f"  • Local:        {net['access_urls']['local']}")
    if net.get("lan_ip") and net["lan_ip"] != "127.0.0.1":
        print(f"  • Red LAN:      {net['access_urls']['lan']}")
    if net.get("tailscale_ip"):
        print(f"  • Tailscale:    {net['access_urls']['tailscale']}")

async def handle_start(args):
    print(f"🚀 [TDM] Iniciando pantalla en backend '{args.backend}'...")
    result = await display_manager.start_screen(
        backend=args.backend,
        mode=args.mode,
        resolution=args.resolution,
        dpi=args.dpi,
        audio=not args.no_audio,
        virgl=not args.no_virgl
    )
    if result.get("status") == "running":
        print(f"✅ Pantalla iniciada con éxito en {args.backend} (:0)")
        if result.get("urls"):
            for k, v in result["urls"].items():
                print(f"   {k}: {v}")
    else:
        print(f"❌ Error iniciando pantalla: {result.get('error_message')}")

async def handle_stop():
    print("🛑 [TDM] Deteniendo pantalla activa...")
    await display_manager.stop_screen()
    print("✅ Pantalla detenida y sockets X11 liberados.")

async def handle_doctor():
    print("🔍 [TDM] Comprobando componentes del sistema...")
    desktops = discover_desktops()
    backends = discover_backends()
    net = discover_network_interfaces()
    
    print("\n📌 Entornos de Escritorio:")
    for d in desktops:
        status_icon = "✓" if d["installed"] else "✗"
        print(f"  [{status_icon}] {d['name']:<22} {'Instalado (' + d['executable'] + ')' if d['installed'] else 'No instalado'}")

    print("\n📌 Servidores de Pantalla (Backends):")
    for b in backends:
        status_icon = "✓" if b["installed"] else "✗"
        print(f"  [{status_icon}] {b['name']:<25} {'Disponible' if b['installed'] else 'No disponible'}")

    print("\n📌 Interfaces de Red y Acceso:")
    print(f"  [✓] Localhost:             127.0.0.1 (http://localhost:{net['ports']['pwa_server']})")
    print(f"  [{'✓' if net['lan_ip'] != '127.0.0.1' else '✗'}] IP Local (LAN):          {net['lan_ip']}")
    if net.get("tailscale_ip"):
        print(f"  [✓] Tailscale Mesh VPN:    {net['tailscale_ip']} (Activo)")
    else:
        print(f"  [i] Tailscale Mesh VPN:    No detectado (Opcional para acceso fuera de casa)")

async def handle_server(args, is_hub=False):
    server = AsyncHTTPServer(host=args.host, port=args.port, is_hub=is_hub)
    await server.start()

async def handle_agent(args):
    from tdm.agent.client import TDMAgent
    agent = TDMAgent(hub_url=args.hub, token=args.token)
    await agent.run()

async def handle_install(args):
    if args.minimal or args.dependencies:
        print("⚡ [TDM] Ejecutando instalación mínima fundamental...")
        success = await installer_service.run_script("setup_minimal.sh")
        print("✅ Dependencias mínimas listas." if success else "❌ Error en dependencias mínimas.")
    elif args.server:
        print(f"🖥️ [TDM] Instalando servidor gráfico '{args.server}' bajo demanda...")
        success = await installer_service.run_script("install_server.sh", [args.server])
        print(f"✅ Servidor {args.server} instalado con éxito." if success else f"❌ Error instalando servidor {args.server}.")
    elif args.desktop:
        print(f"🎨 [TDM] Instalando entorno de escritorio '{args.desktop}' bajo demanda...")
        success = await installer_service.run_script("install_desktop.sh", [args.desktop])
        print(f"✅ {args.desktop} instalado con éxito." if success else f"❌ Error instalando {args.desktop}.")
    elif args.full:
        print("📦 [TDM] Ejecutando instalación completa de todos los servidores...")
        success = await installer_service.run_script("setup_dependencies.sh")
async def handle_service(action: str):
    import subprocess
    home = Path.home()
    prefix = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
    logs_dir = home / ".tdm" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    python_bin = shutil.which("python3") or f"{prefix}/bin/python3"
    tdm_dir = home / "termux-display-manager"
    sv_bin = shutil.which("sv") or f"{prefix}/bin/sv"
    sv_enable_bin = shutil.which("sv-enable") or f"{prefix}/bin/sv-enable"
    sv_disable_bin = shutil.which("sv-disable") or f"{prefix}/bin/sv-disable"
    has_sv = os.path.exists(sv_bin) and os.path.exists(f"{prefix}/var/service/tdm/run")

    env = {
        **os.environ,
        "PATH": f"{prefix}/bin:" + os.environ.get("PATH", ""),
        "PYTHONPATH": f"{tdm_dir}:" + os.environ.get("PYTHONPATH", ""),
        "HOME": str(home),
        "PREFIX": str(prefix)
    }

    if action in ["start", "enable"]:
        print("🚀 [TDM Service] Iniciando/Habilitando servicio...")
        wake_lock = shutil.which("termux-wake-lock") or f"{prefix}/bin/termux-wake-lock"
        if os.path.exists(wake_lock):
            subprocess.run([wake_lock], capture_output=True)
            print("🔒 Termux Wake-Lock activado (evita suspensión por ahorro de batería)")

        # Si termux-services está configurado, usar sv / sv-enable
        if has_sv:
            if action == "enable" and os.path.exists(sv_enable_bin):
                subprocess.run([sv_enable_bin, "tdm"], capture_output=True)
            subprocess.run([sv_bin, "up", "tdm"], capture_output=True)
            print("⚙️  Servicio 'tdm' gestionado por termux-services (sv up)")

        # Iniciar server HTTP como daemon si no está corriendo
        res = subprocess.run(["pgrep", "-f", "tdm.cli.main server"], capture_output=True, text=True)
        if not res.stdout.strip():
            server_log = open(logs_dir / "server.log", "a")
            subprocess.Popen([python_bin, "-m", "tdm.cli.main", "server", "--port", str(PORT_TDM_SERVER)], stdout=server_log, stderr=server_log, env=env)
            print(f"🟢 Servidor HTTP API iniciado en background (:{PORT_TDM_SERVER})")
        else:
            print(f"ℹ️ Servidor HTTP API en ejecución (:{PORT_TDM_SERVER})")

        # Iniciar agent si existe configuración
        cfg_file = home / ".tdm" / "config" / "agent.json"
        if cfg_file.exists():
            res = subprocess.run(["pgrep", "-f", "tdm.agent.client"], capture_output=True, text=True)
            if not res.stdout.strip():
                agent_log = open(logs_dir / "agent.log", "a")
                subprocess.Popen([python_bin, "-m", "tdm.agent.client"], stdout=agent_log, stderr=agent_log, env=env)
                print("🟢 Agente WebSocket TDM iniciado en background")
        print("✅ Servicios TDM activos.")

    elif action in ["stop", "disable"]:
        print("🛑 [TDM Service] Deteniendo/Deshabilitando servicios...")
        if has_sv:
            subprocess.run([sv_bin, "down", "tdm"], capture_output=True)
            if action == "disable" and os.path.exists(sv_disable_bin):
                subprocess.run([sv_disable_bin, "tdm"], capture_output=True)
            print("⚙️  Servicio 'tdm' detenido en termux-services (sv down)")

        subprocess.run(["pkill", "-f", "tdm.agent.client"], capture_output=True)
        subprocess.run(["pkill", "-f", "tdm.cli.main server"], capture_output=True)
        wake_unlock = shutil.which("termux-wake-unlock") or f"{prefix}/bin/termux-wake-unlock"
        if os.path.exists(wake_unlock):
            subprocess.run([wake_unlock], capture_output=True)
        print("✅ Servicios TDM detenidos y Wake-Lock liberado.")

    elif action == "restart":
        print("🔄 [TDM Service] Reiniciando servicios...")
        await handle_service("stop")
        await asyncio.sleep(1)
        await handle_service("start")

    elif action == "status":
        s_res = subprocess.run(["pgrep", "-f", "tdm.cli.main server"], capture_output=True, text=True)
        a_res = subprocess.run(["pgrep", "-f", "tdm.agent.client"], capture_output=True, text=True)
        s_status = "🟢 En ejecución" if s_res.stdout.strip() else "🔴 Detenido"
        a_status = "🟢 En ejecución" if a_res.stdout.strip() else "🔴 Detenido"
        
        print("=====================================================")
        print("📌 [TDM] Estado de los Servicios en Segundo Plano:")
        print("=====================================================")
        print(f"  • Servidor HTTP API (:{PORT_TDM_SERVER}):  {s_status}")
        print(f"  • Agente Hub WebSocket:         {a_status}")
        
        if has_sv:
            sv_out = subprocess.run([sv_bin, "status", "tdm"], capture_output=True, text=True).stdout.strip()
            print(f"  • Gestor Termux (runit/sv):     {sv_out or 'Supervisado'}")
        else:
            print(f"  • Gestor Termux (runit/sv):     No configurado (se instala con setup_minimal.sh)")
        print("=====================================================")

async def handle_logs(args):
    """Muestra y gestiona los registros de TDM (agente, servidor y sesión gráfica)."""
    from tdm.config import TDM_LOGS_DIR
    
    if getattr(args, "clear", False):
        for p in TDM_LOGS_DIR.glob("*.log"):
            try:
                p.write_text("")
            except Exception:
                pass
        print("🧹 [TDM Logs] Registros limpiados correctamente.")
        return

    lines_count = getattr(args, "lines", 50) or 50
    follow = getattr(args, "follow", False)

    log_files = {
        "agent": TDM_LOGS_DIR / "agent.log",
        "server": TDM_LOGS_DIR / "server.log",
        "session": TDM_LOGS_DIR / "session-display-0.log"
    }

    target = None
    if getattr(args, "agent", False):
        target = "agent"
    elif getattr(args, "server", False):
        target = "server"
    elif getattr(args, "session", False):
        target = "session"

    if target:
        chosen_file = log_files[target]
        if not chosen_file.exists() or chosen_file.stat().st_size == 0:
            print(f"ℹ️ El archivo de registro '{chosen_file.name}' aún no contiene eventos.")
            return
        
        print(f"📜 [TDM Logs - {target.upper()}] ({chosen_file}):")
        if follow:
            proc = await asyncio.create_subprocess_exec("tail", "-n", str(lines_count), "-f", str(chosen_file))
            try:
                await proc.wait()
            except KeyboardInterrupt:
                proc.terminate()
        else:
            with open(chosen_file, "r", errors="ignore") as f:
                content = f.readlines()
                for line in content[-lines_count:]:
                    print(line, end="")
    else:
        print("📜 ==================== [TDM LOGS RESUMEN] ====================")
        for name, path in log_files.items():
            print(f"\n🔹 --- [{name.upper()} LOGS] ({path.name}) ---")
            if path.exists() and path.stat().st_size > 0:
                with open(path, "r", errors="ignore") as f:
                    content = f.readlines()
                    last_lines = content[-15:]
                    if last_lines:
                        for l in last_lines:
                            print("  " + l, end="")
                    else:
                        print("  (Archivo vacío)")
            else:
                print("  (Sin registros aún)")
        print("\n💡 Opciones:")
        print("  • tdm logs -a -f   -> Seguir logs del agente en tiempo real")
        print("  • tdm logs -s      -> Ver logs del servidor HTTP")
        print("  • tdm logs -d      -> Ver logs de la sesión gráfica X11")
        print("  • tdm logs --clear -> Limpiar todos los registros")

async def handle_update(args):
    """Descarga e instala la última versión del backend de TDM desde el Hub central."""
    import urllib.request
    import tarfile
    import tempfile
    from tdm.version import __version__
    from tdm.config import HOME, PREFIX

    hub_url = getattr(args, "hub", None)
    if not hub_url:
        cfg_file = HOME / ".tdm" / "config" / "agent.json"
        if cfg_file.exists():
            try:
                cfg = json.loads(cfg_file.read_text())
                hub_url = cfg.get("hub")
            except Exception:
                pass
    if not hub_url:
        hub_url = "https://tdm.oton.cl"

    hub_url = hub_url.rstrip("/")
    bundle_url = f"{hub_url}/tdm-bundle.tar.gz"

    print("=====================================================")
    print(f"🔄 [TDM Update] Actualizando Backend (Versión actual: v{__version__})")
    print(f"🌐 Servidor de origen: {hub_url}")
    print("=====================================================")

    print(f"⬇️  Descargando paquete de actualización...")
    try:
        req = urllib.request.Request(
            bundle_url,
            headers={"User-Agent": f"TDM-Updater/{__version__}"}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status != 200:
                print(f"❌ Error al descargar actualización: Código HTTP {response.status}")
                return
            data = response.read()
            print(f"📦 Paquete descargado con éxito ({len(data) // 1024} KB).")
    except Exception as e:
        print(f"❌ No se pudo conectar al servidor de actualización: {e}")
        return

    # Extraer paquete
    print("🛠️  Aplicando actualización en el sistema...")
    target_dir = HOME / "termux-display-manager"
    target_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        with tarfile.open(tmp_path, "r:gz") as tar:
            tar.extractall(path=target_dir)
        print("✓ Archivos del núcleo TDM actualizados correctamente.")
    except Exception as e:
        print(f"❌ Error al descomprimir actualización: {e}")
        return
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

    # Leer nueva versión
    try:
        sys.path.insert(0, str(target_dir))
        import importlib
        import tdm.version
        importlib.reload(tdm.version)
        new_ver = tdm.version.__version__
    except Exception:
        new_ver = "actualizada"

    print(f"🎉 ¡TDM Backend actualizado con éxito a v{new_ver}!")

    # Reiniciar servicios en segundo plano si estaban activos
    if getattr(args, "restart", True):
        print("🔄 Reiniciando servicios en segundo plano...")
        await handle_service("stop")
        await asyncio.sleep(1)
        await handle_service("start")

    print("=====================================================")
    print("✅ Actualización completada y operativa.")
    print("=====================================================")

async def handle_agy(args):
    """Gestiona el terminal dinámico multidispositivo con agy y tmux."""
    script = Path(__file__).resolve().parent.parent.parent / "scripts" / "agy-dynamic-terminal.sh"
    if not script.exists():
        print(f"❌ Error: Script {script} no encontrado.")
        return
    cmd = [str(script)]
    if getattr(args, "agy_command", None):
        cmd.append(args.agy_command)
    if getattr(args, "extra", None):
        cmd.extend(args.extra)
    subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(prog="tdm", description="Termux Display Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # tdm status
    subparsers.add_parser("status", help="Muestra el estado de la pantalla y el entorno activo")

    # tdm logs
    logs_parser = subparsers.add_parser("logs", help="Muestra los registros y eventos de TDM")
    logs_parser.add_argument("-a", "--agent", action="store_true", help="Muestra registros del agente WebSocket")
    logs_parser.add_argument("-s", "--server", action="store_true", help="Muestra registros del servidor HTTP/Web")
    logs_parser.add_argument("-d", "--session", action="store_true", help="Muestra registros de la sesión gráfica de escritorio")
    logs_parser.add_argument("-f", "--follow", action="store_true", help="Sigue los registros en vivo en tiempo real")
    logs_parser.add_argument("-n", "--lines", type=int, default=50, help="Cantidad de líneas a mostrar (por defecto 50)")
    logs_parser.add_argument("--clear", action="store_true", help="Limpia todos los archivos de registros")

    # tdm update
    update_parser = subparsers.add_parser("update", help="Descarga e instala la última versión del backend de TDM")
    update_parser.add_argument("--hub", "-H", help="URL del servidor Hub de actualización")
    update_parser.add_argument("--no-restart", dest="restart", action="store_false", help="No reiniciar servicios tras actualizar")

    # tdm start
    start_parser = subparsers.add_parser("start", help="Inicia o conmuta la salida de pantalla")
    start_parser.add_argument("--backend", "-b", choices=["termux-x11", "novnc", "rdp", "vnc"], default=BACKEND_TERMUX_X11, help="Servidor de pantalla")
    start_parser.add_argument("--mode", "-m", choices=[SESSION_MODE_DESKTOP, SESSION_MODE_TERMINAL], default=SESSION_MODE_DESKTOP, help="Modo de sesión")
    start_parser.add_argument("--resolution", "-r", default=DEFAULT_RESOLUTION, help="Resolución (ej: 1920x1080)")
    start_parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="Densidad DPI (ej: 96, 120)")
    start_parser.add_argument("--no-audio", action="store_true", help="Desactiva PulseAudio")
    start_parser.add_argument("--no-virgl", action="store_true", help="Desactiva VirGL 3D")

    # tdm stop
    subparsers.add_parser("stop", help="Detiene la pantalla activa")

    # tdm doctor
    subparsers.add_parser("doctor", help="Verifica paquetes y dependencias instaladas")

    # tdm server / web
    server_parser = subparsers.add_parser("server", help="Inicia el servidor HTTP API y Panel Web/PWA")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host de escucha")
    server_parser.add_argument("--port", "-p", type=int, default=PORT_TDM_SERVER, help="Puerto de escucha")

    # alias tdm web
    web_parser = subparsers.add_parser("web", help="Inicia el servidor Web Dashboard")
    web_parser.add_argument("--host", default="0.0.0.0", help="Host de escucha")
    web_parser.add_argument("--port", "-p", type=int, default=PORT_TDM_SERVER, help="Puerto de escucha")

    # tdm hub (Servidor Central Relay en dominio ej: tdm.oton.cl)
    hub_parser = subparsers.add_parser("hub", help="Inicia el Hub Central para conectar Termux de forma remota")
    hub_parser.add_argument("--host", default="0.0.0.0", help="Host de escucha")
    hub_parser.add_argument("--port", "-p", type=int, default=PORT_TDM_SERVER, help="Puerto de escucha")

    # tdm agent (Ejecutado en Termux para conectarse a un Hub remoto)
    agent_parser = subparsers.add_parser("agent", help="Inicia el agente en Termux y se conecta a un Hub remoto")
    agent_parser.add_argument("--hub", "-H", required=True, help="URL del servidor Hub (ej. https://tdm.oton.cl)")
    agent_parser.add_argument("--token", "-t", required=True, help="Token de emparejamiento")

    # tdm install
    install_parser = subparsers.add_parser("install", help="Ejecuta instaladores del backend bajo demanda")
    install_parser.add_argument("--minimal", "-m", action="store_true", help="Instala solo dependencias mínimas fundamentales")
    install_parser.add_argument("--dependencies", "-d", action="store_true", help="Alias de --minimal")
    install_parser.add_argument("--server", "-s", choices=["termux-x11", "novnc", "vnc", "rdp", "audio"], help="Instala un servidor gráfico específico")
    install_parser.add_argument("--desktop", choices=["kde", "mate", "xfce", "lxqt", "i3", "openbox"], help="Instala un escritorio específico")
    install_parser.add_argument("--full", "-f", action="store_true", help="Instala todos los servidores y utilidades")

    # tdm service [start|stop|restart|status|enable|disable]
    service_parser = subparsers.add_parser("service", help="Gestiona los servicios de TDM con el Gestor de Servicios de Termux (termux-services / sv)")
    service_parser.add_argument("action", choices=["start", "stop", "restart", "status", "enable", "disable"], default="status", nargs="?", help="Acción a realizar")

    # tdm agy [start|attach|web|qr|status|stop]
    agy_parser = subparsers.add_parser("agy", help="Terminal dinámico multidispositivo con agy y tmux")
    agy_parser.add_argument("agy_command", nargs="?", default="", help="Subcomando agy (start, attach, web, qr, status, stop, send)")
    agy_parser.add_argument("extra", nargs=argparse.REMAINDER, help="Argumentos adicionales")

    # tdm uninstall
    subparsers.add_parser("uninstall", help="Desinstala TDM y limpia selectivamente solo lo instalado mediante TDM")

    # tdm version
    subparsers.add_parser("version", help="Muestra la versión de TDM y esquema de manifest")

    parser.add_argument("--version", "-v", action="store_true", help="Muestra la versión de TDM")

    args = parser.parse_args()

    if getattr(args, "version", False) or args.command == "version":
        from tdm.version import get_version_info
        info = get_version_info()
        print(f"Termux Display Manager (TDM) v{info['version']} (code: {info['version_code']}, schema: {info['manifest_schema']})")
        sys.exit(0)

    if not args.command:
        print_banner()
        parser.print_help()
        sys.exit(0)

    if args.command == "status":
        asyncio.run(handle_status())
    elif args.command == "agy":
        asyncio.run(handle_agy(args))
    elif args.command == "logs":
        asyncio.run(handle_logs(args))
    elif args.command == "update":
        asyncio.run(handle_update(args))
    elif args.command == "service":
        asyncio.run(handle_service(args.action))
    elif args.command == "start":
        asyncio.run(handle_start(args))
    elif args.command == "stop":
        asyncio.run(handle_stop())
    elif args.command == "doctor":
        asyncio.run(handle_doctor())
    elif args.command in ["server", "web"]:
        asyncio.run(handle_server(args, is_hub=False))
    elif args.command == "hub":
        asyncio.run(handle_server(args, is_hub=True))
    elif args.command == "agent":
        asyncio.run(handle_agent(args))
    elif args.command == "install":
        asyncio.run(handle_install(args))
    elif args.command == "uninstall":
        from tdm.core.uninstaller import uninstaller_service
        asyncio.run(uninstaller_service.perform_uninstall(purge_packages=True))

if __name__ == "__main__":
    main()
