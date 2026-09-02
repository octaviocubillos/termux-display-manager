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
from typing import Dict, Any, Optional

from tdm import __version__
from tdm.core.display_manager import display_manager
from tdm.core.installer import installer_service
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

async def handle_status(args=None):
    status = display_manager.get_status()
    if args and getattr(args, "json", False):
        import json
        print(json.dumps(status, indent=2))
        return status

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
    return status

async def handle_start(args):
    backend = getattr(args, "backend", BACKEND_TERMUX_X11)
    mode = getattr(args, "mode", SESSION_MODE_DESKTOP)
    desktop = getattr(args, "desktop", None)
    resolution = getattr(args, "resolution", DEFAULT_RESOLUTION)
    dpi = getattr(args, "dpi", DEFAULT_DPI)
    audio = not getattr(args, "no_audio", False)
    virgl = not getattr(args, "no_virgl", True)

    print(f"🚀 [TDM] Iniciando pantalla en backend '{backend}'...")
    result = await display_manager.start_screen(
        backend=backend,
        mode=mode,
        desktop_id=desktop,
        resolution=resolution,
        dpi=dpi,
        audio=audio,
        virgl=virgl
    )
    if result.get("status") == "running":
        print(f"✅ Pantalla iniciada con éxito en {backend} (:0)")
        if result.get("urls"):
            for k, v in result["urls"].items():
                print(f"   {k}: {v}")
    else:
        print(f"❌ Error iniciando pantalla: {result.get('error_message')}")
    return result

async def handle_stop():
    print("🛑 [TDM] Deteniendo pantalla activa...")
    stopped = await display_manager.stop_screen()
    print("✅ Pantalla detenida y sockets X11 liberados.")
    return stopped

async def handle_novnc(args):
    action = getattr(args, "action", None) or "start"

    if action == "status":
        info = display_manager.get_novnc_info()
        print("=====================================================")
        print("🌐 [TDM noVNC] Estado del Servidor Web HTML5 / RFB")
        print("=====================================================")
        if info["is_running"]:
            sess = info["active_session"] or {}
            print(f"🟢 Estado: ACTIVO (Sesión :0 en ejecución)")
            print(f"  • Entorno:        {sess.get('desktop_id', 'N/A')}")
            print(f"  • Resolución:     {sess.get('resolution', 'N/A')}")
            print(f"  • Puerto VNC RFB: {info['port_rfb']}")
            print(f"  • Puerto Web:     {info['port_web']}")
            print(f"  • PID Servidor:   #{sess.get('server_pid')}")
            print(f"  • URL Directa:    {info['urls']['direct']}")
        else:
            print("🔴 Estado: INACTIVO (El backend activo no es noVNC o la pantalla está apagada)")
            print("\n📌 URLs preparadas para cuando se inicie:")
            print(f"  • Local:   {info['urls']['local']}")
            if info['urls']['lan'] != info['urls']['local']:
                print(f"  • Red LAN: {info['urls']['lan']}")
        print("=====================================================")
        return

    elif action == "stop":
        print("🛑 [TDM noVNC] Deteniendo sesión gráfica...")
        await display_manager.stop_screen()
        print("✅ Sesión noVNC detenida correctamente.")
        return

    elif action == "url":
        info = display_manager.get_novnc_info()
        print(info["urls"]["direct"])
        return

    elif action in ["start", "open"]:
        print(f"🚀 [TDM noVNC] Iniciando entorno gráfico con salida Web HTML5 (noVNC)...")
        result = await display_manager.start_screen(
            backend="novnc",
            mode=getattr(args, "mode", "desktop"),
            desktop_id=getattr(args, "desktop", None),
            resolution=getattr(args, "resolution", DEFAULT_RESOLUTION),
            dpi=getattr(args, "dpi", DEFAULT_DPI),
            audio=not getattr(args, "no_audio", False),
            virgl=not getattr(args, "no_virgl", False)
        )
        if result.get("status") == "running":
            info = display_manager.get_novnc_info()
            print("=====================================================")
            print("🎉 [TDM noVNC] ¡Sesión HTML5 iniciada con éxito!")
            print("=====================================================")
            print(f"🖥️  Entorno:     {result.get('desktop_id')}")
            print(f"📐 Resolución:  {result.get('resolution')} (DPI {result.get('dpi')})")
            print(f"🔌 Puerto RFB:  {info['port_rfb']} (TigerVNC / Xvnc)")
            print(f"🌐 Puerto Web:  {info['port_web']} (Servidor HTTP + WebSocket Bridge)")
            print("\n🔗 URLs de Acceso Directo al Escritorio:")
            print(f"  • Local (este dispositivo): {info['urls']['local']}")
            if info['urls']['lan'] != info['urls']['local']:
                print(f"  • Red LAN (otros disp.):    {info['urls']['lan']}")
            if info['urls']['tailscale']:
                print(f"  • Tailscale (remoto):      {info['urls']['tailscale']}")
            print("=====================================================")

            if action == "open" or getattr(args, "open_browser", False):
                for opener in ["termux-open-url", "xdg-open"]:
                    if shutil.which(opener):
                        try:
                            subprocess.Popen([opener, info['urls']['local']])
                            print(f"🌐 Navegador abierto con {opener}")
                            break
                        except Exception:
                            pass
        else:
            print(f"❌ Error al iniciar noVNC: {result.get('error_message')}")

