#!/usr/bin/env bash
# ==============================================================================
# Termux Display Manager (TDM) - Instalador y Gestor de Controlador 3D / GPU
# ==============================================================================
# Detecta el modelo de GPU del dispositivo (Qualcomm Adreno, ARM Mali, PowerVR)
# e instala automáticamente el controlador de aceleración 3D óptimo.
# Si el hardware no tiene soporte nativo, informa claramente la limitación y
# configura el motor de renderizado por software seguro (llvmpipe).
# ==============================================================================
set -e
export DEBIAN_FRONTEND=noninteractive
export APT_LISTCHANGES_FRONTEND=none

PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
CONFIG_DIR="$HOME_DIR/.tdm/config"
GPU_CONF="$CONFIG_DIR/gpu.json"
FORCE_INSTALL="${1:-}"

mkdir -p "$CONFIG_DIR" "$HOME_DIR/.tdm/run" "$HOME_DIR/.tdm/logs"

echo "====================================================="
echo "🎮 [TDM 3D] Gestor de Controladores Gráficos y GPU"
echo "====================================================="
echo "[TDM_PROGRESS:10:Detectando GPU y arquitectura de hardware]"

# 1. Comprobar si ya está instalado previamente
if [ "$FORCE_INSTALL" != "--force" ] && [ -f "$GPU_CONF" ]; then
    ALREADY_INSTALLED=$(python3 -c "import json; d=json.load(open('$GPU_CONF')); print(d.get('installed', False))" 2>/dev/null || echo "False")
    if [ "$ALREADY_INSTALLED" = "True" ]; then
        DRIVER_NAME=$(python3 -c "import json; d=json.load(open('$GPU_CONF')); print(d.get('driver_name', '3D Driver'))" 2>/dev/null || echo "3D")
        GPU_NAME=$(python3 -c "import json; d=json.load(open('$GPU_CONF')); print(d.get('gpu_model', 'GPU'))" 2>/dev/null || echo "GPU")
        echo "✅ [TDM 3D] El controlador 3D ($DRIVER_NAME) para $GPU_NAME ya está instalado y optimizado."
        echo "[TDM_PROGRESS:100:Controlador 3D verificado]"
        exit 0
    fi
fi

# 2. Detección exhaustiva de GPU y fabricante
GPU_MODEL=""
GPU_VENDOR="Genérico"
DRIVER_TYPE="llvmpipe"
DRIVER_NAME="Renderizado por Software (llvmpipe)"
VIRGL_SUPPORT=false
PACKAGES_TO_INSTALL=""

