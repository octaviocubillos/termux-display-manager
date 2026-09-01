#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Package Release Bundle Generator
# ==============================================================================
# Empaqueta todos los archivos necesarios para el despliegue limpio en Termux.
# Excluye .git, caches, tests y el directorio landing/ desacoplado.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"

mkdir -p "$DIST_DIR"

VERSION=$(python3 -c "from tdm.version import __version__; print(__version__)" 2>/dev/null || echo "latest")
BUNDLE_NAME="termux-display-manager-v${VERSION}.tar.gz"
LATEST_BUNDLE="termux-display-manager-latest.tar.gz"

echo "====================================================="
echo "📦 [TDM Packaging] Creando paquete para Termux (v$VERSION)"
echo "====================================================="

cd "$ROOT_DIR"

tar -czf "$DIST_DIR/$BUNDLE_NAME" \
    --exclude=".git" \
    --exclude="landing" \
    --exclude="tests" \
    --exclude="dist" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude="termux-home" \
    --exclude=".pytest_cache" \
    bin tdm install.sh uninstall.sh pyproject.toml README.md 2>/dev/null || \
tar -czf "$DIST_DIR/$BUNDLE_NAME" \
    --exclude=".git" \
    --exclude="landing" \
    --exclude="tests" \
    --exclude="dist" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude="termux-home" \
    bin tdm install.sh uninstall.sh pyproject.toml README.md

cp -f "$DIST_DIR/$BUNDLE_NAME" "$DIST_DIR/$LATEST_BUNDLE"
cp -f "$DIST_DIR/$BUNDLE_NAME" "$DIST_DIR/tdm-bundle.tar.gz"

chmod 644 "$DIST_DIR/$BUNDLE_NAME" "$DIST_DIR/$LATEST_BUNDLE" "$DIST_DIR/tdm-bundle.tar.gz"

echo "✅ Paquetes generados con éxito en:"
echo "   • $DIST_DIR/$BUNDLE_NAME"
echo "   • $DIST_DIR/$LATEST_BUNDLE"
echo "   • $DIST_DIR/tdm-bundle.tar.gz"
ls -lh "$DIST_DIR/$BUNDLE_NAME"
echo "====================================================="