def handle_permissions():
    print("=====================================================")
    print("📱 [TDM] Permisos de Android para Termux y Termux:X11")
    print("=====================================================")
    if not os.path.exists("/data/data/com.termux"):
        print("ℹ️  No se detectó un entorno Android/Termux nativo.")
        return

    print("ℹ️  Para que la app gráfica Termux:X11 se abra automáticamente al iniciar,")
    print("   Android requiere el permiso 'Mostrar sobre otras aplicaciones'.")
    print("🚀 Abriendo pantalla de configuración de permisos en tu dispositivo...")

    subprocess.run(["am", "start", "-a", "android.settings.action.MANAGE_OVERLAY_PERMISSION", "-d", "package:com.termux"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    res = subprocess.run(["pm", "list", "packages"], capture_output=True, text=True)
    if "com.termux.x11" in res.stdout:
        subprocess.run(["am", "start", "-a", "android.settings.action.MANAGE_OVERLAY_PERMISSION", "-d", "package:com.termux.x11"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("\n✅ Pantalla de permisos solicitada en tu móvil.")
    print("💡 En MIUI / HyperOS (Xiaomi / Poco): Ve a Ajustes > Apps > Administrar Apps > Termux > Otros Permisos y activa 'Mostrar ventanas emergentes en segundo plano'.")

def handle_desktop(args=None):
    de = display_manager.get_installed_desktop()
    if getattr(args, "json", False):
        import json
        print(json.dumps(de, indent=2))
        return

    if de.get("installed"):
        print("=====================================================")
        print(f"🎨 Entorno de Escritorio Instalado: {de['name']}")
        print(f"📁 Binario Ejecutable: {de['executable']}")
        print(f"🆔 Identificador (ID): {de['id']}")
        print(f"📦 Paquetes Base: {', '.join(de.get('packages', []))}")
        print("=====================================================")
    else:
        print("=====================================================")
        print("ℹ️  No se detectó ningún entorno de escritorio instalado.")
        print("💡 Puedes instalar uno con: tdm install --desktop [xfce|i3|kde|mate|lxqt|openbox]")
        print("   O desde el panel web: http://localhost:19050")
        print("=====================================================")

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
    from tdm.server.http_server import AsyncHTTPServer
    server = AsyncHTTPServer(host=args.host, port=args.port, is_hub=is_hub)
    await server.start()

async def handle_agent(args):
    from tdm.agent.client import TDMAgent
    agent = TDMAgent(hub_url=args.hub, token=args.token)
    await agent.run()

async def handle_install(args):
    if getattr(args, "driver_3d", False) or getattr(args, "gpu", False):
        print("🎮 [TDM] Detectando GPU y configurando controlador 3D...")
        success = await installer_service.run_script("setup_3d.sh")
        print("✅ Controlador 3D listo." if success else "❌ Error configurando controlador 3D.")
    elif getattr(args, "minimal", False) or getattr(args, "dependencies", False) or getattr(args, "full", False):
        print("⚡ [TDM] Instalando dependencias y servidores gráficos...")
        success = await installer_service.run_script("install_server.sh", ["all"])
        print("✅ Dependencias listas." if success else "❌ Error instalando dependencias.")
    elif getattr(args, "server", None):
        print(f"🖥️ [TDM] Instalando servidor gráfico '{args.server}' bajo demanda...")
        success = await installer_service.run_script("install_server.sh", [args.server])
        print(f"✅ Servidor {args.server} instalado con éxito." if success else f"❌ Error instalando servidor {args.server}.")
    elif getattr(args, "desktop", None):
        print(f"🎨 [TDM] Instalando entorno de escritorio '{args.desktop}' bajo demanda...")
        success = await installer_service.install_desktop(args.desktop)
        print(f"✅ {args.desktop} instalado con éxito." if success else f"❌ Error instalando {args.desktop}.")

async def handle_uninstall(args):
    desktop = getattr(args, "desktop", None)
    if desktop:
        print(f"🗑️ [TDM] Desinstalando entorno de escritorio '{desktop}'...")
        success = await installer_service.uninstall_desktop(desktop)
        if success:
            print(f"✅ Entorno '{desktop}' desinstalado y almacenamiento liberado al 100%.")
        else:
            print(f"❌ Error desinstalando entorno '{desktop}'.")
    else:
        from tdm.core.uninstaller import uninstaller_service
        purge = getattr(args, "purge", True)
        await uninstaller_service.perform_uninstall(purge_packages=purge)

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
    """Descarga e instala la última versión del backend de TDM desde el Hub central o GitHub."""
    from tdm.core.updater import perform_update
    from tdm.version import __version__

    hub_url = getattr(args, "hub", None)
    result = await perform_update(hub_url=hub_url)

    if not result.get("success"):
        print(f"❌ Error al actualizar: {result.get('error')}")
        return

    new_ver = result.get("new_version", __version__)

    # Reiniciar servicios en segundo plano si estaban activos
    restart = getattr(args, "restart", True)
    if restart:
        print("🔄 Reiniciando servicios de TDM...")
        try:
            await handle_service("restart")
        except Exception:
            pass

    print("=====================================================")
    print(f"✅ TDM actualizado y operativo en versión v{new_ver}.")
    print("=====================================================")

async def handle_3d(args):
    from tdm.core.gpu_manager import gpu_manager
    info = gpu_manager.get_gpu_info()
    if getattr(args, "json", False):
        import json
        print(json.dumps(info, indent=2))
        return
    print("=====================================================")
    print("🎮 [TDM] Estado del Controlador 3D y GPU")
    print("=====================================================")
    print(f"  • GPU Detectada: {info.get('gpu_model', 'N/A')} ({info.get('gpu_vendor', 'N/A')})")
    print(f"  • Controlador:   {info.get('driver_name', 'N/A')}")
    print(f"  • Estado:        {'✅ Instalado' if info.get('installed') else '❌ No instalado'}")
    print(f"  • VirGL 3D:      {'✅ Compatible' if info.get('virgl_supported') else '❌ No compatible'}")
    print("=====================================================")
    if getattr(args, "install", False):
        print("📦 Configurando controlador 3D...")
        await installer_service.run_script("setup_3d.sh", ["--force"] if getattr(args, "force", False) else [])

def handle_battery(args):
    from tdm.core.device_manager import device_manager
    bat = device_manager.get_battery_status()
    if getattr(args, "json", False):
        import json
        print(json.dumps(bat, indent=2))
        return bat
    icon = "⚡" if bat.get("is_charging") else "🔋"
    print(f"{icon} Batería: {bat.get('percentage')}% • Estado: {bat.get('status')} • Salud: {bat.get('health')} • Temp: {bat.get('temperature')}°C ({bat.get('plugged')})")
    return bat

def handle_volume(args):
    from tdm.core.device_manager import device_manager
    level = getattr(args, "level", None)
    stream = getattr(args, "stream", "music") or "music"
    if level is not None:
        res = device_manager.set_volume(level, stream)
        print(f"🔊 Volumen '{stream}' fijado al {level}%")
        return res
    info = device_manager.get_volume_info()
    if getattr(args, "json", False):
        import json
        print(json.dumps(info, indent=2))
        return info
    print(f"🔊 Volumen Multimedia: {info.get('music_percent')}% ({info.get('music_volume')}/{info.get('music_max')})")
    return info

def handle_brightness(args):
    from tdm.core.device_manager import device_manager
    level = getattr(args, "level", None)
    if level is not None:
        res = device_manager.set_brightness(level)
        print(f"☀️ Brillo fijado a {level}/255" if res.get("success") else f"❌ Error: {res.get('error')}")
        return res
    print("Uso: tdm brightness <0-255>")
    return {"success": False}

def handle_device(args):
    from tdm.core.device_manager import device_manager
    dev = device_manager.get_full_device_info()
    if getattr(args, "json", False):
        import json
        print(json.dumps(dev, indent=2))
        return dev
    bat = dev.get("battery", {})
    vol = dev.get("volume", {})
    api = dev.get("api", {})
    print("=====================================================")
    print("📱 [TDM] Estado del Dispositivo Físico")
    print("=====================================================")
    print(f"  • Batería:    {bat.get('percentage')}% ({bat.get('status')}, {bat.get('temperature')}°C)")
    print(f"  • Volumen:    {vol.get('music_percent')}% (multimedia)")
    print(f"  • Termux:API: {'✅ Listo' if api.get('ready') else '⚠️ Instalar con: pkg install termux-api'}")
    print("=====================================================")
    return dev

async def handle_cancel_install():
    print("🛑 [TDM] Cancelando instalación y revirtiendo paquetes...")
    res = await installer_service.cancel_and_revert()
    print("✅ Cancelación y reversión finalizada.")
    return res

def build_cli_parser():
    parser = argparse.ArgumentParser(prog="tdm", description="Termux Display Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # tdm status
    status_parser = subparsers.add_parser("status", help="Muestra el estado de la pantalla y el entorno activo")
    status_parser.add_argument("--json", "-j", action="store_true", help="Salida en formato JSON")

    # tdm 3d / gpu
    gpu_parser = subparsers.add_parser("3d", aliases=["gpu"], help="Muestra y gestiona el controlador 3D de la GPU")
    gpu_parser.add_argument("--json", "-j", action="store_true", help="Salida en formato JSON")
    gpu_parser.add_argument("--install", "-i", action="store_true", help="Instala el controlador 3D para la GPU detectada")
    gpu_parser.add_argument("--force", "-f", action="store_true", help="Fuerza la reinstalación")

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
    start_parser.add_argument("--desktop", "-d", help="Entorno de escritorio (ej: i3, openbox, xfce, mate, lxqt, kde)")
    start_parser.add_argument("--mode", "-m", choices=[SESSION_MODE_DESKTOP, SESSION_MODE_TERMINAL], default=SESSION_MODE_DESKTOP, help="Modo de sesión")
    start_parser.add_argument("--resolution", "-r", default=DEFAULT_RESOLUTION, help="Resolución (ej: 1920x1080)")
    start_parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="Densidad DPI (ej: 96, 120)")
    start_parser.add_argument("--no-audio", action="store_true", help="Desactiva PulseAudio")
    start_parser.add_argument("--no-virgl", action="store_true", help="Desactiva VirGL 3D")

    # tdm novnc [start|stop|status|url|open]
    novnc_parser = subparsers.add_parser("novnc", aliases=["vnc-web", "webvnc"], help="Inicia, detiene o consulta el servidor Web HTML5 noVNC")
    novnc_parser.add_argument("action", choices=["start", "stop", "status", "url", "open"], default="start", nargs="?", help="Acción a realizar")
    novnc_parser.add_argument("--desktop", "-d", help="Entorno de escritorio (ej: kde, xfce, mate, lxqt, i3, openbox)")
    novnc_parser.add_argument("--mode", "-m", choices=[SESSION_MODE_DESKTOP, SESSION_MODE_TERMINAL], default=SESSION_MODE_DESKTOP, help="Modo de sesión")
    novnc_parser.add_argument("--resolution", "-r", default=DEFAULT_RESOLUTION, help="Resolución (ej: 1920x1080)")
    novnc_parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="Densidad DPI (ej: 96, 120)")
    novnc_parser.add_argument("--open", "-o", dest="open_browser", action="store_true", help="Abre automáticamente el navegador")
    novnc_parser.add_argument("--no-audio", action="store_true", help="Desactiva PulseAudio")
    novnc_parser.add_argument("--no-virgl", action="store_true", help="Desactiva VirGL 3D")

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

    # tdm hub
    hub_parser = subparsers.add_parser("hub", help="Inicia el Hub Central para conectar Termux de forma remota")
    hub_parser.add_argument("--host", default="0.0.0.0", help="Host de escucha")
    hub_parser.add_argument("--port", "-p", type=int, default=PORT_TDM_SERVER, help="Puerto de escucha")

    # tdm agent
    agent_parser = subparsers.add_parser("agent", help="Inicia el agente en Termux y se conecta a un Hub remoto")
    agent_parser.add_argument("--hub", "-H", required=True, help="URL del servidor Hub (ej. https://tdm.oton.cl)")
    agent_parser.add_argument("--token", "-t", required=True, help="Token de emparejamiento")

    # tdm device
    dev_parser = subparsers.add_parser("device", help="Muestra el estado del dispositivo físico (batería, volumen, Termux-API)")
    dev_parser.add_argument("--json", "-j", action="store_true", help="Salida en formato JSON")

    # tdm battery
    bat_parser = subparsers.add_parser("battery", aliases=["bat"], help="Muestra el estado de la batería del dispositivo")
    bat_parser.add_argument("--json", "-j", action="store_true", help="Salida en formato JSON")

    # tdm volume [level]
    vol_parser = subparsers.add_parser("volume", aliases=["vol"], help="Consulta o ajusta el volumen del teléfono")
    vol_parser.add_argument("level", nargs="?", type=int, help="Nivel de volumen en porcentaje (0-100)")
    vol_parser.add_argument("--stream", "-s", choices=["music", "ring", "notification", "alarm", "call", "system"], default="music", help="Canal de audio (por defecto 'music')")
    vol_parser.add_argument("--json", "-j", action="store_true", help="Salida en formato JSON")

    # tdm brightness [level]
    bright_parser = subparsers.add_parser("brightness", help="Ajusta el brillo de la pantalla (0-255)")
    bright_parser.add_argument("level", nargs="?", type=int, help="Nivel de brillo (0-255)")

    # tdm install
    install_parser = subparsers.add_parser("install", help="Ejecuta instaladores del backend bajo demanda")
    install_parser.add_argument("--minimal", "-m", action="store_true", help="Instala solo dependencias mínimas fundamentales")
    install_parser.add_argument("--dependencies", "-d", action="store_true", help="Alias de --minimal")
    install_parser.add_argument("--server", "-s", choices=["termux-x11", "novnc", "vnc", "rdp", "audio"], help="Instala un servidor gráfico específico")
    install_parser.add_argument("--desktop", choices=["kde", "mate", "xfce", "lxqt", "i3", "openbox"], help="Instala un escritorio específico")
    install_parser.add_argument("--driver-3d", "--3d", "--gpu", dest="driver_3d", action="store_true", help="Instala el controlador de aceleración 3D para la GPU detectada")
    install_parser.add_argument("--api", action="store_true", help="Instala el paquete termux-api")
    install_parser.add_argument("--full", "-f", action="store_true", help="Instala todos los servidores y utilidades")
    install_parser.add_argument("--cancel", "-c", action="store_true", help="Cancela y revierte la instalación en curso")

    # tdm cancel-install
    subparsers.add_parser("cancel-install", help="Cancela y revierte la instalación en curso")

    # tdm service [start|stop|restart|status|enable|disable]
    service_parser = subparsers.add_parser("service", help="Gestiona los servicios de TDM con el Gestor de Servicios de Termux (termux-services / sv)")
    service_parser.add_argument("action", choices=["start", "stop", "restart", "status", "enable", "disable"], default="status", nargs="?", help="Acción a realizar")

    # tdm uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Desinstala un entorno o TDM completo")
    uninstall_parser.add_argument("--desktop", "-d", choices=["kde", "mate", "xfce", "lxqt", "i3", "openbox", "all"], help="Desinstala un entorno de escritorio específico (o 'all' para todos)")
    uninstall_parser.add_argument("--purge", action="store_true", default=True, help="Purga paquetes al desinstalar TDM")

    # tdm desktop / env / de
    desktop_parser = subparsers.add_parser("desktop", aliases=["env", "de"], help="Muestra el entorno de escritorio instalado y su binario ejecutable")
    desktop_parser.add_argument("--json", "-j", action="store_true", help="Salida en formato JSON")

    # tdm permissions / perms
    subparsers.add_parser("permissions", aliases=["perms"], help="Solicita en pantalla los permisos de Android para abrir X11 automáticamente")

    # tdm version
    subparsers.add_parser("version", help="Muestra la versión de TDM y esquema de manifest")
    parser.add_argument("--version", "-v", action="store_true", help="Muestra la versión de TDM")

    return parser

async def execute_cli_command(cmd_args: list) -> Dict[str, Any]:
    """
    Despachador central de comandos CLI para ejecución unificada (Web / API / RPC).
    Toda acción web se ejecuta invocando este despachador CLI.
    """
    parser = build_cli_parser()
    try:
        args = parser.parse_args(cmd_args)
    except SystemExit:
        return {"success": False, "error": f"Argumentos CLI inválidos: {' '.join(cmd_args)}"}

    if getattr(args, "version", False) or args.command == "version":
        info = get_version_info()
        return {"success": True, "data": info}
    elif args.command in ["desktop", "env", "de"]:
        de = display_manager.get_installed_desktop()
        return {"success": True, "data": de}
    elif args.command in ["3d", "gpu"]:
        from tdm.core.gpu_manager import gpu_manager
        if getattr(args, "install", False):
            res = await installer_service.run_script("setup_3d.sh", ["--force"] if getattr(args, "force", False) else [])
            return {"success": res, "data": gpu_manager.get_gpu_info()}
        return {"success": True, "data": gpu_manager.get_gpu_info()}
    elif args.command == "status":
        st = display_manager.get_status()
        return {"success": True, "data": st}
    elif args.command in ["permissions", "perms"]:
        handle_permissions()
        return {"success": True, "message": "Permisos solicitados en Android"}
    elif args.command == "start":
        res = await handle_start(args)
        return {"success": res.get("status") == "running", "data": res}
    elif args.command in ["novnc", "vnc-web", "webvnc"]:
        res = await handle_novnc(args)
        return {"success": True, "data": res}
    elif args.command == "stop":
        stopped = await display_manager.stop_screen()
        return {"success": True, "stopped": stopped}
    elif args.command == "install":
        if getattr(args, "cancel", False):
            res = await handle_cancel_install()
            return {"success": True, "data": res}
        res = await handle_install(args)
        return {"success": res}
    elif args.command == "cancel-install":
        res = await handle_cancel_install()
        return {"success": True, "data": res}
    elif args.command == "uninstall":
        res = await handle_uninstall(args)
        return {"success": res}
    elif args.command == "update":
        res = await handle_update(args)
        return {"success": True, "data": res}
    elif args.command == "service":
        await handle_service(args.action)
        return {"success": True, "action": args.action}
    elif args.command in ["device"]:
        res = handle_device(args)
        return {"success": True, "data": res}
    elif args.command in ["battery", "bat"]:
        res = handle_battery(args)
        return {"success": True, "data": res}
    elif args.command in ["volume", "vol"]:
        res = handle_volume(args)
        return {"success": True, "data": res}
    elif args.command in ["brightness"]:
        res = handle_brightness(args)
        return {"success": True, "data": res}
    elif args.command == "doctor":
        await handle_doctor()
        return {"success": True}
    else:
        return {"success": False, "error": f"Comando CLI desconocido: {args.command}"}

def main():
    parser = build_cli_parser()
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

    if args.command in ["desktop", "env", "de"]:
        handle_desktop(args)
    elif args.command in ["3d", "gpu"]:
        asyncio.run(handle_3d(args))
    elif args.command == "device":
        handle_device(args)
    elif args.command in ["battery", "bat"]:
        handle_battery(args)
    elif args.command in ["volume", "vol"]:
        handle_volume(args)
    elif args.command == "brightness":
        handle_brightness(args)
    elif args.command == "status":
        asyncio.run(handle_status(args))
    elif args.command == "permissions" or args.command == "perms":
        handle_permissions()
    elif args.command == "logs":
        asyncio.run(handle_logs(args))
    elif args.command == "update":
        asyncio.run(handle_update(args))
    elif args.command == "service":
        asyncio.run(handle_service(args.action))
    elif args.command == "start":
        asyncio.run(handle_start(args))
    elif args.command in ["novnc", "vnc-web", "webvnc"]:
        asyncio.run(handle_novnc(args))
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
        if getattr(args, "cancel", False):
            asyncio.run(handle_cancel_install())
        else:
            asyncio.run(handle_install(args))
    elif args.command == "cancel-install":
        asyncio.run(handle_cancel_install())
    elif args.command == "uninstall":
        asyncio.run(handle_uninstall(args))

if __name__ == "__main__":
    main()
