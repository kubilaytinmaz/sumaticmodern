#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - SSH Tunnel to Direct MQTT Migration Script
# =============================================================================
# Bu script SSH tünelinden doğrudan MQTT bağlantısına geçiş yapar.
# Kullanım: sudo ./migrate_to_direct_mqtt.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
    echo "║  SSH Tunnel → Direct MQTT Migration Script                     ║"
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

# Pre-migration checks
pre_migration_checks() {
    print_header "Geçiş Öncesi Kontroller"
    
    local all_ok=true
    
    # Check if certificates exist
    print_info "TLS sertifikaları kontrol ediliyor..."
    if [[ -f "$PROJECT_ROOT/mqtt-broker/certs/ca.crt" && \
          -f "$PROJECT_ROOT/mqtt-broker/certs/mqtt-server.crt" && \
          -f "$PROJECT_ROOT/mqtt-broker/certs/mqtt-server.key" ]]; then
        print_success "TLS sertifikaları bulundu"
    else
        print_error "TLS sertifikaları bulunamadı!"
        print_info "Sertifikaları oluşturun: sudo ./generate_mqtt_certs.sh"
        all_ok=false
    fi
    
    # Check if password file exists
    print_info "MQTT password dosyası kontrol ediliyor..."
    if [[ -f "$PROJECT_ROOT/mqtt-broker/passwd" ]]; then
        print_success "Password dosyası bulundu"
    else
        print_error "Password dosyası bulunamadı!"
        print_info "Kullanıcıları oluşturun: sudo ./create_mqtt_users.sh"
        all_ok=false
    fi
    
    # Check if ACL file exists
    print_info "MQTT ACL dosyası kontrol ediliyor..."
    if [[ -f "$PROJECT_ROOT/mqtt-broker/acl" ]]; then
        print_success "ACL dosyası bulundu"
    else
        print_error "ACL dosyası bulunamadı!"
        all_ok=false
    fi
    
    # Check if production mosquitto.conf exists
    print_info "Production mosquitto.conf kontrol ediliyor..."
    if [[ -f "$PROJECT_ROOT/mqtt-broker/mosquitto.conf.production" ]]; then
        print_success "Production mosquitto.conf bulundu"
    else
        print_error "Production mosquitto.conf bulunamadı!"
        all_ok=false
    fi
    
    # Check Docker
    print_info "Docker kontrol ediliyor..."
    if command -v docker &> /dev/null; then
        print_success "Docker yüklü"
    else
        print_error "Docker bulunamadı!"
        all_ok=false
    fi
    
    # Check Docker Compose
    print_info "Docker Compose kontrol ediliyor..."
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        print_success "Docker Compose yüklü"
    else
        print_error "Docker Compose bulunamadı!"
        all_ok=false
    fi
    
    if [[ "$all_ok" == "false" ]]; then
        print_error "Geçiş öncesi kontroller başarısız!"
        exit 1
    fi
    
    print_success "Tüm geçiş öncesi kontroller başarılı!"
    echo ""
}

# Backup current configuration
backup_config() {
    print_info "Mevcut yapılandırma yedekleniyor..."
    
    local backup_dir="$PROJECT_ROOT/backups/migration-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup backend .env
    if [[ -f "$PROJECT_ROOT/backend/.env" ]]; then
        cp "$PROJECT_ROOT/backend/.env" "$backup_dir/backend.env.backup"
        print_success "Backend .env yedeklendi"
    fi
    
    # Backup docker-compose.prod.yml
    if [[ -f "$PROJECT_ROOT/docker-compose.prod.yml" ]]; then
        cp "$PROJECT_ROOT/docker-compose.prod.yml" "$backup_dir/docker-compose.prod.yml.backup"
        print_success "docker-compose.prod.yml yedeklendi"
    fi
    
    # Backup current mosquitto.conf
    if [[ -f "$PROJECT_ROOT/mqtt-broker/mosquitto.conf" ]]; then
        cp "$PROJECT_ROOT/mqtt-broker/mosquitto.conf" "$backup_dir/mosquitto.conf.backup"
        print_success "mosquitto.conf yedeklendi"
    fi
    
    echo "Yedekleme konumu: $backup_dir"
    echo ""
}

