# 🗺️ Roadmap de Implementación: TDM

---

### 🟢 Fase 1: Backend Core en Python (✅ Completado)
- [x] Especificación de arquitectura y diseño web interactivo ([MEMORY.md](file:///workspace/termux-display-manager/MEMORY.md)).
- [x] Implementar `tdm.discovery.desktops` (Detección de entorno único instalado: XFCE4, KDE, MATE, LXQt, i3, Openbox, Terminal X11).
- [x] Implementar adaptadores de servidores:
  - [x] `tdm.backends.termux_x11` (Display `:0` nativo Android)
  - [x] `tdm.backends.novnc` (WebSockets HTML5 puerto `19052`)
  - [x] `tdm.backends.rdp` (xrdp Microsoft Remote Desktop puerto `19054`)
  - [x] `tdm.backends.vnc` (TigerVNC RFB puerto `19053`)
- [x] Implementar `tdm.core.display_manager` (Singleton Display Supervisor con purga `/proc` y `SIGKILL`).
- [x] Implementar REST API + WebSockets nativos RFC 6455 y Hub Relay en `tdm.server` (puerto `19050`).
- [x] Telemetría de RAM en tiempo real vía `/proc/meminfo`.
- [x] Sistema de desinstalación selectiva auditada mediante SQLite (`manifest.db`).

---

### 🟡 Fase 2: CLI y Frontend Web Embebido (✅ Completado)
- [x] Implementar comando `tdm` (`tdm status`, `start`, `stop`, `doctor`, `server`, `service`, `update`, `uninstall`).
- [x] Integrar el panel web interactivo PWA en `tdm/web/` con diseño Material Design 3.
- [x] Empaquetar como paquete Python instalable en Termux (`pyproject.toml` y enlaces `.pth`).
- [x] Scripts de instalación (`install.sh`, `install_desktop.sh`, `install_server.sh`, `setup_dependencies.sh`).
- [x] Entorno de pruebas y desarrollo en Docker (`Dockerfile.termux`, `docker-compose.yml`, `start-termux.sh`).

---

### 🟣 Fase 3: PWA y Web Terminal PTY (✅ Completado)
- [x] PWA completa offline instalable en móvil y escritorio con `sw.js` y `manifest.json`.
- [x] Consola Web interactiva PTY bash/zsh nativa con `xterm.js` y barra de teclas móviles.
- [x] Visor Web noVNC integrado con redimensión y controles táctiles.
- [x] Panel de telemetría en tiempo real (CPU, RAM, Disco, Red LAN/WAN).

---

### 🔵 Fase 4: Próximas Mejoras y Optimizaciones (En Planificación)
- [ ] Optimización de canal de audio PulseAudio TCP (puerto `19055`) con baja latencia.
- [ ] Soporte experimental para protocolos Wayland (Waydroid / Weston).
- [ ] Integración con plugins de aceleración por hardware VirGL 3D.
- [ ] Soporte de autenticación de dos factores (2FA) opcional para el Hub Relay.
