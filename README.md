# Termux Display Manager (TDM)

> Gestor de Pantallas, Servidores Gráficos y PWA para Entornos de Escritorio en Termux y Android.

---

## Resumen del Proyecto

**Termux Display Manager (TDM)** permite proyectar y gestionar entornos de escritorio Linux nativos (KDE Plasma, MATE, XFCE4, LXQt, Openbox, i3, etc.) hacia múltiples servidores gráficos y protocolos:

1. **Termux:X11:** Aplicación nativa de Android con aceleración GPU (VirGL) a 60/120 FPS.
2. **noVNC (Web HTML5):** Visor interactivo en navegador embebido directamente en la PWA (Puerto `19052` / `19050`).
3. **Microsoft Remote Desktop (XRDP):** Servidor RDP estándar para conectar tablets, PC o iPad (Puerto por defecto `3389`).
4. **TigerVNC:** Servidor VNC RFB tradicional para clientes dedicados como bVNC (Puerto por defecto `5900`).
5. **PulseAudio Sink:** Servidor de audio bidireccional TCP (Puerto `19055`).

---

## Instalación y Limpieza en 1 Comando

### Instalación Rápida
Ejecuta en la consola de Termux:
```bash
curl -fsSL https://tdm.oton.cl/install | bash
```
*(O mediante el alias corto: `curl -fsSL https://tdm.oton.cl/go | bash`)*

### Limpiador Total y Reseteo a Cero
Para purgar procesos, dependencias huérfanas, escritorios y restaurar Termux a su estado inicial:
```bash
curl -fsSL https://tdm.oton.cl/clean | bash
```

---

## Identificador Único y Acceso Web Centralizado (HTTPS)

Durante la instalación o al ejecutar `tdm register`, TDM genera un identificador único de **8 letras minúsculas** (`[a-z]{8}`, ej. `kxpmqrvw`) almacenado de forma persistente en SQLite. Este código habilita el acceso web seguro a través del Hub central:

```text
https://tdm.oton.cl/<hash>/
```

### Beneficios del Acceso Central HTTPS
- **Conexión Cifrada SSL/TLS:** Elimina las advertencias de "Sitio no seguro" mostradas por navegadores al acceder por IP plana.
- **Soporte Completo PWA:** Permite instalar el panel web de TDM como una aplicación de escritorio nativa e independiente en PC, Mac o Tablet mediante Service Workers.
- **Portapapeles Bidireccional:** Habilita el uso de la API segura `navigator.clipboard` para copiar y pegar texto sin restricciones entre el navegador y el dispositivo Android.
- **Experiencia Inmersiva:** Desbloquea las APIs de bloqueo de puntero (Pointer Lock), captura de teclado completo y pantalla completa para el control fluido de sesiones de escritorio remoto.

### Privacidad Total y Cero Recolección
- **Procesamiento 100% Local:** Todos los escritorios gráficos, archivos, credenciales y procesos residen exclusivamente dentro de tu dispositivo Android en Termux.
- **Cero Telemetría:** Ninguna información personal, archivo, pulsación de teclas ni historial de navegación se envía ni se almacena en servidores externos.
- **Túnel Seguro:** El dominio público actúa exclusivamente como un puente seguro TLS hacia las IPs locales de tu red privada.

> [!IMPORTANT]
> **Condición de Conectividad para el Acceso Web Central**:
> Para acceder a `https://tdm.oton.cl/<hash>/`, tu cliente (computador o tablet) debe encontrarse conectado a la **misma red Wi-Fi/local** de tu teléfono o tener activa tu red privada **Tailscale**.

---

## Modos de Conectividad Soportados

| Tipo de Acceso | URL / Destino | Descripción |
| :--- | :--- | :--- |
| **Local** | `http://127.0.0.1:19050` | Acceso directo en el propio dispositivo Android. |
| **Red Local (LAN)** | `http://<IP_LOCAL>:19050` | Acceso vía Wi-Fi o Ethernet en tu red doméstica. |
| **Tailscale VPN** | `http://<IP_TAILSCALE>:19050` | Acceso remoto cifrado punto a punto vía Tailscale Mesh. |
| **Acceso Central HTTPS** | `https://tdm.oton.cl/<hash>/` | Acceso seguro con certificado TLS y soporte PWA completo. |

---

## Arquitectura de Persistencia con SQLite

