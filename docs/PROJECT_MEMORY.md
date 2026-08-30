# 🧠 Memoria del Proyecto y Registro de Decisiones de Diseño (TDM)

> **Fecha de Consolidación:** 28 de Agosto, 2026  
> **Proyecto:** Termux Display Manager (`TDM`)  
> **Ubicación del Proyecto:** `/home/octavio/termux-display-manager/`

---

## 📌 1. Resumen Ejecutivo y Alcance
* **Propósito:** Gestor de pantallas y servidores gráficos para Termux (Android).
* **Alcance Actual:** **100% Nativo** (usando paquetes de Termux `pkg install`, sin capas de PRoot/emuladores en esta fase).
* **Entornos Nativos Principales:**
  - ❄️ **KDE Plasma** (`pkg install plasma` / `plasma-desktop`)
  - 🧉 **MATE Desktop** (`pkg install mate-desktop mate-session-manager`)
  - 🐭 **XFCE4** (`pkg install xfce4 xfce4-terminal`)
  - 🚀 **LXQt** (`pkg install lxqt lxqt-session`)
  - 🪟 **i3 Window Manager** / **Openbox** / **Fluxbox**
  - 💻 **Modo Terminal X11 Standalone** (Konsole / Terminal a pantalla completa ultraligera)

---

## 🛡️ 2. Reglas de Arquitectura y Decisiones Críticas
1. **Regla de 1 Solo Entorno Nativo Instalado:**
   - Para evitar conflictos de dependencias, servicios D-Bus, políticas polkit y configuraciones en `$HOME`, el sistema asume y gestiona **1 único entorno de escritorio instalado en el sistema**.
   - Por tanto, la aplicación no mezcla ni conmuta entre múltiples escritorios instalados a la vez, sino que se enfoca en **proyectar ese entorno hacia diferentes pantallas y servidores gráficos**.
2. **Servidores de Salida Gráfica Soportados:**
   - ⚡ **Termux:X11:** App nativa en Android para pantalla táctil local (60/120 Hz).
   - 🌐 **noVNC Web:** Visor Web HTML5 embebido en navegador o WebView sin instalar apps cliente.
   - 📡 **Microsoft Remote Desktop (xrdp):** Servidor RDP en puerto 3389 para clientes de Microsoft RD.
   - 🖥️ **TigerVNC:** Servidor VNC estándar en puerto 5900 para bVNC.
3. **Consola Web Integrada (Web Terminal Drawer):**
   - Panel de terminal PTY interactivo integrado en el panel web/WebView para ejecutar comandos directos de Termux (`pkg`, `top`, `btop`, diagnósticos).
4. **Asistente Post-Instalación del APK (Setup Wizard / Onboarding):**
   - Pantalla de bienvenida que guía en 4 pasos la primera vez que se abre la app en Android:
     1. Verificación de la app Termux (`com.termux`).
     2. Permiso `com.termux.permission.RUN_COMMAND` y `allow-external-apps = true`.
     3. Instalación de la app complementaria Termux:X11 (`com.termux.x11`) o selección de noVNC.
     4. Comprobación y acceso al Panel de Control de Pantallas.

---

## 📂 3. Mapa de Archivos del Proyecto

```
termux-display-manager/
├── README.md                          # Visión general del proyecto
├── docs/
│   ├── ARCHITECTURE.md                # Diagramas de capas, procesos y variables
│   ├── SCREENS_AND_BACKENDS.md        # Especificación técnica de Termux:X11, noVNC, RDP y VNC
│   ├── DESKTOP_ENVIRONMENTS.md        # Guía de inicialización de KDE, MATE, XFCE4, LXQt, i3
│   ├── ANDROID_INTEGRATION.md         # Integración APK, Intents y Setup Wizard
│   ├── ROADMAP.md                     # Hitos de desarrollo y fases
│   └── PROJECT_MEMORY.md              # Este archivo (Memoria consolidada)
├── plans/
│   ├── PROJECT_PLAN.md                # Requisitos funcionales y diseño maestro
│   └── API_SPECIFICATION.md           # Endpoints REST y eventos WebSockets
└── web-prototype/
    ├── index.html                     # Prototipo interactivo del Panel de Control de Pantallas
    └── setup_wizard.html               # Prototipo interactivo del Asistente Post-Instalación APK
```

---

## 🌐 4. Prototipos Web Disponibles para Pruebas

* **Panel de Control de Pantallas:**  
  👉 `http://localhost:8080/preview_tdm.html` o `http://localhost:8080/web-prototype/index.html`
* **Asistente Post-Instalación APK:**  
  👉 `http://localhost:8080/preview_apk_wizard.html` o `http://localhost:8080/web-prototype/setup_wizard.html`
