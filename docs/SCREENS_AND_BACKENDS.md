# 🖥️ Servidores y Salidas de Pantalla en TDM

## 1. ⚡ Termux:X11 (App Nativa de Android)

* **¿Para qué sirve?**
  Es el servidor gráfico con mejor rendimiento para usar en la pantalla física del teléfono o tablet. Se comunica por sockets directos de Linux/Android, permitiendo tasas de refresco de 60 Hz / 120 Hz con aceleración táctil directa.
* **Comando interno ejecutado:**
  ```bash
  termux-x11 :0 -ac -listen tcp
  ```
* **Lanzamiento en Android:**
  La app TDM o el backend dispara el intent de Android:
  ```bash
  am start --user 0 -n com.termux.x11/com.termux.x11.MainActivity
  ```

---

## 2. 🌐 noVNC (Visor Web HTML5 Integrado)

* **¿Para qué sirve?**
  Permite ver y controlar el escritorio en cualquier navegador web moderno (Chrome, Firefox, Safari) en PC, tablet o dentro de un WebView de Android sin instalar aplicaciones cliente adicionales.
* **Componentes:**
  1. **Servidor VNC base:** `Xvnc :0 -rfbport 5900 -SecurityTypes None`
  2. **Proxy WebSockets:** `websockify 6080 127.0.0.1:5900 --web $PREFIX/share/novnc`
* **URL de acceso:**
  `http://<IP-LOCAL>:6080/vnc.html?autoconnect=true&resize=remote`

---

## 3. 📡 xrdp (Microsoft Remote Desktop / RDP)

* **¿Para qué sirve?**
  Utiliza el protocolo oficial de Microsoft Remote Desktop. Ofrece una excelente compresión de ancho de banda, soporte fluido de portapapeles y canal de audio sincronizado, ideal para conectarse desde una PC con Windows o un iPad con la app oficial de Microsoft RD Client.
* **Puerto predeterminado:** `3389`
* **Conexión:** `rdp://127.0.0.1:3389`

---

## 4. 🖥️ TigerVNC Server

* **¿Para qué sirve?**
  Servidor VNC estándar en protocolo RFB. Pensado para usuarios que prefieren clientes VNC nativos instalados en Android (como bVNC Free/Pro) o en PC (como TigerVNC Viewer o RealVNC).
* **Puerto predeterminado:** `5900`
* **Conexión:** `vnc://127.0.0.1:5900`
