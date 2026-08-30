# 🧩 Estrategia de Instalación Modular y Bajo Demanda (TDM)

Para optimizar el uso de almacenamiento, ancho de banda y tiempo en Termux, TDM utiliza un enfoque de **Instalación Progresiva Bajo Demanda (On-Demand Modular Setup)**:

```
┌─────────────────────────────────────────────────────────────┐
│ ⚡ FASE 1: INSTALACIÓN MÍNIMA (setup_minimal.sh)             │
│ • python, dbus, x11-repo, utilidades base                   │
│ • allow-external-apps=true y carpetas ~/.tdm                │
│ (Se ejecuta en segundos la primera vez)                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 🚀 FASE 2: GATILLADO BAJO DEMANDA (Al seleccionar en la UI) │
├──────────────────────────────┼──────────────────────────────┤
│ Si eliges Termux:X11         │ Instala `termux-x11-nightly` │
│ Si eliges noVNC Web          │ Instala `tigervnc` + `novnc` │
│ Si eliges Remote Desktop     │ Instala `xrdp` + `pulseaudio`│
│ Si eliges TigerVNC (bVNC)    │ Instala `tigervnc` base      │
│ Si eliges Audio PulseAudio   │ Instala `pulseaudio`         │
└──────────────────────────────┴──────────────────────────────┘
```

---

## 🛠️ Scripts en el Backend (`tdm/scripts/`)

1. **`setup_minimal.sh`**:
   Instala solo lo fundamental para que el daemon TDM y la API REST funcionen.
2. **`install_server.sh <server>`**:
   Instala de forma independiente el servidor gráfico solicitado (`termux-x11`, `novnc`, `vnc`, `rdp`, `audio`).
3. **`install_desktop.sh <desktop>`**:
   Instala de forma independiente el entorno solicitado (`kde`, `mate`, `xfce`, `lxqt`, `i3`, `openbox`).
4. **`check_system.sh`**:
   Escanea y reporta el estado de cada componente.

---

## 📡 Control desde el Frontend / App

* **Endpoint de Instalación Mínima:** `POST /api/install/minimal`
* **Endpoint de Servidor Específico:** `POST /api/install/server` con `{"server": "novnc"}`
* **Endpoint de Escritorio Específico:** `POST /api/install/desktop` con `{"desktop": "kde"}`
* **Diagnóstico en Vivo:** `GET /api/system/check`
