# 🖥️ Termux Display Manager (TDM)

> **Gestor de Pantallas, Servidores Gráficos y PWA para Entornos de Escritorio en Termux y Android.**

---

## 📌 Resumen del Proyecto

**Termux Display Manager (`TDM`)** permite proyectar y gestionar entornos de escritorio Linux nativos (KDE Plasma, MATE, XFCE4, LXQt, Openbox, i3, etc.) hacia múltiples servidores gráficos:

1. ⚡ **Termux:X11:** App nativa de Android con aceleración GPU (VirGL) a 60/120 FPS.
2. 🌐 **noVNC (Web HTML5):** Visor web interactivo embebido directamente en la PWA (Puerto `19052`).
3. 📡 **Microsoft Remote Desktop (XRDP):** Servidor RDP para conectar tablets, PC o iPad (Puerto `19054`).
4. 🖥️ **TigerVNC:** Servidor VNC RFB tradicional para clientes dedicados como bVNC (Puerto `19053`).
5. 🔊 **PulseAudio Sink:** Servidor de audio bidireccional TCP (Puerto `19055`).

---

## 🌟 Arquitectura 100% Local y Autónoma en Termux

TDM funciona completamente de manera local y soberana dentro de Termux (sin necesidad de servidores públicos en la nube):

### 1. 📱 Panel Web PWA y API REST Local
El servidor corre directamente en Termux en el puerto `19050`:
```bash
# Iniciar servidor local
tdm server --port 19050

# O iniciar como servicio en segundo plano con Wake-Lock
tdm service start
```
- **Local:** Accede a `http://localhost:19050` desde Chrome/Brave/Firefox o la app de Android.
- **Red Local (LAN):** Accede desde cualquier PC o tablet en la misma red Wi-Fi (`http://<IP_LOCAL>:19050`).
- **Remoto Seguro (Tailscale):** Accede desde cualquier lugar del mundo mediante tu red privada Mesh VPN (`http://<IP_TAILSCALE>:19050`).
- Pulsa **"PWA / Instalar App"** para añadir TDM a tu pantalla de inicio como aplicación nativa independiente.

---

## 🛠️ Comandos CLI Disponibles

```bash
tdm status                                    # Muestra el estado de la pantalla y escritorio instalado
tdm start --backend [termux-x11|novnc|rdp|vnc]# Inicia la salida gráfica
tdm stop                                      # Apaga la pantalla activa y purga procesos
tdm doctor                                    # Diagnóstico de paquetes y componentes
tdm server [--port 19050]                     # Inicia servidor HTTP REST y PWA local
tdm service [start|stop|status]               # Daemon en segundo plano con wake-lock
tdm install --desktop [xfce|kde|openbox]      # Instalación modular bajo demanda
tdm uninstall                                 # Desinstalación selectiva y limpia (SQLite audit)
tdm agy [start|web|attach|qr|status|stop]     # Terminal dinámico persistente agy con tmux (PC/Móvil/Tablet)
```

---

## 📁 Estructura del Repositorio

```
termux-display-manager/
├── agy-terminal.sh            # Lanzador directo de terminal dinámico agy multidispositivo
├── android-app/               # Aplicación nativa Android (WebView + Puente Termux)
├── android-sdk/               # SDK stub para compilación autónoma de APK
├── docs/                      # Documentación técnica y guías de arquitectura
│   ├── AGY_DYNAMIC_TERMINAL.md# Terminal dinámico multidispositivo (PC, celular, tablet)
│   ├── ANDROID_INTEGRATION.md # Integración con Android y Setup Wizard
│   ├── ARCHITECTURE.md        # Diagramas de capas y ciclo de vida
│   ├── DESKTOP_ENVIRONMENTS.md# Entornos de escritorio soportados
│   ├── MODULAR_INSTALLATION.md# Sistema de instalación bajo demanda
│   ├── ROADMAP.md             # Línea de ruta del proyecto
│   ├── SCREENS_AND_BACKENDS.md# Backends gráficos y resoluciones
│   └── TAILSCALE_AND_SECURITY.md # Conectividad segura LAN y Tailscale Mesh
├── plans/                     # Especificaciones de API y arquitectura
├── scripts/                   # Scripts de instalación, compilación y administración
│   ├── build_apk.sh           # Generador y compilador de APK offline
│   ├── install.sh             # Instalador bootstrap del backend
│   ├── install_desktop.sh     # Instalador modular de entornos de escritorio
│   ├── install_server.sh      # Instalador de servidores de pantalla
│   ├── setup_dependencies.sh  # Instalación de paquetes base
│   ├── stop_x11.sh            # Purga de procesos y apagado total
│   └── uninstall.sh           # Desinstalación limpia auditada
├── tdm/                       # Paquete Python del núcleo de TDM (Zero-Dependencies)
│   ├── agent/                 # Agente WebSocket cliente para Termux
│   ├── backends/              # Adaptadores de Termux:X11, noVNC, XRDP, VNC
│   ├── cli/                   # Interfaz CLI de comandos `tdm`
│   ├── core/                  # Supervisor de pantallas, manifest SQLite e instalador
│   ├── discovery/             # Detección de entornos, backends y red
│   ├── runners/               # Generador de scripts de sesión y variables D-Bus
│   ├── scripts/               # Scripts empaquetados para ejecución en runtime
│   ├── server/                # Servidor HTTP REST, WebSocket RFC 6455 y Hub Relay
│   └── web/                   # PWA (HTML5, CSS, JS, manifest.json, service-worker, noVNC)
├── tests/                     # Suite de pruebas automatizadas
├── install.sh                 # Acceso directo al instalador bootstrap
├── uninstall.sh               # Acceso directo al desinstalador limpio
├── pyproject.toml             # Empaquetado pip estándar (Zero dependencias)
├── MEMORY.md                  # Memoria técnica del proyecto y decisiones de diseño
└── README.md
```
