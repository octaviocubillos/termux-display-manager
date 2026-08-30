# 🎨 Modos de Sesión Gráfica Nativos en Termux

TDM permite lanzar tanto el entorno de escritorio instalado como un modo terminal ultraligero a pantalla completa:

---

## 1. ❄️ KDE Plasma (Nativo en `x11-repo`)

* **Instalación:**
  ```bash
  pkg install -y x11-repo
  pkg install -y plasma-desktop plasma-workspace breeze konsole dolphin
  ```
* **Variables requeridas:**
  - `export KDE_FULL_SESSION=true`
  - `export QT_QPA_PLATFORM=xcb`
* **Ejecutable:**
  `startplasma-x11` (o arranque de fallback con `kwin_x11 & plasmashell`).

---

## 2. 🧉 MATE Desktop

* **Instalación:**
  ```bash
  pkg install -y x11-repo
  pkg install -y mate-desktop mate-panel mate-session-manager mate-terminal marco
  ```
* **Variables requeridas:**
  - `export GSETTINGS_BACKEND=keyfile`
  - `export XDG_CURRENT_DESKTOP=MATE`
* **Ejecutable:**
  `mate-session`

---

## 3. 🐭 XFCE4

* **Instalación:**
  ```bash
  pkg install -y x11-repo
  pkg install -y xfce4 xfce4-terminal
  ```
* **Variables requeridas:**
  - `export XDG_CURRENT_DESKTOP=XFCE`
* **Ejecutable:**
  `xfce4-session`

---

## 4. 🚀 LXQt / i3 / Openbox

* **Instalación:**
  ```bash
  pkg install -y lxqt lxqt-session qterminal i3 openbox tint2
  ```
* **Ejecutable:**
  `startlxqt`, `i3`, o `openbox-session`

---

## 5. 💻 Modo Terminal X11 Standalone (Ultraligero)

* **¿Para qué sirve?**
  Lanza una sesión gráfica pura que contiene únicamente un emulador de terminal maximizado (como `konsole`, `mate-terminal`, `xfce4-terminal` o `xterm`).
* **Ventajas:**
  - Cero consumo de RAM en paneles, widgets o demonios de escritorio.
  - Ideal para trabajar con **NeoVim**, **Emacs**, **tmux**, compilar código o scripts intensivos con aceleración de fuentes y GPU en Termux:X11 o noVNC.
* **Ejecutable:**
  `konsole --fullscreen` o `mate-terminal --maximize` o `xfce4-terminal --maximize` o `xterm -geometry 120x40`.
