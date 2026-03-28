#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - MQTT User Creation Script
# =============================================================================
# Bu script MQTT broker için güvenli kullanıcı hesapları oluşturur.
# Kullanım: sudo ./create_mqtt_users.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MQTT_CONFIG_DIR="$SCRIPT_DIR/../mqtt-broker"
PASSWD_FILE="$MQTT_CONFIG_DIR/passwd"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Functions
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

print_header() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║     Sumatic Modern IoT - MQTT User Creation                   ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "Bu script root olarak çalıştırılmalıdır (sudo kullanın)"
        exit 1
    fi
}

# Check if mosquitto_passwd is installed
check_dependencies() {
    if ! command -v mosquitto_passwd &> /dev/null; then
        print_error "mosquitto_passwd bulunamadı. Mosquitto broker'ı kurun:"
        echo "  Ubuntu/Debian: sudo apt-get install mosquitto mosquitto-clients"
        echo "  CentOS/RHEL: sudo yum install mosquitto"
        exit 1
    fi
    print_success "Mosquitto araçları bulundu"
}

# Create password file
create_password_file() {
    print_info "MQTT password dosyası oluşturuluyor..."
    
    # Create mqtt-broker directory if it doesn't exist
    mkdir -p "$MQTT_CONFIG_DIR"
    
    # Remove existing password file if requested
    if [[ -f "$PASSWD_FILE" ]]; then
        print_warning "Password dosyası zaten mevcut: $PASSWD_FILE"
        read -p "Mevcut dosya üzerine yazılsın mı? (yes/no): " OVERWRITE
        if [[ $OVERWRITE == "yes" ]]; then
            rm -f "$PASSWD_FILE"
            print_info "Mevcut password dosyası silindi"
        else
            print_info "Mevcut password dosyası korunuyor"
            return 0
        fi
    fi
    
    # Create new password file
    touch "$PASSWD_FILE"
    chmod 640 "$PASSWD_FILE"
    print_success "Password dosyası oluşturuldu: $PASSWD_FILE"
}

# Generate secure random password
generate_password() {
    local length=${1:-24}
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-${length}
}

# Create backend user
create_backend_user() {
    print_info "Backend kullanıcısı oluşturuluyor..."
    
    read -p "Backend kullanıcı adı [sumatic-backend]: " BACKEND_USER
    BACKEND_USER=${BACKEND_USER:-sumatic-backend}
    
    read -sp "Backend şifresi (boş bırakılırsa rastgele oluşturulur): " BACKEND_PASS
    echo ""
    
    if [[ -z "$BACKEND_PASS" ]]; then
        BACKEND_PASS=$(generate_password 24)
        print_warning "Rastgele şifre oluşturuldu"
    fi
    
    mosquitto_passwd -b "$PASSWD_FILE" "$BACKEND_USER" "$BACKEND_PASS"
    print_success "Backend kullanıcısı oluşturuldu: $BACKEND_USER"
    
    # Save credentials to secure file
    cat > "$MQTT_CONFIG_DIR/.backend_credentials" << EOF
# MQTT Backend Credentials
# WARNING: Keep this file secure and restrict access!
MQTT_USERNAME=$BACKEND_USER
MQTT_PASSWORD=$BACKEND_PASS
EOF
    chmod 600 "$MQTT_CONFIG_DIR/.backend_credentials"
    print_warning "Kimlik bilgileri $MQTT_CONFIG_DIR/.backend_credentials dosyasına kaydedildi"
}

# Create dashboard user
create_dashboard_user() {
    print_info "Dashboard kullanıcısı oluşturuluyor..."
    
    read -p "Dashboard kullanıcı adı [dashboard]: " DASHBOARD_USER
    DASHBOARD_USER=${DASHBOARD_USER:-dashboard}
    
    read -sp "Dashboard şifresi (boş bırakılırsa rastgele oluşturulur): " DASHBOARD_PASS
    echo ""
    
    if [[ -z "$DASHBOARD_PASS" ]]; then
        DASHBOARD_PASS=$(generate_password 24)
        print_warning "Rastgele şifre oluşturuldu"
    fi
    
    mosquitto_passwd -b "$PASSWD_FILE" "$DASHBOARD_USER" "$DASHBOARD_PASS"
    print_success "Dashboard kullanıcısı oluşturuldu: $DASHBOARD_USER"
}

# Create admin user
create_admin_user() {
    print_info "Admin kullanıcısı oluşturuluyor..."
    
    read -p "Admin kullanıcı adı [admin]: " ADMIN_USER
    ADMIN_USER=${ADMIN_USER:-admin}
    
    read -sp "Admin şifresi (boş bırakılırsa rastgele oluşturulur): " ADMIN_PASS
    echo ""
    
    if [[ -z "$ADMIN_PASS" ]]; then
        ADMIN_PASS=$(generate_password 24)
        print_warning "Rastgele şifre oluşturuldu"
    fi
    
    mosquitto_passwd -b "$PASSWD_FILE" "$ADMIN_USER" "$ADMIN_PASS"
    print_success "Admin kullanıcısı oluşturuldu: $ADMIN_USER"
}

