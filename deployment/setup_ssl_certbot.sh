#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - SSL Certificate Setup with Let's Encrypt & Certbot
# =============================================================================
# This script sets up automatic SSL certificates using Let's Encrypt and Certbot
# Usage: ./setup_ssl_certbot.sh [domain-name] [email]
# Example: ./setup_ssl_certbot.sh yourdomain.com admin@yourdomain.com
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SSL_DIR="/etc/nginx/ssl"
CERTBOT_DIR="/etc/letsencrypt"
NGINX_CONF="$SCRIPT_DIR/nginx.conf"
DOCKER_COMPOSE="$PROJECT_ROOT/docker-compose.prod.yml"

# Get parameters
DOMAIN="${1:-}"
EMAIL="${2:-}"

# ─────────────────────────────────────────────────────────────────────────────
# Function: Print colored messages
# ─────────────────────────────────────────────────────────────────────────────
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Display usage
# ─────────────────────────────────────────────────────────────────────────────
usage() {
    cat << EOF
${BLUE}Sumatic Modern IoT - SSL Certificate Setup${NC}

${YELLOW}Usage:${NC}
    $0 [DOMAIN] [EMAIL]

${YELLOW}Parameters:${NC}
    DOMAIN          - Your domain name (e.g., yourdomain.com or subdomain.yourdomain.com)
    EMAIL           - Email for Let's Encrypt notifications and recovery

${YELLOW}Examples:${NC}
    $0 yourdomain.com admin@yourdomain.com
    $0 api.yourdomain.com security@yourdomain.com

${YELLOW}Notes:${NC}
    - This script should run on your production server
    - Your domain must be publicly accessible before running this script
    - Port 80 must be open for ACME challenge verification
    - Requires Docker and docker-compose to be installed
    - Requires sudo privileges for SSL directory creation
EOF
    exit 1
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Validate domain
# ─────────────────────────────────────────────────────────────────────────────
validate_domain() {
    local domain="$1"
    
    # Simple domain validation regex
    if [[ ! $domain =~ ^([a-z0-9](-?[a-z0-9])*\.)+[a-z]{2,}$ ]]; then
        print_error "Invalid domain format: $domain"
        print_info "Domain must be valid (e.g., yourdomain.com)"
        return 1
    fi
    
    print_success "Domain validation passed: $domain"
    return 0
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Validate email
# ─────────────────────────────────────────────────────────────────────────────
validate_email() {
    local email="$1"
    
    # Simple email validation regex
    if [[ ! $email =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        print_error "Invalid email format: $email"
        return 1
    fi
    
    print_success "Email validation passed: $email"
    return 0
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Check prerequisites
# ─────────────────────────────────────────────────────────────────────────────
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if running as root or with sudo capability
    if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
        print_error "This script needs sudo privileges"
        print_info "Please run with sudo or ensure passwordless sudo is configured"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check docker-compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose is not installed"
        exit 1
    fi
    print_success "docker-compose is installed"
    
    # Check if nginx.conf exists
    if [ ! -f "$NGINX_CONF" ]; then
        print_error "nginx.conf not found at: $NGINX_CONF"
        exit 1
    fi
    print_success "nginx.conf found"
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Create SSL directories
# ─────────────────────────────────────────────────────────────────────────────
create_ssl_directories() {
    print_info "Creating SSL directories..."
    
    if [[ $EUID -eq 0 ]]; then
        mkdir -p "$SSL_DIR"
        mkdir -p /var/www/certbot
    else
        sudo mkdir -p "$SSL_DIR"
        sudo mkdir -p /var/www/certbot
    fi
    
    print_success "SSL directories created"
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Generate initial SSL certificate with Certbot
# ─────────────────────────────────────────────────────────────────────────────
generate_certificate() {
    local domain="$1"
    local email="$2"
    
    print_info "Generating SSL certificate for domain: $domain"
    print_info "Email: $email"
    
    # Run Certbot in Docker
    docker run -it --rm \
        -v "$SSL_DIR:/etc/letsencrypt" \
        -v "/var/www/certbot:/var/www/certbot" \
        certbot/certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        --email "$email" \
        --agree-tos \
        --no-eff-email \
        -d "$domain"
    
    if [ $? -eq 0 ]; then
        print_success "SSL certificate generated successfully"
        return 0
    else
        print_error "Failed to generate SSL certificate"
        print_warning "Make sure:"
        print_warning "  1. Your domain is publicly accessible"
        print_warning "  2. Port 80 is open and accessible"
        print_warning "  3. Your domain DNS is pointing to this server"
        return 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Setup automatic certificate renewal with cron
# ─────────────────────────────────────────────────────────────────────────────
setup_renewal_cron() {
    print_info "Setting up automatic certificate renewal..."
    
    # Create renewal script
    RENEWAL_SCRIPT="/usr/local/bin/sumatic_ssl_renewal.sh"
    
    if [[ $EUID -eq 0 ]]; then
        cat > "$RENEWAL_SCRIPT" << 'RENEWAL_EOF'
#!/bin/bash
# SSL Certificate Renewal Script
# Runs daily via cron to renew certificates before expiration

DOCKER_COMPOSE_PATH="/path/to/docker-compose.prod.yml"
SSL_DIR="/etc/nginx/ssl"
LOG_FILE="/var/log/sumatic_ssl_renewal.log"

echo "[$(date)] Starting SSL renewal check..." >> "$LOG_FILE"

# Renew certificates
docker run --rm \
    -v "$SSL_DIR:/etc/letsencrypt" \
    -v "/var/www/certbot:/var/www/certbot" \
    certbot/certbot renew \
    --webroot \
    --webroot-path /var/www/certbot \
    --quiet >> "$LOG_FILE" 2>&1

# Reload Nginx if renewal succeeded
if [ $? -eq 0 ]; then
    echo "[$(date)] Certificate renewal successful. Reloading Nginx..." >> "$LOG_FILE"
    cd "$(dirname "$DOCKER_COMPOSE_PATH")"
    docker-compose -f "$(basename "$DOCKER_COMPOSE_PATH")" exec -T nginx nginx -s reload
else
    echo "[$(date)] Certificate renewal check completed (no renewal needed)" >> "$LOG_FILE"
fi

echo "[$(date)] SSL renewal check finished" >> "$LOG_FILE"
RENEWAL_EOF
        
        # Make script executable
        chmod +x "$RENEWAL_SCRIPT"
        
        # Update placeholder in renewal script
        sed -i "s|/path/to/docker-compose.prod.yml|$DOCKER_COMPOSE|g" "$RENEWAL_SCRIPT"
        
        # Add to crontab if not already present
        if ! crontab -l 2>/dev/null | grep -q "sumatic_ssl_renewal.sh"; then
            (crontab -l 2>/dev/null; echo "0 3 * * * $RENEWAL_SCRIPT") | crontab -
            print_success "Cron job added for daily certificate renewal"
        else
            print_warning "Cron job for SSL renewal already exists"
        fi
    else
        print_warning "Root privileges required for cron setup. Running as non-root."
        print_info "To enable automatic renewal, add this to root's crontab:"
        print_info "  0 3 * * * docker run --rm -v /etc/nginx/ssl:/etc/letsencrypt -v /var/www/certbot:/var/www/certbot certbot/certbot renew --webroot --webroot-path /var/www/certbot --quiet && docker-compose -f $DOCKER_COMPOSE exec -T nginx nginx -s reload"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Generate strong DH parameters
# ─────────────────────────────────────────────────────────────────────────────
generate_dhparam() {
    print_info "Generating DH parameters (this may take a few minutes)..."
    
    local dhparam_file="$SSL_DIR/dhparam.pem"
    
    if [ -f "$dhparam_file" ]; then
        print_warning "DH parameters already exist"
        return 0
    fi
    
    if [[ $EUID -eq 0 ]]; then
        openssl dhparam -out "$dhparam_file" 2048
    else
        sudo openssl dhparam -out "$dhparam_file" 2048
    fi
    
    if [ $? -eq 0 ]; then
        print_success "DH parameters generated"
        return 0
    else
        print_error "Failed to generate DH parameters"
        return 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Update Nginx configuration
# ─────────────────────────────────────────────────────────────────────────────
update_nginx_config() {
    local domain="$1"
    
    print_info "Creating production Nginx configuration with SSL..."
    
    # Create new nginx.conf with SSL enabled
    cat > "$NGINX_CONF" << 'NGINX_EOF'
# =============================================================================
# Sumatic Modern IoT - Nginx Reverse Proxy Configuration (HTTPS/SSL)
# =============================================================================

# Worker settings
worker_processes auto;
worker_rlimit_nofile 65535;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    multi_accept on;
    use epoll;
}

http {
    # ─── Basic Settings ──────────────────────────────────────────────────────
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    charset utf-8;

    # ─── Logging ─────────────────────────────────────────────────────────────
    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time $upstream_response_time';

    access_log /var/log/nginx/access.log main;

    # ─── Performance ─────────────────────────────────────────────────────────
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 100;
    types_hash_max_size 2048;
    client_max_body_size 10m;
    server_tokens off;

    # ─── Gzip Compression ───────────────────────────────────────────────────
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_buffers 16 8k;
    gzip_http_version 1.1;
    gzip_min_length 256;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml
        application/rss+xml
        application/atom+xml
        image/svg+xml;

    # ─── Rate Limiting ───────────────────────────────────────────────────────
    # General rate limit: 30 requests per second per IP
    limit_req_zone $binary_remote_addr zone=general:10m rate=30r/s;
    # API rate limit: 100 requests per minute per IP
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
    # Login rate limit: 5 requests per minute per IP
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    # ─── Upstream Definitions ────────────────────────────────────────────────
    upstream backend {
        server backend:8000;
        keepalive 32;
    }

    upstream frontend {
        server frontend:3000;
        keepalive 32;
    }

    # ─── Map for WebSocket Upgrade ───────────────────────────────────────────
    map $http_upgrade $connection_upgrade {
        default upgrade;
        ''      close;
    }

    # ─── HTTP Server (Redirect to HTTPS) ─────────────────────────────────────
    server {
        listen 80;
        server_name _;

        # Health check endpoint (keep accessible on HTTP)
        location /health {
            access_log off;
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }

        # ACME challenge for SSL certificate renewal
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # Redirect all HTTP to HTTPS
        location / {
            return 301 https://$host$request_uri;
        }
    }

    # ─── HTTPS Server (SSL Enabled) ──────────────────────────────────────────
    server {
        listen 443 ssl http2;
        server_name DOMAIN_PLACEHOLDER;

        # SSL Certificates (Let's Encrypt)
        ssl_certificate /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/privkey.pem;

        # SSL Configuration (Modern & Secure)
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        ssl_session_tickets off;

        # DH Parameters (for Perfect Forward Secrecy)
        ssl_dhparam /etc/nginx/ssl/dhparam.pem;

        # OCSP Stapling
        ssl_stapling on;
        ssl_stapling_verify on;
        ssl_trusted_certificate /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/chain.pem;

        # HSTS (HTTP Strict Transport Security)
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: ws: https:;" always;

        # Backend API
        location /api/ {
            limit_req zone=api burst=20 nodelay;

            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # Login endpoint with stricter rate limiting
        location /api/v1/auth/login {
            limit_req zone=login burst=3 nodelay;

            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
        }

        # Backend health check
        location /api/health {
            proxy_pass http://backend/health;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            access_log off;
        }

        # WebSocket connections
        location /api/v1/ws {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_read_timeout 3600s;
            proxy_send_timeout 3600s;
        }

        # Frontend (Next.js)
        location / {
            limit_req zone=general burst=50 nodelay;

            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection $connection_upgrade;
        }

        # Next.js static files (with caching)
        location /_next/static {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_cache_valid 200 60m;
            add_header Cache-Control "public, max-age=31536000, immutable";
        }

        # Favicon and static assets (with caching)
        location ~* \.(ico|png|jpg|jpeg|gif|svg|woff|woff2|ttf|eot)$ {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            expires 30d;
            add_header Cache-Control "public, no-transform";
        }
    }
}
NGINX_EOF

    # Replace domain placeholder
    sed -i "s/DOMAIN_PLACEHOLDER/$domain/g" "$NGINX_CONF"
    
    print_success "Nginx configuration updated with SSL"
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Restart Docker containers
# ─────────────────────────────────────────────────────────────────────────────
restart_containers() {
    print_info "Restarting Docker containers..."
    
    cd "$PROJECT_ROOT"
    
    if [ -f "$DOCKER_COMPOSE" ]; then
        docker-compose -f "$DOCKER_COMPOSE" restart nginx
    else
        print_warning "docker-compose.prod.yml not found. Manual restart needed."
        print_info "Run: docker-compose -f docker-compose.prod.yml restart nginx"
        return 1
    fi
    
    print_success "Docker containers restarted"
    return 0
}

# ─────────────────────────────────────────────────────────────────────────────
# Function: Display SSL verification info
# ─────────────────────────────────────────────────────────────────────────────
verify_ssl_setup() {
    local domain="$1"
    
    print_info "SSL Setup Complete! 🔒"
    echo ""
    print_success "Certificate Information:"
    echo "  Domain: $domain"
    echo "  Certificate: /etc/letsencrypt/live/$domain/fullchain.pem"
    echo "  Private Key: /etc/letsencrypt/live/$domain/privkey.pem"
    echo ""
    print_success "Verification Commands:"
    echo "  # Check certificate details"
    echo "  openssl x509 -in /etc/letsencrypt/live/$domain/fullchain.pem -text -noout"
    echo ""
    echo "  # Check certificate expiration"
    echo "  openssl x509 -in /etc/letsencrypt/live/$domain/fullchain.pem -noout -dates"
    echo ""
    echo "  # Test SSL configuration"
    echo "  curl -I https://$domain"
    echo "  openssl s_client -connect $domain:443"
    echo ""
    echo "  # Check SSL Labs score"
    echo "  https://www.ssllabs.com/ssltest/analyze.html?d=$domain"
    echo ""
    print_info "Certificate Renewal:"
    echo "  - Automatic renewal is scheduled daily at 3 AM"
    echo "  - Certificates renew 30 days before expiration"
    echo "  - Next renewal check: Tomorrow at 3 AM"
    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Main Execution
# ─────────────────────────────────────────────────────────────────────────────
main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║     Sumatic Modern IoT - SSL Certificate Setup                ║"
    echo "║     Using Let's Encrypt & Certbot                             ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Validate inputs
    if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
        print_error "Domain and email are required"
        echo ""
        usage
    fi
    
    # Validate domain and email
    if ! validate_domain "$DOMAIN"; then
        exit 1
    fi
    
    if ! validate_email "$EMAIL"; then
        exit 1
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Create SSL directories
    create_ssl_directories
    
    # Generate DH parameters
    generate_dhparam
    
    # Generate SSL certificate
    if ! generate_certificate "$DOMAIN" "$EMAIL"; then
        print_error "Failed to generate SSL certificate"
        print_info "Please check the errors above and try again"
        exit 1
    fi
    
    # Update Nginx configuration
    update_nginx_config "$DOMAIN"
    
    # Setup automatic renewal
    setup_renewal_cron
    
    # Restart containers
    if restart_containers; then
        verify_ssl_setup "$DOMAIN"
    else
        print_warning "Please manually restart the containers and verify SSL setup"
    fi
    
    print_success "SSL setup completed successfully! ✓"
    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Run main function
# ─────────────────────────────────────────────────────────────────────────────
main "$@"
