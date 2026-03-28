#!/bin/bash
# ==============================================================================
# Sumatic Modern IoT - Coolify SSH Key Setup Script
# ==============================================================================
# Bu script Coolify deployment için SSH key yapılandırmasını hazırlar.
# SSH key, remote MQTT sunucusuna tunnel oluşturmak için kullanılır.
# ==============================================================================

set -e

# Renkli çıktı
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}  Sumatic Modern IoT - SSH Key Setup (Coolify)${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""

# SSH key path
SSH_KEY_NAME="sumatic_tunnel_key"
SSH_KEY_PATH="$HOME/.ssh/${SSH_KEY_NAME}"

echo -e "${BLUE}Adım 1: SSH Key Oluşturma${NC}"
echo "================================"

# Mevcut key kontrolü
if [ -f "$SSH_KEY_PATH" ]; then
    echo -e "${YELLOW}SSH key zaten mevcut: ${SSH_KEY_PATH}${NC}"
    read -p "Yeni bir key oluşturmak istiyor musunuz? (e/H): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ee]$ ]]; then
        echo -e "${GREEN}Mevcut key kullanılacak.${NC}"
    else
        rm -f "${SSH_KEY_PATH}" "${SSH_KEY_PATH}.pub"
        echo -e "${GREEN}Eski key silindi.${NC}"
    fi
fi

# Yeni key oluştur
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo -e "${GREEN}Yeni SSH key oluşturuluyor...${NC}"
    ssh-keygen -t ed25519 -a 100 -f "$SSH_KEY_PATH" -N "" -C "sumatic-tunnel@coolify"
    echo -e "${GREEN}✓ SSH key oluşturuldu: ${SSH_KEY_PATH}${NC}"
else
    echo -e "${GREEN}✓ Mevcut SSH key kullanılıyor: ${SSH_KEY_PATH}${NC}"
fi

echo ""
echo -e "${BLUE}Adım 2: Public Key${NC}"
echo "================================"
echo -e "${YELLOW}Aşağıdaki public key'i remote MQTT sunucusuna ekleyin:${NC}"
echo ""
echo -e "${GREEN}$(cat ${SSH_KEY_PATH}.pub)${NC}"
echo ""

# Public key'i kopyala
if command -v pbcopy > /dev/null; then
    cat "${SSH_KEY_PATH}.pub" | pbcopy
    echo -e "${GREEN}✓ Public key panoya kopyalandı (macOS)${NC}"
elif command -v clip > /dev/null; then
    cat "${SSH_KEY_PATH}.pub" | clip
    echo -e "${GREEN}✓ Public key panoya kopyalandı (Windows)${NC}"
elif command -v xclip > /dev/null; then
    cat "${SSH_KEY_PATH}.pub" | xclip -selection clipboard
    echo -e "${GREEN}✓ Public key panoya kopyalandı (Linux)${NC}"
fi

echo ""
echo -e "${BLUE}Adım 3: Remote Sunucuya Key Ekleme${NC}"
echo "================================"
echo -e "${YELLOW}Remote sunucuda şu komutu çalıştırın:${NC}"
echo ""
echo -e "${GREEN}echo '$(cat ${SSH_KEY_PATH}.pub)' >> ~/.ssh/authorized_keys${NC}"
echo ""
echo -e "${YELLOW}Veya manuel olarak:${NC}"
echo "  1. Remote sunucuya SSH ile bağlanın"
echo "  2. ~/.ssh/authorized_keys dosyasına public key'i ekleyin"
echo "  3. SSH config'i kontrol edin"

echo ""
echo -e "${BLUE}Adım 4: SSH Bağlantı Testi${NC}"
echo "================================"

# SSH_HOST kontrolü
if [ -z "$SSH_HOST" ]; then
    echo -e "${YELLOW}SSH_HOST environment variable tanımlı değil.${NC}"
    read -p "Remote MQTT sunucu IP adresi: " SSH_HOST_INPUT
    SSH_HOST=$SSH_HOST_INPUT
fi

if [ -z "$SSH_USER" ]; then
    SSH_USER="sumatic-tunnel"
fi

echo -e "${GREEN}SSH bağlantısı test ediliyor...${NC}"
echo "  Host: ${SSH_HOST}"
echo "  User: ${SSH_USER}"
echo "  Key: ${SSH_KEY_PATH}"
echo ""

# Test connection
if ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "${SSH_USER}@${SSH_HOST}" "echo 'SSH bağlantısı başarılı!'" 2>/dev/null; then
    echo -e "${GREEN}✓ SSH bağlantısı başarılı!${NC}"
else
    echo -e "${RED}✗ SSH bağlantısı başarısız!${NC}"
    echo -e "${YELLOW}Kontrol edilecekler:${NC}"
    echo "  1. Public key remote sunucuya eklendi mi?"
    echo "  2. SSH kullanıcısı doğru mu?"
    echo "  3. Firewall SSH portuna (22) izin veriyor mu?"
    echo "  4. SSH servisi remote sunucuda çalışıyor mu?"
fi

echo ""
echo -e "${BLUE}Adım 5: Coolify Secret Hazırlama${NC}"
echo "================================"
echo -e "${YELLOW}Aşağıdaki private key'i Coolify'da secret olarak ekleyin:${NC}"
echo ""
echo -e "${GREEN}Secret Name: SSH_PRIVATE_KEY${NC}"
echo -e "${GREEN}Secret Value:${NC}"
echo ""
cat "$SSH_KEY_PATH"
echo ""
echo -e "${YELLOW}Nasıl eklenir:${NC}"
echo "  1. Coolify dashboard'da projenize gidin"
echo "  2. Servis seçin > Environment Variables"
echo "  3. 'Add Secret' butonuna tıklayın"
echo "  4. Name: SSH_PRIVATE_KEY"
echo "  5. Value: (yukarıdaki private key)"
echo "  6. 'Add' butonuna tıklayın"

echo ""
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}  SSH Key Setup Tamamlandı!${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""
echo -e "${YELLOW}Önemli Dosyalar:${NC}"
echo "  Private Key: ${SSH_KEY_PATH}"
echo "  Public Key: ${SSH_KEY_PATH}.pub"
echo ""
echo -e "${RED}GÜVENLİK UYARISI:${NC}"
echo "  - Private key'i asla kimseyle paylaşmayın!"
echo "  - Private key'i git'e commit etmeyin!"
echo "  - Private key'i güvenli bir yerde saklayın!"
echo ""
