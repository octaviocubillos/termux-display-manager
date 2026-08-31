#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker compose -f "$DIR/docker-compose.yml" up -d
echo "✅ Contenedor 'termux-local' iniciado en segundo plano."
echo "👉 Acceso directo (no SSH): ./termux-shell.sh"
echo "👉 Acceso SSH:             ./termux-ssh.sh"
