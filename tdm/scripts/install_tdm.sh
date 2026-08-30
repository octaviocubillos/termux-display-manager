#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Script de Instalación del Comando `tdm`
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_BIN="${PREFIX:-/usr}/bin/tdm"

echo "====================================================="
echo "📦 [TDM] Instalando lanzador global 'tdm' en $TARGET_BIN"
echo "====================================================="

# Crear el script lanzador global
cat << 'EOF' > "$TARGET_BIN"
#!/data/data/com.termux/files/usr/bin/bash
# Launcher script para Termux Display Manager
PROJECT_DIR="${HOME}/termux-display-manager"

if [ ! -d "$PROJECT_DIR" ]; then
    PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

export PYTHONPATH="$PROJECT_DIR:${PYTHONPATH}"
exec python3 -m tdm.cli.main "$@"
EOF

chmod +x "$TARGET_BIN"

# Asegurar permisos de scripts
chmod +x "$DIR"/scripts/*.sh 2>/dev/null || true

echo "✅ Comando 'tdm' instalado correctamente en $TARGET_BIN"
echo "💡 Ahora puedes ejecutar 'tdm --help' o 'tdm status' desde cualquier lugar."
echo "====================================================="
