# 📋 Plan Maestro del Proyecto: Termux Display Manager (TDM)

## 1. Visión y Objetivos

El objetivo de **TDM** es proporcionar una solución integral, visual y por línea de comandos para administrar las salidas gráficas de un entorno de escritorio nativo en Termux (Android).

### Principios Fundamentales:
* **100% Nativo:** Utiliza exclusivamente paquetes oficiales de Termux (`pkg install`), sin depender de capas adicionales como PRoot o emuladores en esta fase.
* **1 Solo Entorno Nativo Instalado:** Para evitar conflictos de librerías, dependencias D-Bus y configuraciones en `$HOME`, el sistema asume y gestiona un único escritorio instalado en el prefijo de Termux (KDE Plasma, MATE, XFCE4, LXQt, etc.).
* **Gestor de Pantallas Multisalida:** La función central es permitir proyectar ese escritorio en la pantalla adecuada según la necesidad del usuario (**Termux:X11**, **noVNC Web**, **xrdp RDP**, **TigerVNC**).

---

## 2. Requisitos Funcionales

### RF-1: Detección y Modos de Ejecución
* TDM escanea `$PREFIX/bin` para identificar qué entorno o modo está disponible:
  - KDE Plasma (`startplasma-x11`)
  - MATE Desktop (`mate-session`)
  - XFCE4 (`xfce4-session` / `startxfce4`)
  - LXQt (`startlxqt`)
  - i3 Window Manager (`i3`)
  - Openbox (`openbox-session`)
  - **💻 Modo Terminal X11 Standalone:** Sesión gráfica ligera ejecutando directamente el emulador de terminal (`konsole`, `mate-terminal`, `xfce4-terminal`, `xterm`) a pantalla completa sin cargar un entorno pesado.
  - **⌨️ Consola Web Integrada:** PTY interactiva vía WebSockets en el panel web/WebView para ejecutar comandos directos de Termux (`pkg`, `top`, `btop`).

### RF-2: Conmutación de Servidor / Pantalla
* Permite seleccionar y cambiar la salida activa:
  1. **⚡ Termux:X11:** Inicia el servidor X11 local y abre la app Android `com.termux.x11`.
  2. **🌐 noVNC (Web HTML5):** Inicia Xvnc + proxy WebSockets y sirve el visor interactivo en navegador/WebView.
  3. **📡 xrdp (RDP):** Inicia el servidor RDP en el puerto 3389 para clientes de Microsoft Remote Desktop.
  4. **🖥️ TigerVNC:** Inicia Xvnc en puerto 5900 para clientes VNC externos (bVNC).

### RF-3: Ajustes Dinámicos de Pantalla
* Configuración de resolución (Auto/Móvil, 1080p, 720p, 2K, etc.).
* Configuración de escala DPI (96, 120, 144, 192 DPI).
* Habilitación / Deshabilitación de canal de audio PulseAudio TCP 4713.
* Habilitación / Deshabilitación de aceleración gráfica VirGL 3D (GPU virpipe).

### RF-4: Supervisión Limpia de Procesos
* Parada ordenada (`graceful termination`) del servidor anterior antes de encender uno nuevo.
* Limpieza automática de sockets X11 huérfanos (`/tmp/.X11-unix/X0`, `/tmp/.X0-lock`).
* Monitoreo de estado (Iniciando, En ejecución, Detenido, Error).

---

## 3. Interfaces de Usuario

1. **Dashboard Web / WebView:** Interfaz táctil moderna (Dark Mode) con visor noVNC embebido y puente nativo Android.
2. **CLI de Terminal (`tdm`):**
   - `tdm start [--backend termux-x11|novnc|rdp|vnc] [--res 1920x1080]`
   - `tdm stop`
   - `tdm status`
   - `tdm doctor`
   - `tdm web [--port 9050]`
