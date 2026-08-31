#!/bin/bash
# ==============================================================================
# 🔑 Acceso SSH a Termux en Docker (Puerto 8022)
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEY_FILE="$DIR/termux-home/.ssh/id_ed25519"

# Verificar si el contenedor está en ejecución; si no, levantarlo
if [ -z "$(docker ps -q -f name=termux-local)" ]; then
    echo "⚡ [TDM] Iniciando contenedor Termux en segundo plano..."
    docker compose -f "$DIR/docker-compose.yml" up -d
    sleep 1
fi

if [ -f "$KEY_FILE" ]; then
    chmod 600 "$KEY_FILE" 2>/dev/null || true
    if [ $# -gt 0 ]; then
        ssh -i "$KEY_FILE" \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -o LogLevel=ERROR \
            -p 8022 system@127.0.0.1 "$@"
    else
        ssh -i "$KEY_FILE" \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -p 8022 system@127.0.0.1
    fi
else
    if [ $# -gt 0 ]; then
        ssh -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -p 8022 system@127.0.0.1 "$@"
    else
        ssh -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -p 8022 system@127.0.0.1
    fi
fi
