#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - MQTT Connection Test Script
# =============================================================================
# Bu script MQTT broker bağlantısını test eder ve sorunları teşhis eder.
# Kullanım: ./test_mqtt_connection.sh [broker_host] [port]
# =============================================================================

set -e

# Default values
BROKER_HOST=${1:-localhost}
BROKER_PORT=${2:-8883}
TEST_TOPIC="sumatic-test-$$"
TEST_MESSAGE="Test message from $(hostname) at $(date)"

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
    echo "║     Sumatic Modern IoT - MQTT Connection Test                 ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Check dependencies
check_dependencies() {
    print_info "Bağımlılıklar kontrol ediliyor..."
    
    local missing_deps=()
    
    if ! command -v mosquitto_pub &> /dev/null; then
        missing_deps+=("mosquitto-clients")
    fi
    
    if ! command -v openssl &> /dev/null; then
        missing_deps+=("openssl")
    fi
    
    if ! command -v nc &> /dev/null && ! command -v netcat &> /dev/null; then
        missing_deps+=("netcat")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "Eksik bağımlılıklar: ${missing_deps[*]}"
        echo "Kurulum komutları:"
        echo "  Ubuntu/Debian: sudo apt-get install mosquitto-clients openssl netcat"
        echo "  CentOS/RHEL: sudo yum install mosquitto openssl nc"
        exit 1
    fi
    
    print_success "Tüm bağımlılıklar yüklü"
}

# Test TCP connection
test_tcp_connection() {
    print_info "TCP bağlantısı test ediliyor: $BROKER_HOST:$BROKER_PORT"
    
    if nc -z -w5 "$BROKER_HOST" "$BROKER_PORT" 2>/dev/null || \
       netcat -z -w5 "$BROKER_HOST" "$BROKER_PORT" 2>/dev/null; then
        print_success "TCP bağlantısı başarılı"
        return 0
    else
        print_error "TCP bağlantısı başarısız"
        print_warning "Güvenlik duvarı kurallarını ve broker durumunu kontrol edin"
        return 1
    fi
}

# Test TLS connection
test_tls_connection() {
    print_info "TLS bağlantısı test ediliyor..."
    
    if echo | openssl s_client -connect "$BROKER_HOST:$BROKER_PORT" -servername "$BROKER_HOST" \
        2>/dev/null | grep -q "Verify return code"; then
        print_success "TLS bağlantısı başarılı"
        
        # Show certificate details
        print_info "Sertifika bilgileri:"
        echo | openssl s_client -connect "$BROKER_HOST:$BROKER_PORT" -servername "$BROKER_HOST" \
            2>/dev/null | grep -A 2 "subject\|issuer" | head -10
        return 0
    else
        print_error "TLS bağlantısı başarısız"
        print_warning "Sertifika geçerliliğini ve broker TLS yapılandırmasını kontrol edin"
        return 1
    fi
}

# Test MQTT connection without auth
test_mqtt_no_auth() {
    print_info "MQTT bağlantısı test ediliyor (kimlik doğrulama olmadan)..."
    
    # Try to subscribe to a test topic
    timeout 5 mosquitto_sub -h "$BROKER_HOST" -p "$BROKER_PORT" \
        -t "$TEST_TOPIC" -C 1 -W 2 2>/dev/null &
    
    local sub_pid=$!
    sleep 1
    
    # Try to publish
    if mosquitto_pub -h "$BROKER_HOST" -p "$BROKER_PORT" \
        -t "$TEST_TOPIC" -m "$TEST_MESSAGE" 2>/dev/null; then
        
        wait $sub_pid 2>/dev/null
        print_success "MQTT bağlantısı başarılı (kimlik doğrulama kapalı)"
        return 0
    else
        wait $sub_pid 2>/dev/null
        print_warning "MQTT bağlantısı başarısız veya kimlik doğrulama gerekli"
        return 1
    fi
}

# Test MQTT connection with auth
test_mqtt_with_auth() {
    print_info "MQTT bağlantısı test ediliyor (kimlik doğrulama ile)..."
    
    # Check if credentials file exists
    local creds_file="../mqtt-broker/.backend_credentials"
    if [ ! -f "$creds_file" ]; then
        print_warning "Kimlik bilgisi dosyası bulunamadı: $creds_file"
        read -p "Kullanıcı adı: " MQTT_USER
        read -sp "Şifre: " MQTT_PASS
        echo ""
    else
        source "$creds_file"
        MQTT_USER="$MQTT_USERNAME"
        MQTT_PASS="$MQTT_PASSWORD"
    fi
    
    if [ -z "$MQTT_USER" ] || [ -z "$MQTT_PASS" ]; then
        print_error "Kimlik bilgileri eksik"
        return 1
    fi
    
    # Try to subscribe
    timeout 5 mosquitto_sub -h "$BROKER_HOST" -p "$BROKER_PORT" \
        -u "$MQTT_USER" -P "$MQTT_PASS" \
        -t "$TEST_TOPIC" -C 1 -W 2 2>/dev/null &
    
    local sub_pid=$!
    sleep 1
    
    # Try to publish
    if mosquitto_pub -h "$BROKER_HOST" -p "$BROKER_PORT" \
        -u "$MQTT_USER" -P "$MQTT_PASS" \
        -t "$TEST_TOPIC" -m "$TEST_MESSAGE" 2>/dev/null; then
        
        wait $sub_pid 2>/dev/null
        print_success "MQTT bağlantısı başarılı (kimlik doğrulama ile)"
        return 0
    else
        wait $sub_pid 2>/dev/null
        print_error "MQTT bağlantısı başarısız"
        print_warning "Kullanıcı adı, şifre ve ACL yapılandırmasını kontrol edin"
        return 1
    fi
}

