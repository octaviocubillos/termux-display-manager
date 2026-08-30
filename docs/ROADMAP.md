# 🗺️ Roadmap de Implementación: TDM

---

### 🟢 Fase 1: Backend Core en Python (En progreso)
- [x] Especificación de arquitectura y diseño web interactivo.
- [ ] Implementar `tdm.discovery.desktops` (Detección de entorno único instalado).
- [ ] Implementar adaptadores de servidores:
  - `tdm.backends.termux_x11`
  - `tdm.backends.novnc`
  - `tdm.backends.rdp`
  - `tdm.backends.vnc`
- [ ] Implementar `tdm.core.display_manager` (Singleton Display Supervisor).
- [ ] Implementar REST API + WebSockets en `tdm.api`.

---

### 🟡 Fase 2: CLI y Frontend Web Embebido
- [ ] Implementar comando `tdm` (`tdm start`, `tdm stop`, `tdm status`, `tdm web`).
- [ ] Integrar el panel web interactivo en `tdm/web/` con visor noVNC embebido.
- [ ] Empaquetar como paquete instalable en Python / Termux.

---

### 🟣 Fase 3: App Android (WebView + Intents)
- [ ] Crear el proyecto Android en Kotlin con `WebView`.
- [ ] Implementar el intent `com.termux.RUN_COMMAND` para autoiniciar TDM.
- [ ] Inyectar `AndroidBridge` para lanzar la app de Termux:X11 y clientes RDP/VNC.
- [ ] Generar APK instalable.