TDM no utiliza dependencias externas para almacenamiento ni archivos JSON concurrentes expuestos a corrupción:
- **Dispositivo (Termux):** Registro de identidad (`device_identity`) y auditoría de paquetes instalados en `~/.tdm/manifest.sqlite3`.
- **Servidor Hub (Landing):** Registro de dispositivos y sondeo de IP activa en `landing/devices.sqlite3` en modo WAL (`Write-Ahead Logging`).
- **Desinstalación Cero Residuos:** `tdm uninstall` consulta el manifiesto SQLite para desinstalar única y exclusivamente los paquetes que TDM instaló, respetando herramientas previas del usuario.

---

## Comandos CLI Disponibles

```bash
tdm register                                  # Registra el dispositivo en el Hub y proyecta el banner de accesos
tdm status                                    # Muestra estado de pantalla, backends y URLs de conectividad
tdm start --backend [termux-x11|novnc|rdp|vnc]# Inicia la salida gráfica con el entorno configurado
tdm stop                                      # Apaga el servidor gráfico y detiene procesos asociados
tdm novnc [start|stop|status|url|open]        # Control directo del visor web HTML5 noVNC
tdm doctor                                    # Diagnóstico de paquetes, aceleración 3D e interfaces de red
tdm server [--port 19050]                     # Servidor HTTP REST y panel Web Dashboard/PWA
tdm service [start|stop|restart|status]       # Gestor de servicio en segundo plano con wake-lock
tdm install --desktop [xfce|kde|openbox]      # Instalación modular de escritorios bajo demanda
tdm uninstall                                 # Desinstalación selectiva auditada por SQLite
tdm permissions                               # Solicita en pantalla el permiso "Mostrar sobre otras apps"
```

---

## Estructura del Repositorio

```
termux-display-manager/
├── docs/                      # Documentación técnica y guías de arquitectura
│   ├── ARCHITECTURE.md        # Diagramas de capas y ciclo de vida
│   ├── DESKTOP_ENVIRONMENTS.md# Entornos de escritorio soportados
│   ├── MODULAR_INSTALLATION.md# Sistema de instalación modular
│   ├── ROADMAP.md             # Línea de ruta del proyecto
│   ├── SCREENS_AND_BACKENDS.md# Backends gráficos y resoluciones
│   └── TAILSCALE_AND_SECURITY.md # Conectividad segura LAN y Tailscale Mesh
├── landing/                   # Landing Page y Reverse Proxy Dinámico
│   ├── db.py                  # Gestor de persistencia SQLite (modo WAL)
│   ├── server.py              # Servidor HTTP y Reverse Proxy con autodetección de IP
│   ├── index.html             # Landing Page pública oficial
│   ├── install.sh             # Script de instalación bootstrap
│   ├── clean.sh               # Script de limpieza total a cero
│   ├── go                     # Script alias corto de instalación
│   ├── nginx.conf             # Plantilla de proxy inverso Nginx / OpenResty
│   └── Caddyfile              # Plantilla de proxy Caddy
├── tdm/                       # Paquete Python del núcleo de TDM (Zero-Dependencies)
│   ├── backends/              # Controladores de Termux:X11, noVNC, XRDP y VNC
│   ├── cli/                   # Interfaz de línea de comandos `tdm`
│   ├── core/                  # Identidad de dispositivo, supervisor y SQLite manifest
│   │   ├── device.py          # Hash de 8 letras, IPs locales, Tailscale y banner
│   │   ├── manifest.py        # Registro de auditoría SQLite
│   │   └── uninstaller.py     # Desinstalador limpio selectivo
│   ├── discovery/             # Detección de entornos, backends y red
│   ├── runners/               # Generador de scripts de sesión y variables D-Bus
│   ├── scripts/               # Scripts de instalación y configuración de entornos
│   ├── server/                # Servidor HTTP REST y WebSockets RFC 6455
│   └── web/                   # Panel Web PWA (HTML5, JS, noVNC, terminal xterm.js)
├── tests/                     # Suite de pruebas automatizadas
│   ├── test_device_hash.py    # Pruebas de hash, SQLite y proxy dinámico
│   └── test_cli.py            # Pruebas de comandos CLI
├── install.sh                 # Instalador bootstrap del sistema
├── clean.sh                   # Limpiador total del sistema
├── uninstall.sh               # Desinstalador auditado directo
├── pyproject.toml             # Configuración de paquete Python
└── README.md
```
