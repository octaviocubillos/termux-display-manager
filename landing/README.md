# Termux Display Manager (TDM) - Landing Page

Este directorio contiene la **Landing Page estática independiente** de Termux Display Manager con soporte para **HTTP Reverse Proxy** en `/aabbcc`.

## 🎯 Características
- **100% desacoplada del runtime de Termux**: No se instala ni se copia dentro de Termux (`$PREFIX/opt/termux-display-manager`).
- **Diseño Moderno**: Basado en Material Design 3 Dark Theme con tipografía Plus Jakarta Sans y JetBrains Mono.
- **HTTP Reverse Proxy en `/aabbcc`**: Reenvío transparente de HTTP y WebSockets a la aplicación web de TDM (en `192.168.1.197:19050` o host configurable), eliminando dependencias de iframes.
- **Lista para Nginx / Caddy / Python Server**: Incluye servidor Python standalone (`server.py`), plantilla `nginx.conf` y `Caddyfile`.

## 📦 Endpoints y Archivos Hospedados en el Dominio (`tdm.oton.cl`)
El landing page sirve directamente los scripts de instalación rápida, el paquete release y el gateway proxy:
- `https://tdm.oton.cl/install` -> Script de instalación oficial ejecutado con `curl -sSL https://tdm.oton.cl/install | bash`
- `https://tdm.oton.cl/go` -> Alias ultra-corto (`curl -sSL https://tdm.oton.cl/go | bash`)
- `https://tdm.oton.cl/install.sh` -> Script shell directo
- `https://tdm.oton.cl/tdm-bundle.tar.gz` -> Paquete release comprimido para despliegue y auto-actualizador
- `https://tdm.oton.cl/aabbcc/` -> **HTTP Reverse Proxy** hacia la aplicación web de TDM en tu red local

## 🚀 Ejecución del Servidor con HTTP-Proxy
Para iniciar la landing page con el proxy hacia tu dispositivo Android / Termux:
```bash
cd landing
# Reemplaza --target-host si tu IP cambia
python3 server.py --port 8080 --target-host 192.168.1.197 --target-port 19050
# Abre en el navegador:
# • Landing Page: http://localhost:8080
# • App Web vía Proxy: http://localhost:8080/aabbcc/
```
