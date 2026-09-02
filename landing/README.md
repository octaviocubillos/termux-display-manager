# Termux Display Manager (TDM) - Landing Page

Este directorio contiene la **Landing Page estática independiente** de Termux Display Manager con soporte para **Reverse Proxy Dinámico** basado en hashes de 8 letras y SQLite, además de soporte legacy para `/aabbcc`.

## Características
- **100% desacoplada del runtime de Termux**: No se instala ni se copia dentro del entorno Termux del usuario.
- **Diseño Moderno**: Basado en Material Design 3 Dark Theme con tipografía Plus Jakarta Sans y JetBrains Mono.
- **Reverse Proxy Dinámico con SQLite**: Reenvío transparente de HTTP y WebSockets a la aplicación web de TDM mediante hashes únicos de 8 letras (`/<hash>/`), detectando automáticamente si la IP local o de Tailscale está activa.
- **Autodetección de Conectividad**: Prueba secuencialmente `127.0.0.1`, interfaces LAN y Tailscale con caché de IP activa.
- **Protección de Scripts contra Navegadores**: Bloquea la visualización accidental en navegadores web de `/install`, `/clean` y `/go` respondiendo con código HTTP 403 y guía de uso para Termux.
- **Soporte para Nginx, Caddy y Servidor Python Nativo**: Incluye servidor asíncrono (`server.py`), módulo de base de datos (`db.py`), plantilla `nginx.conf` y `Caddyfile`.

## Endpoints y Archivos Hospedados (`tdm.oton.cl`)
El landing page sirve directamente los scripts de instalación rápida, el paquete release y el gateway proxy:
- `https://tdm.oton.cl/install` -> Script de instalación oficial ejecutado con `curl -fsSL https://tdm.oton.cl/install | bash`
- `https://tdm.oton.cl/go` -> Alias corto de instalación (`curl -fsSL https://tdm.oton.cl/go | bash`)
- `https://tdm.oton.cl/clean` -> Limpiador total a cero (`curl -fsSL https://tdm.oton.cl/clean | bash`)
- `https://tdm.oton.cl/tdm-bundle.tar.gz` -> Paquete release comprimido para despliegue y auto-actualizador
- `https://tdm.oton.cl/<hash>/` -> **Reverse Proxy Dinámico** hacia el panel web de TDM en tu red local o Tailscale
- `https://tdm.oton.cl/api/register` -> Endpoint API para registro de dispositivos y sondeo de IPs

## Ejecución del Servidor con Proxy Dinámico
Para iniciar la landing page localmente o en producción:
```bash
cd landing
python3 server.py --port 8080 --target-host 192.168.1.197 --target-port 19050
```