# Update backend configuration
update_backend_config() {
    print_info "Backend yapılandırması güncelleniyor..."
    
    local env_file="$PROJECT_ROOT/backend/.env"
    
    if [[ ! -f "$env_file" ]]; then
        print_error "Backend .env dosyası bulunamadı: $env_file"
        return 1
    fi
    
    # Backup the original file
    cp "$env_file" "$env_file.pre-migration"
    
    # Update configuration
    print_info "SSH tüneli devre dışı bırakılıyor..."
    sed -i 's/^SSH_ENABLED=.*/SSH_ENABLED=false/' "$env_file"
    
    print_info "MQTT TLS etkinleştiriliyor..."
    sed -i 's/^MQTT_TLS_ENABLED=.*/MQTT_TLS_ENABLED=true/' "$env_file"
    
    # Ask for broker host
    read -p "MQTT Broker IP adresi veya hostname: " BROKER_HOST
    if [[ -n "$BROKER_HOST" ]]; then
        sed -i "s/^MQTT_BROKER_HOST=.*/MQTT_BROKER_HOST=$BROKER_HOST/" "$env_file"
    fi
    
    # Update port to TLS port
    sed -i 's/^MQTT_BROKER_PORT=.*/MQTT_BROKER_PORT=8883/' "$env_file"
    
    # Add TLS certificate paths if not present
    if ! grep -q "MQTT_TLS_CA_CERT" "$env_file"; then
        cat >> "$env_file" << 'EOF'

# MQTT TLS Certificate Paths
MQTT_TLS_CA_CERT=/app/mqtt-certs/ca.crt
MQTT_TLS_CLIENT_CERT=/app/mqtt-certs/client.crt
MQTT_TLS_CLIENT_KEY=/app/mqtt-certs/client.key
MQTT_TLS_REQUIRE_CERT=false
MQTT_TLS_INSECURE=false
EOF
    fi
    
    print_success "Backend yapılandırması güncellendi"
    print_warning "Orijinal dosya: $env_file.pre-migration"
    echo ""
}

# Update mosquitto configuration
update_mosquitto_config() {
    print_info "Mosquitto yapılandırması güncelleniyor..."
    
    local conf_file="$PROJECT_ROOT/mqtt-broker/mosquitto.conf"
    local prod_conf="$PROJECT_ROOT/mqtt-broker/mosquitto.conf.production"
    
    if [[ ! -f "$prod_conf" ]]; then
        print_error "Production mosquitto.conf bulunamadı: $prod_conf"
        return 1
    fi
    
    # Backup current config
    if [[ -f "$conf_file" ]]; then
        cp "$conf_file" "$conf_file.pre-migration"
    fi
    
    # Copy production config
    cp "$prod_conf" "$conf_file"
    
    print_success "Mosquitto yapılandırması production config ile güncellendi"
    print_warning "Orijinal dosya: $conf_file.pre-migration"
    echo ""
}

# Update docker-compose production
update_docker_compose() {
    print_info "Docker Compose production yapılandırması güncelleniyor..."
    
    local compose_file="$PROJECT_ROOT/docker-compose.prod.yml"
    
    if [[ ! -f "$compose_file" ]]; then
        print_error "docker-compose.prod.yml bulunamadı: $compose_file"
        return 1
    fi
    
    # Update MQTT port mapping to only expose TLS ports
    print_info "MQTT port mapping güncelleniyor..."
    
    # This is a simplified update - in production, you might want to manually edit
    print_warning "Port mapping'i manuel olarak kontrol edin:"
    echo "  - 1883:1883 (plain MQTT) → Kapatın veya yorum satırı yapın"
    echo "  - 8883:8883 (MQTTS) → Aık tutun"
    echo "  - 9001:9001 (plain WS) → Kapatın veya yorum satırı yapın"
    echo "  - 9883:9883 (WSS) → Aık tutun"
    echo ""
}

# Restart services
restart_services() {
    print_info "Docker servisleri yeniden başlatılıyor..."
    
    cd "$PROJECT_ROOT"
    
    # Stop services
    print_info "Servisler durduruluyor..."
    docker-compose -f docker-compose.prod.yml down
    
    # Start services
    print_info "Servisler başlatılıyor..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services to be healthy
    print_info "Servisler sağlıklı hale gelmesi bekleniyor..."
    sleep 10
    
    # Check service status
    print_info "Servis durumu:"
    docker-compose -f docker-compose.prod.yml ps
    
    print_success "Servisler yeniden başlatıldı"
    echo ""
}