# Test MQTT over TLS
test_mqtt_tls() {
    print_info "MQTT over TLS (MQTTS) bağlantısı test ediliyor..."
    
    # Check if credentials file exists
    local creds_file="../mqtt-broker/.backend_credentials"
    if [ ! -f "$creds_file" ]; then
        print_warning "Kimlik bilgisi dosyası bulunamadı: $creds_file"
        read -p "Kullanıcı adı: " MQTT_USER
        read -sp "Şifre: " MQTT_PASS
        echo ""
    else
        source "$creds_file"
        MQTT_USER="$MQTT_USERNAME"
        MQTT_PASS="$MQTT_PASSWORD"
    fi
    
    # Check for CA certificate
    local ca_cert="../mqtt-broker/certs/ca.crt"
    local tls_args=""
    
    if [ -f "$ca_cert" ]; then
        tls_args="--cafile $ca_cert"
        print_info "CA sertifika kullanılıyor: $ca_cert"
    else
        tls_args="--insecure"
        print_warning "CA sertifika bulunamadı, --insecure mod kullanılıyor"
    fi
    
    # Try to subscribe
    timeout 5 mosquitto_sub -h "$BROKER_HOST" -p "$BROKER_PORT" \
        -u "$MQTT_USER" -P "$MQTT_PASS" \
        $tls_args \
        -t "$TEST_TOPIC" -C 1 -W 2 2>/dev/null &
    
    local sub_pid=$!
    sleep 1
    
    # Try to publish
    if mosquitto_pub -h "$BROKER_HOST" -p "$BROKER_PORT" \
        -u "$MQTT_USER" -P "$MQTT_PASS" \
        $tls_args \
        -t "$TEST_TOPIC" -m "$TEST_MESSAGE" 2>/dev/null; then
        
        wait $sub_pid 2>/dev/null
        print_success "MQTTS bağlantısı başarılı"
        return 0
    else
        wait $sub_pid 2>/dev/null
        print_error "MQTTS bağlantısı başarısız"
        print_warning "TLS sertifikasını ve broker yapılandırmasını kontrol edin"
        return 1
    fi
}

# Test broker info
test_broker_info() {
    print_info "Broker bilgileri alınıyor..."
    
    # Try to get broker info from $SYS topics
    timeout 5 mosquitto_sub -h "$BROKER_HOST" -p "$BROKER_PORT" \
        -t "\$SYS/#" -C 5 -W 2 2>/dev/null
    
    if [ $? -eq 0 ]; then
        print_success "Broker bilgileri alındı"
    else
        print_warning "Broker bilgileri alınamadı"
    fi
}

# Display summary
display_summary() {
    local tcp_ok=$1
    local tls_ok=$2
    local mqtt_ok=$3
    
    print_header "Test Özeti"
    
    echo ""
    echo "Broker: $BROKER_HOST:$BROKER_PORT"
    echo ""
    
    echo "Test Sonuçları:"
    [ "$tcp_ok" -eq 0 ] && echo "  [✓] TCP Bağlantısı" || echo "  [✗] TCP Bağlantısı"
    [ "$tls_ok" -eq 0 ] && echo "  [✓] TLS Bağlantısı" || echo "  [✗] TLS Bağlantısı"
    [ "$mqtt_ok" -eq 0 ] && echo "  [✓] MQTT Bağlantısı" || echo "  [✗] MQTT Bağlantısı"
    echo ""
    
    if [ "$tcp_ok" -eq 0 ] && [ "$tls_ok" -eq 0 ] && [ "$mqtt_ok" -eq 0 ]; then
        print_success "Tüm testler başarılı! MQTT broker hazır."
        return 0
    else
        print_error "Bazı testler başarısız. Sorunları giderin."
        return 1
    fi
}

# Main execution
main() {
    print_header
    
    print_info "Test parametreleri:"
    echo "  Broker: $BROKER_HOST"
    echo "  Port:   $BROKER_PORT"
    echo ""
    
    check_dependencies
    
    local tcp_result=1
    local tls_result=1
    local mqtt_result=1
    
    # Run tests
    test_tcp_connection && tcp_result=0 || true
    echo ""
    
    if [ "$BROKER_PORT" = "8883" ] || [ "$BROKER_PORT" = "9883" ]; then
        test_tls_connection && tls_result=0 || true
        echo ""
    fi
    
    # Try MQTT connection
    if [ "$BROKER_PORT" = "8883" ] || [ "$BROKER_PORT" = "9883" ]; then
        test_mqtt_tls && mqtt_result=0 || true
    else
        test_mqtt_with_auth && mqtt_result=0 || \
        test_mqtt_no_auth && mqtt_result=0 || true
    fi
    echo ""
    
    # Get broker info
    test_broker_info
    echo ""
    
    # Display summary
    display_summary $tcp_result $tls_result $mqtt_result
}

# Run main
main "$@"
