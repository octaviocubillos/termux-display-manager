#!/bin/sh
# ==============================================================================
# Termux Display Manager (TDM) - Configuración de Firewall (nftables / ufw)
# ==============================================================================
set -e

echo "🔒 [TDM Firewall] Configurando reglas para puertos 19050-19055..."

# 1. Caso nftables (postmarketOS / Alpine / Debian nftables)
if [ -d "/etc/nftables.d" ]; then
    echo "[*] Configurando regla nftables en /etc/nftables.d/50_tdm.nft..."
    cat << 'NFT_EOF' | tee /etc/nftables.d/50_tdm.nft > /dev/null
#!/usr/sbin/nft -f

table inet filter {
	chain input {
		tcp dport 19050-19055 accept comment "accept TDM services (PWA, noVNC, VNC, RDP, Audio)"
	}
}
NFT_EOF
    chmod 644 /etc/nftables.d/50_tdm.nft
    if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet nftables; then
        systemctl restart nftables
    elif command -v rc-service >/dev/null 2>&1 && rc-service nftables status >/dev/null 2>&1; then
        rc-service nftables restart
    elif command -v nft >/dev/null 2>&1; then
        nft -f /etc/nftables.nft 2>/dev/null || nft add rule inet filter input tcp dport 19050-19055 accept
    fi
    echo "✅ Reglas de nftables aplicadas y activas."
fi

# 2. Caso UFW (Ubuntu / Debian con ufw)
if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q "Status: active"; then
    echo "[*] Abriendo puertos 19050:19055/tcp en UFW..."
    ufw allow 19050:19055/tcp comment "TDM Services"
    echo "✅ Reglas UFW aplicadas."
fi

# 3. Caso firewalld (Fedora / RHEL)
if command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
    echo "[*] Abriendo puertos en firewalld..."
    firewall-cmd --add-port=19050-19055/tcp --permanent
    firewall-cmd --reload
    echo "✅ Reglas firewalld aplicadas."
fi

echo "====================================================="
echo "🎉 ¡Puertos 19050 a 19055 abiertos correctamente para la red LAN!"
echo "====================================================="