# Test connection
test_connection() {
    print_info "MQTT bağlantısı test ediliyor..."
    
    # Run test script
    if [[ -f "$SCRIPT_DIR/test_mqtt_connection.sh" ]]; then
        chmod +x "$SCRIPT_DIR/test_mqtt_connection.sh"
        "$SCRIPT_DIR/test_mqtt_connection.sh" localhost 8883
    else
        print_warning "Test script'i bulunamadı"
    fi
    echo ""
}

# Display post-migration instructions
display_post_migration() {
    print_header "Geçiş Sonrası Talimatlar"
    
    cat << 'EOF'
Geçiş tamamlandı! Aşağıdaki adımları takip edin:

1. Cihazları Yeniden Yapılandırın:
   - MQTT Broker IP: Yeni sunucu IP adresi
   - MQTT Broker Port: 8883 (TLS)
   - TLS: Etkin
   - CA Certificate: Sunucu CA sertifikası

2. Bağlantıyı Test Edin:
   - Her cihazın bağlandığını doğrulayın
   - MQTT loglarını kontrol edin: docker logs sumatic-mqtt-prod

3. Monitor Edin:
   - Backend logları: docker logs sumatic-backend-prod
   - MQTT logları: docker logs sumatic-mqtt-prod
   - Güvenlik duvarı logları

4. Güvenlik Duvarı:
   - Plain MQTT port (1883) kapalı olduğunu doğrulayın
   - Sadece MQTTS port (8883) açık olmalı

5. Yedekleme:
   - Eski yapılandırmalar yedeklendi
   - Sorun olursa geri dönüş yapabilirsiniz

Geri Dönüş:
   SSH tüneline geri dönmek için:
   1. Backend .env dosyasında: SSH_ENABLED=true
   2. Backend .env dosyasında: MQTT_TLS_ENABLED=false
   3. Servisleri yeniden başlatın

EOF
}

# Rollback function
rollback() {
    print_header "Geri Dönüş (Rollback)"
    
    print_warning "Son yapılandırma değişiklikleri geri alınıyor..."
    
    local env_file="$PROJECT_ROOT/backend/.env"
    local conf_file="$PROJECT_ROOT/mqtt-broker/mosquitto.conf"
    
    # Restore backend .env
    if [[ -f "$env_file.pre-migration" ]]; then
        cp "$env_file.pre-migration" "$env_file"
        print_success "Backend .env geri yüklendi"
    fi
    
    # Restore mosquitto.conf
    if [[ -f "$conf_file.pre-migration" ]]; then
        cp "$conf_file.pre-migration" "$conf_file"
        print_success "Mosquitto.conf geri yüklendi"
    fi
    
    # Restart services
    print_info "Servisler yeniden başlatılıyor..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.prod.yml restart
    
    print_success "Geri dönüş tamamlandı!"
}

# Main execution
main() {
    print_header
    
    check_root
    
    # Ask for confirmation
    print_warning "Bu işlem SSH tünelinden doğrudan MQTT bağlantısına geçiş yapar."
    print_warning "Geçiş öncesi yedekleme yapılacaktır."
    echo ""
    read -p "Devam etmek istiyor musunuz? (yes/no): " CONFIRM
    
    if [[ "$CONFIRM" != "yes" ]]; then
        print_info "Geçiş iptal edildi"
        exit 0
    fi
    
    echo ""
    
    # Run migration steps
    pre_migration_checks
    backup_config
    
    echo ""
    read -p "Backend yapılandırmasını güncellemek istiyor musunuz? (yes/no): " UPDATE_BACKEND
    if [[ "$UPDATE_BACKEND" == "yes" ]]; then
        update_backend_config
    fi
    
    echo ""
    read -p "Mosquitto yapılandırmasını güncellemek istiyor musunuz? (yes/no): " UPDATE_MOSQUITTO
    if [[ "$UPDATE_MOSQUITTO" == "yes" ]]; then
        update_mosquitto_config
    fi
    
    echo ""
    read -p "Servisleri yeniden başlatmak istiyor musunuz? (yes/no): " RESTART
    if [[ "$RESTART" == "yes" ]]; then
        restart_services
        test_connection
    fi
    
    echo ""
    display_post_migration
    
    # Ask if rollback is needed
    echo ""
    read -p "Geri dönüş yapmak istiyor musunuz? (yes/no): " DO_ROLLBACK
    if [[ "$DO_ROLLBACK" == "yes" ]]; then
        echo ""
        rollback
    fi
}

# Run main
main "$@"
