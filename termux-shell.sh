#!/bin/bash
# ==============================================================================
# 💻 Acceso Directo Interactivo a Termux en Docker (Sin necesidad de SSH)
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verificar si el contenedor está en ejecución; si no, levantarlo
if [ -z "$(docker ps -q -f name=termux-local)" ]; then
    echo "⚡ [TDM] Iniciando contenedor Termux en segundo plano..."
    docker compose -f "$DIR/docker-compose.yml" up -d
    sleep 1
fi

if [ $# -gt 0 ]; then
    # Ejecutar comando pasado por argumentos
    docker exec -it \
        -u system \
        -e TERM=xterm-256color \
        -e HOME=/data/data/com.termux/files/home \
        -e PREFIX=/data/data/com.termux/files/usr \
        -e PATH=/data/data/com.termux/files/usr/bin:/bin \
        -w /data/data/com.termux/files/home \
        termux-local bash -c "$*"
else
    # Sesión interactiva completa
    echo "====================================================="
    echo "📱 Conectando a terminal Termux interactiva (Docker)..."
    echo "📂 Directorio Home: $DIR/termux-home"
    echo "📂 Repositorio TDM: /data/data/com.termux/files/home/termux-display-manager"
    echo "====================================================="
    docker exec -it \
        -u system \
        -e TERM=xterm-256color \
        -e HOME=/data/data/com.termux/files/home \
        -e PREFIX=/data/data/com.termux/files/usr \
        -e PATH=/data/data/com.termux/files/usr/bin:/bin \
        -w /data/data/com.termux/files/home \
        termux-local bash
fi
