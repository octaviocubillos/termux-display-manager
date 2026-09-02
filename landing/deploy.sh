#!/bin/bash
# ==============================================================================
# TDM Landing Page - Script de Deploy a tdm.oton.cl
# ==============================================================================
# Uso: bash landing/deploy.sh [--host servidor] [--user usuario] [--path /ruta/web]
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

REMOTE_HOST="${DEPLOY_HOST:-tdm.oton.cl}"
REMOTE_USER="${DEPLOY_USER:-root}"
REMOTE_PATH="${DEPLOY_PATH:-/var/www/tdm-landing}"

echo "=============================================="
echo "🚀 [TDM Landing] Deploy a ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"
echo "=============================================="

while [[ $# -gt 0 ]]; do
    case $1 in
        --host) REMOTE_HOST="$2"; shift 2 ;;
        --user) REMOTE_USER="$2"; shift 2 ;;
        --path) REMOTE_PATH="$2"; shift 2 ;;
        *) echo "Argumento desconocido: $1"; exit 1 ;;
    esac
done

# 1. Generar bundle actualizado
echo "[1/4] Generando paquete actualizado..."
bash "${ROOT_DIR}/tdm/scripts/package_bundle.sh" 2>&1 | tail -5

# 2. Sincronizar install.sh
echo "[2/4] Sincronizando install.sh..."
cp "${ROOT_DIR}/install.sh" "${SCRIPT_DIR}/install.sh"

# 3. Copiar bundle al directorio landing
echo "[3/4] Copiando bundle..."
cp "${ROOT_DIR}/dist/tdm-bundle.tar.gz" "${SCRIPT_DIR}/tdm-bundle.tar.gz"

# 4. Subir al servidor remoto
echo "[4/4] Subiendo al servidor remoto..."
if command -v rsync &>/dev/null; then
    rsync -avz --progress \
        "${SCRIPT_DIR}/index.html" \
        "${SCRIPT_DIR}/install.sh" \
        "${SCRIPT_DIR}/clean.sh" \
        "${SCRIPT_DIR}/clean" \
        "${SCRIPT_DIR}/go" \
        "${SCRIPT_DIR}/nginx.conf" \
        "${SCRIPT_DIR}/Caddyfile" \
        "${SCRIPT_DIR}/server.py" \
        "${SCRIPT_DIR}/tdm-bundle.tar.gz" \
        "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"
    [ -d "${SCRIPT_DIR}/changelog" ] && rsync -avz "${SCRIPT_DIR}/changelog/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/changelog/"
    [ -d "${SCRIPT_DIR}/icons" ]    && rsync -avz "${SCRIPT_DIR}/icons/"    "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/icons/"
else
    scp "${SCRIPT_DIR}/index.html" "${SCRIPT_DIR}/install.sh" "${SCRIPT_DIR}/clean.sh" "${SCRIPT_DIR}/clean" "${SCRIPT_DIR}/go" "${SCRIPT_DIR}/tdm-bundle.tar.gz" \
        "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/"
fi

echo ""
echo "=============================================="
echo "✅ Deploy completo → https://${REMOTE_HOST}"
echo ""
echo "🔗 Instalar con:"
echo "   curl -sSL https://${REMOTE_HOST}/install | bash"
echo "   curl -sSL https://${REMOTE_HOST}/go | bash"
echo "=============================================="
