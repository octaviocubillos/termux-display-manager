# 🧠 Memoria de Arquitectura y Especificación Técnica — TDM

> **Termux Display Manager (TDM)**
> Motor unificado de entornos gráficos nativos, servidor REST asíncrono, WebSockets locales y PWA para Android/Termux y Linux.
> **Versión**: `v0.0.13` | **Puertos**: `19050 - 19055` | **Licencia**: MIT

---

## 📑 1. Resumen Ejecutivo y Misión del Proyecto

TDM transforma cualquier dispositivo Android con Termux en una estación de trabajo gráfica fluida (60/120 Hz) o en un servidor de escritorio accesible localmente (o vía LAN/Tailscale) mediante HTML5, VNC o RDP.

El sistema elimina la complejidad de configurar scripts dispersos, gestionar sockets X11 huérfanos o lidiar con procesos zombies que agotan la batería, ofreciendo una experiencia 100% local controlable tanto por CLI como desde una Progressive Web App (PWA) minimalista inspirada en Material Design 3.

```
+-------------------------------------------------------------------------------+
|                             CLIENTES & CONTROL                                |
|   +------------------------------------+  +-------------------------------+   |
|   |    PWA / Web Dashboard (Local)     |  |          CLI Terminal         |   |
|   |  (Canvas Único, Material You MD3)  |  | (tdm start, status, update...) |   |
|   +-----------------+------------------+  +---------------+---------------+   |
+---------------------|-------------------------------------|-------------------+
                      | REST API / WebSocket Local (/ws)    | Local IPC
                      v                                     v
+-------------------------------------------------------------------------------+
|                           TDM CORE SERVER & ENGINE                            |
|   +-----------------------------------------------------------------------+   |
|   |                       Async HTTP & WebSocket Server                   |   |
|   |                  (REST API, Static PWA, Streaming Logs)               |   |
|   +-----------------------------------+-----------------------------------+   |
|                                       |
|                                       v
|   +-----------------------------------------------------------------------+   |
|   |                       Display & Process Manager                       |   |
|   |        (Single Display Controller :0, Purga /proc, Signal 9)          |   |
|   +-----------------------------------+-----------------------------------+   |
|                                       |
|         +-----------------------------+-----------------------------+         |
|         |                             |                             |         |
|         v                             v                             v         |
|   +-------------+               +-------------+               +-----------+   |
|   | Termux:X11  |               |    noVNC    |               |  TigerVNC |   |
|   | (Display :0)|               | (WebSockets)|               |  & XRDP   |   |
|   +------+------+               +------+------+               +-----+-----+   |
|          |                             |                            |         |
+----------|-----------------------------|----------------------------|---------+
           v                             v                            v
+-------------------------------------------------------------------------------+
|                              ENTORNOS GRÁFICOS                                |
|            XFCE4  •  KDE Plasma  •  MATE  •  LXQt  •  i3 WM  •  Openbox       |
+-------------------------------------------------------------------------------+
```

---

## 🔌 2. Matriz de Puertos y Servicios (Rango `1905x`)

Todos los servicios y protocolos de comunicación operan en el bloque `19050 - 19055`:

| Puerto | Protocolo | Servicio / Componente | Descripción |
| :--- | :---: | :--- | :--- |
| **`19050`** | `HTTP / WSS` | **TDM Hub & Web API** | Panel Web PWA, API REST y Router de WebSockets. |
| **`19051`** | `HTTP` | **TDM Server Secundario** | Puerto alternativo configurable para APIs secundarias. |
| **`19052`** | `HTTP / WS` | **noVNC (Web Viewer)** | Servidor WebSockets puente (`websockify`) + visor HTML5. |
| **`19053`** | `RFB` | **TigerVNC / Xvnc** | Servidor de pantalla remota para clientes VNC nativos. |
| **`19054`** | `RDP` | **XRDP (Remote Desktop)** | Servidor Microsoft RDP de alta compresión. |
| **`19055`** | `TCP` | **PulseAudio Sound Sink** | Servidor de transmisión de audio bidireccional. |

---

## ⚙️ 3. Componentes Principales del Sistema

### 3.1. Hub Relay y Conexión de Agentes (`tdm/server/hub.py`)
- **Aislamiento 1:1**: Cada cliente web se asocia exclusivamente con el token generado (`/ws/client/{token}`). No se produce cruce ni auto-adopción indebida entre sesiones.
- **Detección Inmediata de Desconexión**: Emite eventos `agent_disconnected` en tiempo real ante la caída del socket para que la interfaz refleje el estado offline instantáneamente.
- **Sondeo de Salud**: El frontend consulta el estado cada 4 segundos; si el backend se apaga, la UI pasa a `🔴 No Disponible`.

### 3.2. Purga y Detención Exhaustiva de Procesos (`tdm/core/display_manager.py`)
- **Escaneo del Kernel por Variable `DISPLAY`**: Examina `/proc/[pid]/environ` para localizar cualquier subproceso asignado a `DISPLAY=:0` (ventanas, plugins, utilidades, navegadores).
- **Terminación Fulminante**: Envía `SIGKILL` (Señal 9) a todos los procesos hijos sin dejar residuos ni procesos zombies.
- **Cierre Forzado en Android**: Emite broadcasts a Termux:X11 (`am force-stop com.termux.x11`) y libera el Wake-Lock (`termux-wake-unlock`).
- **Limpieza de Locks**: Elimina sockets `/tmp/.X11-unix`, pipes y sockets D-Bus temporales.

