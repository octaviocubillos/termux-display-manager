# 🔒 Guía de Seguridad, Red Local (LAN) y Tailscale Mesh VPN para TDM

Esta guía describe cómo utilizar **Termux Display Manager (TDM)** de forma segura y ultraeficiente dentro de tu red local (LAN) o a través de internet mediante una red privada **Tailscale (WireGuard Mesh VPN)**.

---

## 📌 1. Arquitectura de Conexión Recomendada

```
                                  [ PC / Laptop / iPad ]
                                (Tailscale IP: 100.80.10.5)
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │
             (En la misma WiFi / LAN)                    (Fuera de casa / 4G / 5G)
                       │                                           │
                       ▼                                           ▼
             http://192.168.1.39:19050                  http://100.80.10.20:19050
                       │                                           │
                       └─────────────────────┬─────────────────────┘
                                             ▼
                                  [ Termux en tu Teléfono ]
                                (Tailscale IP: 100.80.10.20)
                                 - TDM Server (:19050)
                                 - noVNC HTML5 (:19052)
                                 - TigerVNC (:19053)
                                 - XRDP Server (:19054)
                                 - PulseAudio (:19055)
```

---

## ⚡ 2. Ventajas del Modelo Tailscale + LAN

1. **Cifrado Punto a Punto (E2E):** Todo el tráfico gráfico, pulsaciones de teclas y comandos viajan encriptados mediante el protocolo **WireGuard** de última generación.
2. **Cero Exposición a Internet:** No necesitas abrir puertos en tu router (Port Forwarding), ni configurar DMZ ni exponer servicios a bots o escaneos públicos.
3. **Cero Latencia / Conexión Directa (P2P):** Los dispositivos negocian una conexión directa entre ellos (*UDP Hole Punching*). El streaming de pantalla (60 FPS) va a la velocidad pura de tu red sin pasar por servidores intermediarios.
4. **Dominio Automático con MagicDNS:** Puedes acceder con un nombre fácil como `http://termux:19050` o `http://pixel.tailnet.ts.net:19050`.

---

## 🚀 3. Paso a Paso: Configuración con Tailscale

### Paso 1: Instalar Tailscale en tu Teléfono y en tu PC/Tablet
- **Android:** Descarga la app [Tailscale en Google Play](https://play.google.com/store/apps/details?id=com.tailscale.ipn) o F-Droid.
- **PC / Mac / Linux / iOS:** Descarga el cliente oficial desde [tailscale.com/download](https://tailscale.com/download).

### Paso 2: Iniciar Sesión en la Misma Cuenta
- Abre Tailscale en ambos dispositivos y conéctate con la misma cuenta (Google, GitHub, Microsoft o Apple).
- Activa la VPN en ambos.

### Paso 3: Obtener la IP privada de tu Teléfono
- En la app de Tailscale verás la IP asignada a tu teléfono (comienza con `100.x.y.z`, ej: `100.85.120.44`).

### Paso 4: Iniciar TDM en Termux
```bash
tdm server --port 19050
```
TDM detectará automáticamente la interfaz de Tailscale y mostrará:
```text
🚀 [TDM Server] Servidor Local + PWA activo:
   • Local:     http://localhost:19050
   • Red LAN:   http://192.168.1.39:19050
   • Tailscale: http://100.85.120.44:19050
```

### Paso 5: Abrir la PWA en cualquier dispositivo
- Desde tu laptop o tablet, abre tu navegador en:
  👉 **`http://100.85.120.44:19050`** (o `http://<nombre-dispositivo>:19050` con MagicDNS).
- Pulsa **"📲 Instalar App"** para usar TDM a pantalla completa.

---

## 🛡️ 4. Tabla de Puertos de TDM sobre Tailscale / LAN

Todos los servicios gráficos quedan accesibles en tu red privada:

| Servicio | Puerto | Descripción / Cliente Compatible |
| :--- | :--- | :--- |
| **PWA & API** | `19050` | Panel de control web y terminal interactiva |
| **TDM Secundario** | `19051` | Servidor secundario / puente de bundle |
| **noVNC** | `19052` | Visor web embebido HTML5 (sin apps externas) |
| **TigerVNC** | `19053` | Clientes VNC (bVNC, RealVNC, AVNC) |
| **XRDP** | `19054` | Microsoft Remote Desktop (RD Client en PC/iPad) |
| **PulseAudio** | `19055` | Streaming de audio en tiempo real |

---

## 💡 5. Diagnóstico de Red con `tdm doctor`

Para verificar en cualquier momento el estado de tus interfaces de red:
```bash
tdm doctor
```
Mostrará la detección de red en tiempo real:
```text
📌 Interfaces de Red y Acceso:
  [✓] Localhost:             127.0.0.1 (http://localhost:19050)
  [✓] IP Local (LAN):          192.168.1.39
  [✓] Tailscale Mesh VPN:    100.85.120.44 (Activo)
```