# Create device users
create_device_users() {
    print_info "Cihaz kullanıcıları oluşturuluyor..."
    
    read -p "Kaç adet cihaz kullanıcısı oluşturulacak? " DEVICE_COUNT
    
    if [[ -z "$DEVICE_COUNT" || $DEVICE_COUNT -le 0 ]]; then
        print_info "Cihaz kullanıcısı oluşturulmadı"
        return
    fi
    
    for ((i=1; i<=DEVICE_COUNT; i++)); do
        read -p "Cihaz $i kullanıcı adı (örn: device_001): " DEVICE_USER
        
        if [[ -z "$DEVICE_USER" ]]; then
            DEVICE_USER="device_$(printf "%03d" $i)"
        fi
        
        read -sp "$DEVICE_USER şifresi (boş bırakılırsa rastgele oluşturulur): " DEVICE_PASS
        echo ""
        
        if [[ -z "$DEVICE_PASS" ]]; then
            DEVICE_PASS=$(generate_password 16)
            print_warning "Rastgele şifre oluşturuldu"
        fi
        
        mosquitto_passwd -b "$PASSWD_FILE" "$DEVICE_USER" "$DEVICE_PASS"
        print_success "Cihaz kullanıcısı oluşturuldu: $DEVICE_USER"
        
        # Add to device credentials file
        echo "$DEVICE_USER:$DEVICE_PASS" >> "$MQTT_CONFIG_DIR/.device_credentials"
    done
    
    if [[ -f "$MQTT_CONFIG_DIR/.device_credentials" ]]; then
        chmod 600 "$MQTT_CONFIG_DIR/.device_credentials"
        print_warning "Cihaz kimlik bilgileri $MQTT_CONFIG_DIR/.device_credentials dosyasına kaydedildi"
    fi
}

# Update ACL file for device users
update_acl_for_devices() {
    print_info "ACL dosyası güncelleniyor..."
    
    ACL_FILE="$MQTT_CONFIG_DIR/acl"
    
    if [[ ! -f "$ACL_FILE" ]]; then
        print_error "ACL dosyası bulunamadı: $ACL_FILE"
        return
    fi
    
    # Check if device credentials file exists
    if [[ ! -f "$MQTT_CONFIG_DIR/.device_credentials" ]]; then
        print_info "Cihaz kimlik bilgisi dosyası bulunamadı, ACL güncellenmedi"
        return
    fi
    
    print_info "ACL dosyasına cihaz kullanıcıları ekleniyor..."
    print_warning "ACL dosyasını manuel olarak düzenlemeniz gerekebilir"
}

# Display summary
display_summary() {
    print_header "Kullanıcı Oluşturma Özeti"
    
    echo ""
    echo "Oluşturulan kullanıcılar:"
    mosquitto_passwd -c "$PASSWD_FILE" -b 2>/dev/null || cat "$PASSWD_FILE" | grep -v "^#" | cut -d: -f1
    echo ""
    
    echo "Dosyalar:"
    echo "  - Password dosyası: $PASSWD_FILE"
    echo "  - ACL dosyası:      $MQTT_CONFIG_DIR/acl"
    echo "  - Backend creds:    $MQTT_CONFIG_DIR/.backend_credentials"
    echo "  - Device creds:     $MQTT_CONFIG_DIR/.device_credentials"
    echo ""
    
    print_warning "GÜVENLİK UYARILARI:"
    echo "  1. Kimlik bilgileri içeren dosyaları güvenli saklayın"
    echo "  2. .credentials dosyalarının izinleri 600 olarak ayarlandı"
    echo "  3. Bu dosyaları versiyon kontrol sistemine eklemeyin (.gitignore)"
    echo "  4. Production'da güçlü, benzersiz şifreler kullanın"
    echo ""
    
    print_success "MQTT kullanıcıları başarıyla oluşturuldu!"
    echo ""
    echo "Sonraki adımlar:"
    echo "  1. ACL dosyasını düzenleyin: $MQTT_CONFIG_DIR/acl"
    echo "  2. Mosquitto'yu yeniden başlatın: docker-compose restart mqtt"
    echo "  3. Bağlantıyı test edin: ./test_mqtt_connection.sh"
}

# Main execution
main() {
    print_header
    
    check_root
    check_dependencies
    create_password_file
    
    echo ""
    read -p "Backend kullanıcısı oluşturulsun mu? (yes/no): " CREATE_BACKEND
    if [[ $CREATE_BACKEND == "yes" ]]; then
        create_backend_user
    fi
    
    echo ""
    read -p "Dashboard kullanıcısı oluşturulsun mu? (yes/no): " CREATE_DASHBOARD
    if [[ $CREATE_DASHBOARD == "yes" ]]; then
        create_dashboard_user
    fi
    
    echo ""
    read -p "Admin kullanıcısı oluşturulsun mu? (yes/no): " CREATE_ADMIN
    if [[ $CREATE_ADMIN == "yes" ]]; then
        create_admin_user
    fi
    
    echo ""
    read -p "Cihaz kullanıcıları oluşturulsun mu? (yes/no): " CREATE_DEVICES
    if [[ $CREATE_DEVICES == "yes" ]]; then
        create_device_users
        update_acl_for_devices
    fi
    
    echo ""
    display_summary
}

# Run main
main "$@"