### 3.3. Telemetría de Memoria en Tiempo Real
- Consulta dinámica de `/proc/meminfo` retornando memoria total, usada, disponible y porcentaje de carga en la API y en `tdm status`.

---

## 📱 4. Permisos de Android y Modo Persistente

Para que Termux:X11 se inicie automáticamente en Android 10+ (MIUI, HyperOS, OneUI, AOSP):
1. **Permiso de Superposición / Ventanas Emergentes**:
   - `am start -a android.settings.action.MANAGE_OVERLAY_PERMISSION -d package:com.termux`
2. **Propiedad de Comunicación Externa**:
   - `allow-external-apps = true` en `~/.termux/termux.properties`.
3. **Persistencia en Segundo Plano**:
   - `termux-wake-lock` activado durante la ejecución del servicio para evitar que el sistema congele el proceso.

---

## 🛠️ 5. Comandos de la CLI de TDM

```bash
# Ver estado del sistema, pantalla y telemetría de memoria
tdm status

# Ver registros y eventos en vivo
tdm logs -a -f          # Logs del agente WebSocket
tdm logs -s             # Logs del servidor HTTP
tdm logs -d             # Logs de la sesión gráfica X11
tdm logs --clear        # Limpiar registros

# Iniciar / Apagar entorno gráfico
tdm start --backend termux-x11 --resolution 1080x2400
tdm stop

# Actualizar el backend a la última versión
tdm update

# Gestión del servicio en segundo plano
tdm service start
tdm service stop
tdm service status

# Diagnóstico de paquetes y dependencias
tdm doctor

# Desinstalación completa sin residuos
tdm uninstall
```

---

## 📋 6. Estructura del Repositorio

```
termux-display-manager/
├── MEMORY.md                   # Esta especificación técnica y de arquitectura
├── README.md                   # Documentación principal para usuarios
├── pyproject.toml              # Definición del paquete Python y dependencias
├── scripts/
│   ├── install.sh              # Instalador bootstrap one-liner
│   ├── install_desktop.sh      # Instalador de escritorios (XFCE, KDE, MATE, LXQt, etc.)
│   ├── launch_x11.sh           # Lanzador optimizado para Termux:X11
│   ├── stop_x11.sh             # Script de purga total y detención de pantalla
│   └── setup_dependencies.sh   # Configuración de repositorios y paquetes base
├── tdm/
│   ├── __init__.py
│   ├── constants.py            # Puertos (1905x), displays y constantes globales
│   ├── config.py               # Gestión de configuración persistente (~/.tdm)
│   ├── logger.py               # Sistema de logs unificado
│   ├── version.py              # Control de versiones del proyecto
│   ├── agent/
│   │   └── client.py           # Agente WebSocket cliente para Termux
│   ├── backends/
│   │   ├── base.py             # Clase base abstracta de backends
│   │   ├── termux_x11.py       # Adaptador nativo Termux:X11
│   │   ├── novnc.py            # Adaptador Web HTML5 (websockify)
│   │   ├── vnc.py              # Adaptador TigerVNC RFB
│   │   └── rdp.py              # Adaptador Microsoft XRDP
│   ├── cli/
│   │   └── main.py             # Entrada CLI (status, start, stop, update, logs, etc.)
│   ├── core/
│   │   ├── display_manager.py  # Orquestador de pantallas y telemetría de memoria
│   │   ├── installer.py        # Gestor de instalación de escritorios y servidores
│   │   ├── manifest.py         # SQLite Manifest Ledger para desinstalación limpia
│   │   ├── models.py           # Modelos de datos de sesión y configuración
│   │   └── uninstaller.py      # Motor de desinstalación selectiva
│   ├── discovery/
│   │   ├── backends.py         # Detección de binarios de servidores gráficos
│   │   ├── desktops.py         # Detección de entornos de escritorio instalados
│   │   └── network.py          # Detección de IPs (Local, LAN, Tailscale)
│   ├── runners/
│   │   ├── env_helper.py       # Preparación de variables de entorno y D-Bus
│   │   └── session_builder.py  # Generador de scripts de inicio de sesión
│   ├── server/
│   │   ├── http_server.py      # Servidor HTTP REST y despachador WebSockets
│   │   ├── hub.py              # Hub central y gestor de sesiones 1:1
│   │   └── websocket.py        # Protocolo WebSocket RFC 6455
│   └── web/                    # Dashboard PWA compilado y empaquetado
│       ├── index.html          # Interfaz Single-Canvas Material Design 3
│       ├── manifest.json       # PWA Manifest
│       ├── service-worker.js   # Service Worker para ejecución offline
│       └── tdm-bundle.tar.gz   # Bundle autónomo de distribución
```

---

## 🔒 7. Decisiones de Diseño y Buenas Prácticas

1. **Aislamiento Seguro**: No se transmiten credenciales en texto plano; las sesiones se identifican mediante tokens criptográficos efímeros.
2. **Cero Residuos en Sistema**: Toda instalación de paquetes se audita en el archivo SQLite `manifest.db` para que `tdm uninstall` solo elimine lo que TDM instaló, sin tocar herramientas previas del usuario.
3. **Control Total de Recursos**: La purga vía `/proc` y `SIGKILL` garantiza que al pulsar "Apagar", el consumo de CPU y RAM retorne a 0% de inmediato.
