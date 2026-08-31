#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Termux Display Manager (TDM) - Generador y Compilador de APK de Android
# ==============================================================================
# Compila, empaqueta el Backend completo offline y firma el APK compatible con Android 7 a 15.
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$DIR/build"
DIST_DIR="$DIR/dist"
APP_DIR="$DIR/android-app"
SDK_JAR="$DIR/android-sdk/android.jar"

echo "====================================================="
echo "📱 [TDM] Compilación de APK Autónomo (100% Offline)"
echo "====================================================="

# 1. Verificar herramientas
echo "[1/6] Verificando herramientas de compilación..."
for tool in aapt2 javac d8 apksigner jarsigner zip tar keytool python3; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "❌ Herramienta faltante: $tool. Ejecuta: pkg install -y openjdk-17 aapt2 d8 apksigner zip"
        exit 1
    fi
done

if [ ! -f "$SDK_JAR" ]; then
    echo "❌ No se encontró $SDK_JAR"
    exit 1
fi

# 2. Preparar directorios de compilación
echo "[2/6] Preparando directorios de compilación..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/compiled_res" "$BUILD_DIR/gen" "$BUILD_DIR/obj" "$DIST_DIR"

# Empaquetar todo el código del backend TDM en un tarball autónomo para instalación sin Git
echo "[*] Generando tdm-bundle.tar.gz con el Backend completo..."
mkdir -p "$BUILD_DIR/assets"
tar -czf "$BUILD_DIR/assets/tdm-bundle.tar.gz" \
    -C "$DIR/.." \
    --exclude="termux-display-manager/android-app" \
    --exclude="termux-display-manager/build" \
    --exclude="termux-display-manager/dist" \
    --exclude="termux-display-manager/android-sdk" \
    --exclude="termux-display-manager/.git" \
    --exclude="termux-display-manager/**/__pycache__" \
    termux-display-manager

# Sincronizar assets web dentro del APK
echo "[*] Sincronizando assets web y noVNC dentro del APK..."
cp -r "$DIR"/tdm/web/* "$BUILD_DIR/assets/" 2>/dev/null || true

# 3. Compilar recursos con aapt2
echo "[3/6] Compilando recursos XML e iconos (aapt2 compile)..."
aapt2 compile --dir "$APP_DIR/res" -o "$BUILD_DIR/compiled_res.zip"

echo "[4/6] Enlazando APK base y generando R.java (aapt2 link con minSdkVersion=24)..."
aapt2 link \
    -I "$SDK_JAR" \
    --min-sdk-version 24 \
    --target-sdk-version 34 \
    --version-code 29 \
    --version-name "0.0.29" \
    --manifest "$APP_DIR/AndroidManifest.xml" \
    -A "$BUILD_DIR/assets" \
    -o "$BUILD_DIR/unaligned.apk" \
    --java "$BUILD_DIR/gen" \
    --auto-add-overlay \
    "$BUILD_DIR/compiled_res.zip"

# 4. Compilar código Java con compatibilidad Java 8
echo "[5/6] Compilando clases Java (javac --release 8)..."
javac \
    -cp "$SDK_JAR" \
    --release 8 \
    -d "$BUILD_DIR/obj" \
    "$BUILD_DIR/gen/com/termux/displaymanager/R.java" \
    "$APP_DIR"/src/com/termux/displaymanager/*.java

# 5. Convertir a bytecode Dalvik (d8 --min-api 24 -> classes.dex)
echo "[*] Generando bytecode Dalvik classes.dex (d8 --min-api 24)..."
d8 \
    --min-api 24 \
    --lib "$SDK_JAR" \
    --output "$BUILD_DIR/" \
    "$BUILD_DIR"/obj/com/termux/displaymanager/*.class

# Empaquetar classes.dex en el APK
(cd "$BUILD_DIR" && zip -uj unaligned.apk classes.dex)

# 6. Generar keystore si no existe
KEYSTORE="$BUILD_DIR/debug.keystore"
if [ ! -f "$KEYSTORE" ]; then
    keytool -genkeypair \
        -keystore "$KEYSTORE" \
        -alias androiddebugkey \
        -keypass android \
        -storepass android \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -dname "CN=TermuxDisplayManager, OU=TDM, O=Android, L=Local, ST=State, C=US" \
        2>/dev/null
fi

# Firma V1 previa con jarsigner
echo "[6/6] Firmando el APK (Esquemas V1, V2 y V3)..."
jarsigner \
    -sigalg SHA256withRSA \
    -digestalg SHA-256 \
    -keystore "$KEYSTORE" \
    -storepass android \
    -keypass android \
    "$BUILD_DIR/unaligned.apk" \
    androiddebugkey >/dev/null 2>&1

TARGET_APK="$DIST_DIR/termux-display-manager.apk"

apksigner sign \
    --ks "$KEYSTORE" \
    --ks-pass pass:android \
    --ks-key-alias androiddebugkey \
    --key-pass pass:android \
    --out "$TARGET_APK" \
    "$BUILD_DIR/unaligned.apk"

apksigner verify --verbose "$TARGET_APK"

echo "====================================================="
echo "🎉 ¡APK autónomo (100% Offline) generado y firmado con éxito!"
echo "📍 Ubicación: $TARGET_APK"
echo "📦 Tamaño: $(du -h "$TARGET_APK" | cut -f1)"
echo "📲 Backend TDM embebido en: assets/tdm-bundle.tar.gz"
echo "====================================================="
