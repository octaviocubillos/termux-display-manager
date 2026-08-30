# 🖥️ Termux Display Manager (TDM)

> **Gestor de Pantallas, Servidores Gráficos y PWA para Entornos de Escritorio en Termux y Android.**

---

## 📌 Resumen del Proyecto

**Termux Display Manager (`TDM`)** permite proyectar y gestionar entornos de escritorio Linux nativos (KDE Plasma, MATE, XFCE4, LXQt, Openbox, i3, etc.) hacia múltiples servidores gráficos:

1. ⚡ **Termux:X11:** App nativa de Android con aceleración GPU (VirGL) a 60 FPS.
2. 🌐 **noVNC (Web HTML5):** Visor web interactivo embebido directamente en la PWA.
3. 📡 **Microsoft Remote Desktop (XRDP):** Servidor RDP para conectar tablets, PC o iPad en puerto 3389.
4. 🖥️ **TigerVNC:** Servidor VNC tradicional en puerto 5900 para clientes dedicados.

---

## 🌟 Modos de Operación: Local y Cloud Relay (PWA)

### 1. 📱 Modo Local (Directo en el Teléfono)
El servidor HTTP y WebSocket corre directamente en Termux en el puerto `9050`:
```bash
# Iniciar servidor local
tdm server --port 9050
```
- Accede a `http://localhost:9050` desde Chrome/Brave/Firefox.
- Pulsa **"Instalar App"** para añadir la PWA a tu pantalla de inicio en modo independiente a pantalla completa.

---

### 2. ☁️ Modo Cloud Relay (ej: `https://tdm.oton.cl`)
Permite controlar Termux desde cualquier navegador remoto (PC, tablet, teléfono) gestionando tu propio dominio:

1. **En tu Servidor / VPS (`tdm.oton.cl`):**
   ```bash
   tdm hub --port 9050
   ```
2. **En tu Navegador / PWA:**
   - Entra a `https://tdm.oton.cl`.
   - Se genera un token de emparejamiento único con el comando de arranque:
     ```bash
     curl -sSL https://tdm.oton.cl/setup | bash
     ```
3. **En Termux:**
   - Pegas esa sola línea. Termux se conecta mediante un túnel WebSocket saliente seguro.
   - Desde la web puedes pulsar **"Instalar XFCE"**, **"Iniciar noVNC"**, **"Ver Pantalla"** o abrir la **Terminal Web Interactiva** para ejecutar órdenes en tiempo real dentro de Termux.

---

## 🛠️ Comandos CLI Disponibles

```bash
tdm status                          # Muestra el estado de la pantalla y escritorio instalado
tdm start --backend [novnc|termux-x11|rdp|vnc]   # Inicia la salida gráfica
tdm stop                            # Apaga la pantalla activa
tdm doctor                          # Diagnóstico de paquetes y componentes
tdm server [--port 9050]            # Inicia servidor HTTP REST y PWA local
tdm hub [--port 9050]               # Inicia Hub Central Relay para dominios web
tdm agent --hub <URL> --token <TOK> # Agente de conexión remota desde Termux
tdm install --desktop [xfce|kde|openbox] # Instalación modular bajo demanda
tdm uninstall                       # Desinstalación selectiva y limpia
```

---

## 📁 Estructura del Repositorio

```
termux-display-manager/
├── tdm/
│   ├── agent/                 # Agente WebSocket cliente para Termux
│   │   └── client.py
│   ├── server/                # Servidor HTTP, WebSocket RFC 6455 y Hub Relay
│   │   ├── http_server.py
│   │   ├── hub.py
│   │   └── websocket.py
│   ├── core/                  # Supervisor de pantallas, instalador y desinstalador
│   ├── discovery/              # Detección de entornos (KDE, XFCE, Openbox, etc.)
│   ├── backends/               # Adaptadores de Termux:X11, noVNC, XRDP, VNC
│   ├── cli/                    # Interfaz CLI de comandos `tdm`
│   └── web/                    # PWA (HTML5, CSS, JS, manifest.json, service-worker.js, icons)
├── web-prototype/              # Prototipo visual y assets de la PWA
├── pyproject.toml              # Empaquetado pip estándar (Zero dependencias)
└── README.md
```
