# 📡 Especificación de la API de TDM (REST & WebSockets)

El servidor de TDM corre por defecto en `http://127.0.0.1:19050`.

---

## 1. Endpoints REST

### `GET /api/status`
Devuelve el estado general del sistema, el entorno instalado y la pantalla activa.

**Respuesta de ejemplo:**
```json
{
  "installed_desktop": {
    "id": "kde",
    "name": "KDE Plasma",
    "executable": "/data/data/com.termux/files/usr/bin/startplasma-x11"
  },
  "screen": {
    "status": "running",
    "backend": "termux-x11",
    "display": ":0",
    "resolution": "1080x2400",
    "dpi": 96,
    "audio": true,
    "virgl": true,
    "pid": 58420,
    "uptime_seconds": 2530,
    "urls": {
      "connect": "termux-x11://display:0"
    }
  }
}
```

---

### `POST /api/screen/start`
Inicia o cambia el servidor de pantalla actual.

**Cuerpo de solicitud (JSON):**
```json
{
  "backend": "novnc",
  "resolution": "1920x1080",
  "dpi": 96,
  "audio": true,
  "virgl": true
}
```

---

### `POST /api/screen/stop`
Detiene la pantalla activa, mata los procesos asociados y limpia sockets temporales.

---

### `GET /api/doctor`
Ejecuta diagnósticos para verificar si los paquetes y librerías necesarias están instalados.

---

## 2. Eventos WebSocket (`/ws/events`)

Permite recibir actualizaciones en tiempo real sobre cambios de estado:
* `screen_starting`: La pantalla se está iniciando.
* `screen_started`: La pantalla está lista para recibir conexiones.
* `screen_stopped`: La pantalla se ha detenido.
* `screen_error`: Ocurrió un error en el servidor gráfico o en el escritorio.
