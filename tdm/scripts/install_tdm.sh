#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Script de Instalación del Comando `tdm`
# ==============================================================================

set -e

DIR="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
TARGET_BIN="$PREFIX/bin/tdm"

echo "====================================================="
echo "📦 [TDM] Instalando lanzador global 'tdm' en $TARGET_BIN"
echo "====================================================="

export TMPDIR="${PREFIX:-/data/data/com.termux/files/usr}/tmp"
mkdir -p "$TMPDIR"

# Crear el script lanzador global
printf '%s\n' \
'#!/data/data/com.termux/files/usr/bin/bash' \
'# Launcher script para Termux Display Manager' \
'PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"' \
'PROJECT_DIR="${PREFIX}/opt/termux-display-manager"' \
'' \
'if [ ! -d "$PROJECT_DIR" ]; then' \
'    PROJECT_DIR="${PREFIX}/share/termux-display-manager"' \
'fi' \
'' \
'if [ ! -d "$PROJECT_DIR" ]; then' \
'    PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"' \
'fi' \
'' \
'export PYTHONPATH="$PROJECT_DIR:${PYTHONPATH}"' \
'exec python3 -m tdm.cli.main "$@"' > "$TARGET_BIN"

chmod +x "$TARGET_BIN"

# Asegurar permisos de scripts
chmod +x "$DIR"/tdm/scripts/*.sh "$DIR"/*.sh 2>/dev/null || true

echo "✅ Comando 'tdm' instalado correctamente en $TARGET_BIN"
echo "💡 Ahora puedes ejecutar 'tdm --help' o 'tdm status' desde cualquier lugar."
echo "====================================================="
