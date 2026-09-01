# Termux Display Manager (TDM) - Landing Page

Este directorio contiene la **Landing Page estática independiente** de Termux Display Manager.

## 🎯 Características
- **100% desacoplada del runtime de Termux**: No se instala ni se copia dentro de Termux (`$PREFIX/opt/termux-display-manager`).
- **Diseño Moderno**: Basado en Material Design 3 Dark Theme con tipografía Plus Jakarta Sans y JetBrains Mono.
- **Lista para GitHub Pages**: Puede publicarse directamente activando GitHub Pages en el repositorio o mediante despliegue estático en Vercel, Netlify, Cloudflare Pages o cualquier servidor web.

## 📦 Endpoints y Archivos Hospedados en el Dominio (`tdm.oton.cl`)
El landing page sirve directamente los scripts de instalación rápida y el paquete release:
- `https://tdm.oton.cl/install` -> Script de instalación oficial ejecutado con `curl -sSL https://tdm.oton.cl/install | bash`
- `https://tdm.oton.cl/go` -> Alias ultra-corto (`curl -sSL https://tdm.oton.cl/go | bash`)
- `https://tdm.oton.cl/install.sh` -> Script shell directo
- `https://tdm.oton.cl/tdm-bundle.tar.gz` -> Paquete release comprimido para despliegue y auto-actualizador

## 🚀 Vista previa local
Para abrir la landing page en tu navegador local:
```bash
cd landing
python3 -m http.server 8080
# Abre en el navegador: http://localhost:8080
```