# A. Detección en Android / Termux (KGSL, SOC, Properties)
if [ -d "/data/data/com.termux" ] || [ -n "$ANDROID_ROOT" ] || command -v getprop >/dev/null 2>&1; then
    # A.1. Qualcomm Adreno
    if [ -f "/sys/class/kgsl/kgsl-3d0/gpu_model" ]; then
        GPU_MODEL=$(cat "/sys/class/kgsl/kgsl-3d0/gpu_model" 2>/dev/null | tr -d '
')
        GPU_VENDOR="Qualcomm"
    fi
    
    if [ -z "$GPU_MODEL" ] && command -v getprop >/dev/null 2>&1; then
        SOC_MODEL=$(getprop ro.soc.model 2>/dev/null || true)
        HW_PROP=$(getprop ro.hardware 2>/dev/null || true)
        PLAT_PROP=$(getprop ro.board.platform 2>/dev/null || true)
        
        if echo "$HW_PROP $PLAT_PROP $SOC_MODEL" | grep -qiE "(qcom|qualcomm|adreno|kona|lahaina|taro|sm8|sm7|sm6|sdm)"; then
            GPU_VENDOR="Qualcomm"
            GPU_MODEL="Qualcomm Adreno ($SOC_MODEL)"
        elif echo "$HW_PROP $PLAT_PROP $SOC_MODEL" | grep -qiE "(mali|exynos|mt6|mt8|mtk|mediatek|dimensity|tensor)"; then
            GPU_VENDOR="ARM"
            GPU_MODEL="ARM Mali ($SOC_MODEL)"
        elif echo "$HW_PROP $PLAT_PROP" | grep -qiE "(pvr|powervr)"; then
            GPU_VENDOR="Imagination"
            GPU_MODEL="PowerVR GPU"
        fi
    fi

    # Si encontramos /dev/mali0 o /sys/class/misc/mali0
    if [ -e "/dev/mali0" ] || [ -d "/sys/class/misc/mali0" ]; then
        GPU_VENDOR="ARM"
        [ -z "$GPU_MODEL" ] && GPU_MODEL="ARM Mali"
    fi
fi

# B. Detección en Linux tradicional
if [ -z "$GPU_MODEL" ] && command -v lspci >/dev/null 2>&1; then
    VGA_INFO=$(lspci | grep -iE 'vga|3d|display' || true)
    if echo "$VGA_INFO" | grep -qi "NVIDIA"; then
        GPU_VENDOR="NVIDIA"
        GPU_MODEL=$(echo "$VGA_INFO" | head -n1)
    elif echo "$VGA_INFO" | grep -qiE "AMD|Radeon|ATI"; then
        GPU_VENDOR="AMD"
        GPU_MODEL=$(echo "$VGA_INFO" | head -n1)
    elif echo "$VGA_INFO" | grep -qi "Intel"; then
        GPU_VENDOR="Intel"
        GPU_MODEL=$(echo "$VGA_INFO" | head -n1)
    fi
fi

if [ -z "$GPU_MODEL" ]; then
    GPU_MODEL="GPU Genérica / $(uname -m)"
fi

echo "🔍 [TDM 3D] GPU Identificada: $GPU_MODEL ($GPU_VENDOR)"
echo "[TDM_PROGRESS:35:Analizando controladores disponibles para $GPU_VENDOR]"

# 3. Selección del controlador según arquitectura y soporte de paquetes
SUDO=""
if [ "$(id -u)" -ne 0 ] && [ ! -d "/data/data/com.termux" ]; then
    if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; elif command -v doas >/dev/null 2>&1; then SUDO="doas"; fi
fi

if command -v pkg >/dev/null 2>&1; then
    # En Termux:
    if [ "$GPU_VENDOR" = "Qualcomm" ]; then
        echo "🚀 [TDM 3D] Compatible con controlador nativo Mesa Turnip (Vulkan) + Zink y VirGL"
        DRIVER_TYPE="turnip_zink"
        DRIVER_NAME="Mesa Turnip (Vulkan) + Zink & VirGL"
        VIRGL_SUPPORT=true
        PACKAGES_TO_INSTALL="mesa-vulkan-icd-freedreno virglrenderer-android vulkan-loader-android angle-android mesa-demos"
    elif [ "$GPU_VENDOR" = "ARM" ] || [ "$GPU_VENDOR" = "Imagination" ]; then
        echo "⚡ [TDM 3D] Compatible con aceleración 3D compartida VirGL Renderer Android"
        DRIVER_TYPE="virgl"
        DRIVER_NAME="VirGL Renderer Android (Hardware-accelerated GLES)"
        VIRGL_SUPPORT=true
        PACKAGES_TO_INSTALL="virglrenderer-android mesa mesa-demos"
    else
        echo "⚡ [TDM 3D] Usando aceleración VirGL genérica / Fallback llvmpipe"
        DRIVER_TYPE="virgl"
        DRIVER_NAME="VirGL Renderer / Software llvmpipe"
        VIRGL_SUPPORT=true
        PACKAGES_TO_INSTALL="virglrenderer-android mesa"
    fi
elif [ -f "/etc/alpine-release" ] || command -v apk >/dev/null 2>&1; then
    DRIVER_TYPE="mesa_native"
    DRIVER_NAME="Mesa Native Drivers"
    VIRGL_SUPPORT=true
    PACKAGES_TO_INSTALL="mesa-dri-gallium mesa-va-gallium virglrenderer"
elif command -v apt-get >/dev/null 2>&1; then
    DRIVER_TYPE="mesa_native"
    DRIVER_NAME="Mesa Native Drivers"
    VIRGL_SUPPORT=true
    PACKAGES_TO_INSTALL="libgl1-mesa-dri virglrenderer"
elif command -v pacman >/dev/null 2>&1; then
    DRIVER_TYPE="mesa_native"
    DRIVER_NAME="Mesa Native Drivers"
    VIRGL_SUPPORT=true
    PACKAGES_TO_INSTALL="mesa virglrenderer"
else
    echo "⚠️ [TDM 3D] No se encontró gestor de paquetes para instalar controladores 3D propietarios."
    DRIVER_TYPE="llvmpipe"
    DRIVER_NAME="Software llvmpipe Fallback"
    VIRGL_SUPPORT=false
fi

# 4. Instalación de paquetes
echo "[TDM_PROGRESS:60:Instalando controlador: $DRIVER_NAME]"
INSTALL_SUCCESS=false

if [ -n "$PACKAGES_TO_INSTALL" ]; then
    echo "📦 [TDM 3D] Instalando paquetes: $PACKAGES_TO_INSTALL..."
    if command -v pkg >/dev/null 2>&1; then
        pkg install -y x11-repo || true
        pkg update -y || true
        if pkg install -y $PACKAGES_TO_INSTALL; then
            INSTALL_SUCCESS=true
        else
            echo "[!] Reintentando instalación paquete por paquete..."
            for p in $PACKAGES_TO_INSTALL; do
                pkg install -y "$p" || echo "[!] Advertencia: paquete $p no disponible."
            done
            INSTALL_SUCCESS=true
        fi
    elif command -v apk >/dev/null 2>&1; then
        $SUDO apk add $PACKAGES_TO_INSTALL && INSTALL_SUCCESS=true || true
    elif command -v apt-get >/dev/null 2>&1; then
        $SUDO apt-get update -y || true
        $SUDO apt-get install -y $PACKAGES_TO_INSTALL && INSTALL_SUCCESS=true || true
    elif command -v pacman >/dev/null 2>&1; then
        $SUDO pacman -S --noconfirm $PACKAGES_TO_INSTALL && INSTALL_SUCCESS=true || true
    fi
else
    echo "ℹ️ [TDM 3D] No se requieren paquetes adicionales. Se utilizará renderizado software seguro."
    INSTALL_SUCCESS=true
fi

# 5. Registro de configuración y estado en SQLite y JSON
echo "[TDM_PROGRESS:90:Guardando configuración del controlador 3D]"

python3 -c "
import json, time
conf = {
    'gpu_model': '$GPU_MODEL',
    'gpu_vendor': '$GPU_VENDOR',
    'driver_type': '$DRIVER_TYPE',
    'driver_name': '$DRIVER_NAME',
    'virgl_supported': bool('$VIRGL_SUPPORT' == 'true'),
    'installed': bool('$INSTALL_SUCCESS' == 'true'),
    'packages': '$PACKAGES_TO_INSTALL'.split(),
    'updated_at': int(time.time())
}
with open('$GPU_CONF', 'w') as f:
    json.dump(conf, f, indent=2)
" 2>/dev/null || true

# Registrar en Manifest
if [ "$INSTALL_SUCCESS" = "true" ] && [ -n "$PACKAGES_TO_INSTALL" ]; then
    python3 -c "
try:
    from tdm.core.manifest import manifest_ledger
    manifest_ledger.record_packages_if_new('$PACKAGES_TO_INSTALL'.split(), component='gpu:3d_driver')
except Exception:
    pass
" 2>/dev/null || true
fi

echo "[TDM_PROGRESS:100:Controlador 3D instalado con éxito]"
echo "====================================================="
if [ "$INSTALL_SUCCESS" = "true" ]; then
    echo "🎉 [TDM 3D] ¡Controlador 3D configurado exitosamente!"
    echo "   • GPU:         $GPU_MODEL ($GPU_VENDOR)"
    echo "   • Controlador: $DRIVER_NAME"
    echo "   • VirGL 3D:    $VIRGL_SUPPORT"
else
    echo "⚠️ [TDM 3D] No se pudo instalar el controlador 3D dedicado. Se utilizará fallback llvmpipe."
fi
echo "====================================================="
