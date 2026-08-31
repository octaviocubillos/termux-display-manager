#!/data/data/com.termux/files/usr/bin/bash
set -e

HOME="/data/data/com.termux/files/home"
PREFIX="/data/data/com.termux/files/usr"
export PATH="$PREFIX/bin:$PATH"

mkdir -p "$HOME/.ssh" "$PREFIX/etc/ssh" "$PREFIX/tmp" "$HOME/.tdm" 2>/dev/null || true
chmod 700 "$HOME/.ssh" 2>/dev/null || true
chmod 755 "$HOME" 2>/dev/null || true

# Generar host keys si no existen
if [ ! -f "$PREFIX/etc/ssh/ssh_host_ed25519_key" ]; then
    ssh-keygen -A 2>/dev/null || true
fi

# Si se generó una clave local, autorizarla
if [ -f "$HOME/.ssh/id_ed25519.pub" ]; then
    cat "$HOME/.ssh/id_ed25519.pub" >> "$HOME/.ssh/authorized_keys" 2>/dev/null || true
fi
if [ -f "$HOME/.ssh/id_rsa.pub" ]; then
    cat "$HOME/.ssh/id_rsa.pub" >> "$HOME/.ssh/authorized_keys" 2>/dev/null || true
fi
if [ -f "$HOME/.ssh/authorized_keys" ]; then
    chmod 600 "$HOME/.ssh/authorized_keys" 2>/dev/null || true
fi

# Symlink de conveniencia al repo
if [ ! -e "$HOME/termux-display-manager" ] && [ -d "/data/data/com.termux/files/termux-display-manager" ]; then
    ln -s /data/data/com.termux/files/termux-display-manager "$HOME/termux-display-manager" 2>/dev/null || true
fi

# Iniciar sshd en puerto 8022 con StrictModes=no
echo "[*] Iniciando OpenSSH Server en puerto 8022..."
pkill sshd 2>/dev/null || true
"$PREFIX/bin/sshd" -p 8022 -o StrictModes=no -o PubkeyAuthentication=yes -o PasswordAuthentication=yes 2>/dev/null || true

echo "====================================================="
echo "📱 [Termux Docker] Contenedor Activo y Listo"
echo "🔑 SSH:   ssh -p 8022 system@localhost"
echo "💻 Shell: docker exec -it termux-local bash"
echo "📂 Home:  $HOME (Montado en ./termux-home)"
echo "====================================================="

if [ $# -gt 0 ]; then
    exec "$@"
else
    exec tail -f /dev/null
fi
