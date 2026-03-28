#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - Fail2Ban Installation and Configuration
# =============================================================================
# This script installs and configures Fail2Ban for intrusion prevention
# Usage: sudo ./setup_fail2ban.sh
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Functions
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Sumatic Modern IoT - Fail2Ban Setup                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    print_error "Cannot detect OS"
    exit 1
fi

print_info "Detected OS: $OS $VERSION"

# Install Fail2Ban
install_fail2ban() {
    print_info "Installing Fail2Ban..."
    
    case $OS in
        ubuntu|debian)
            apt-get update
            apt-get install -y fail2ban
            ;;
        centos|rhel|fedora)
            if command -v dnf &> /dev/null; then
                dnf install -y epel-release
                dnf install -y fail2ban
            else
                yum install -y epel-release
                yum install -y fail2ban
            fi
            ;;
        *)
            print_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    
    print_success "Fail2Ban installed"
}

# Create Nginx filter for authentication failures
create_nginx_auth_filter() {
    print_info "Creating Nginx authentication filter..."
    
    cat > /etc/fail2ban/filter.d/nginx-auth.conf << 'EOF'
# Fail2Ban filter for Nginx authentication failures

[Definition]
failregex = ^ \[error\] \d+#\d+: \*\d+ user "(?:[^"]+|.*?)"\s?(?:was not found|no user|password mismatch)\s?in\s?"/.*?"\s?, client: <HOST>
            ^ \[error\] \d+#\d+: \*\d+ user "(?:[^"]+|.*?)"\s?(?:was not found|no user|password mismatch)\s?, client: <HOST>
            ^ \[error\] \d+#\d+: \*\d+ no user/password was provided for basic authentication\s?, client: <HOST>
ignoreregex =
EOF

    print_success "Nginx auth filter created"
}

# Create Nginx filter for bad requests
create_nginx_bad_requests_filter() {
    print_info "Creating Nginx bad requests filter..."
    
    cat > /etc/fail2ban/filter.d/nginx-bad-requests.conf << 'EOF'
# Fail2Ban filter for Nginx bad requests

[Definition]
failregex = ^<HOST> -.*"(GET|POST|HEAD).*HTTP.*"(400|401|403|444).*
            ^<HOST> -.*"-".*(400|401|403|444).*
ignoreregex =
EOF

    print_success "Nginx bad requests filter created"
}

# Create Nginx filter for rate limiting
create_nginx_rate_limit_filter() {
    print_info "Creating Nginx rate limit filter..."
    
    cat > /etc/fail2ban/filter.d/nginx-ratelimit.conf << 'EOF'
# Fail2Ban filter for Nginx rate limiting

[Definition]
failregex = limiting requests, excess:.* by zone.*client: <HOST>
ignoreregex =
EOF

    print_success "Nginx rate limit filter created"
}

# Create jail configuration
create_jail_configuration() {
    print_info "Creating jail configuration..."
    
    cat > /etc/fail2ban/jail.d/sumatic-local.conf << 'EOF'
# =============================================================================
# Sumatic Modern IoT - Fail2Ban Jail Configuration
# =============================================================================

[DEFAULT]
# Ban IP for 1 hour (3600 seconds)
bantime = 3600

# Find failures within 10 minutes
findtime = 600

# Ban after 5 failures
maxretry = 5

# Send email notifications (optional)
# destemail = admin@yourdomain.com
# sendername = Fail2Ban-Sumatic
# action = %(action_)s
#           %(action_mwl)s

# Ignore local network
ignoreip = 127.0.0.1/8 ::1 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16

# -----------------------------------------------------------------------------
# Nginx Authentication Failures
# -----------------------------------------------------------------------------
[nginx-auth]
enabled = true
filter = nginx-auth
logpath = /var/log/nginx/error.log
maxretry = 3
findtime = 300
bantime = 7200
action = iptables-multiport[name=nginx-auth, port="http,https", protocol=tcp]

# -----------------------------------------------------------------------------
# Nginx Bad Requests (400, 403, 404, etc.)
# -----------------------------------------------------------------------------
[nginx-bad-requests]
enabled = true
filter = nginx-bad-requests
logpath = /var/log/nginx/access.log
maxretry = 10
findtime = 60
bantime = 1800
action = iptables-multiport[name=nginx-bad, port="http,https", protocol=tcp]

# -----------------------------------------------------------------------------
# Nginx Rate Limiting
# -----------------------------------------------------------------------------
[nginx-ratelimit]
enabled = true
filter = nginx-ratelimit
logpath = /var/log/nginx/error.log
maxretry = 5
findtime = 60
bantime = 3600
action = iptables-multiport[name=nginx-ratelimit, port="http,https", protocol=tcp]

# -----------------------------------------------------------------------------
# SSH (if SSH access is enabled)
# -----------------------------------------------------------------------------
[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
findtime = 600
bantime = 86400

# -----------------------------------------------------------------------------
# Docker containers (if logs are accessible)
# -----------------------------------------------------------------------------
[sumatic-backend-auth]
enabled = true
filter = sumatic-backend-auth
logpath = /var/lib/docker/containers/*sumatic-backend*/*-json.log
maxretry = 5
findtime = 300
bantime = 3600
action = iptables-multiport[name=backend-auth, port="http,https", protocol=tcp]
EOF

    print_success "Jail configuration created"
}

# Create custom filter for backend authentication
create_backend_auth_filter() {
    print_info "Creating backend authentication filter..."
    
    cat > /etc/fail2ban/filter.d/sumatic-backend-auth.conf << 'EOF'
# Fail2Ban filter for Sumatic Backend authentication failures

[Definition]
failregex = ^.*"POST /api/v1/auth/login HTTP.*" 401.*"client_ip": "<HOST>"
            ^.*"POST /api/v1/auth/login HTTP.*" 403.*"client_ip": "<HOST>"
            ^.*Authentication failed.*client_ip=<HOST>
            ^.*Invalid credentials.*client_ip=<HOST>
ignoreregex =
EOF

    print_success "Backend auth filter created"
}

# Configure Fail2Ban to work with Docker logs
configure_docker_logs() {
    print_info "Configuring Docker log access..."
    
    # Add fail2ban user to docker group to read container logs
    usermod -aG docker fail2ban 2>/dev/null || true
    
    # Create systemd override for fail2ban to start after docker
    mkdir -p /etc/systemd/system/fail2ban.service.d
    cat > /etc/systemd/system/fail2ban.service.d/override.conf << 'EOF'
[Unit]
After=docker.service
Requires=docker.service
EOF
    
    systemctl daemon-reload
    
    print_success "Docker log access configured"
}

# Start and enable Fail2Ban
start_fail2ban() {
    print_info "Starting Fail2Ban service..."
    
    systemctl enable fail2ban
    systemctl restart fail2ban
    
    # Wait for service to start
    sleep 3
    
    if systemctl is-active --quiet fail2ban; then
        print_success "Fail2Ban service started"
    else
        print_error "Failed to start Fail2Ban service"
        systemctl status fail2ban
        exit 1
    fi
}

# Display status
display_status() {
    print_info "Fail2Ban Status:"
    echo ""
    
    # Show active jails
    echo "Active Jails:"
    fail2ban-client status
    echo ""
    
    # Show detailed status for each jail
    echo "Detailed Jail Status:"
    for jail in $(fail2ban-client status | grep "Jail list" | sed 's/.*Jail list:\s*//' | sed 's/,//g'); do
        echo ""
        echo "Jail: $jail"
        fail2ban-client status "$jail" 2>/dev/null || echo "  No status available"
    done
}

# Display management commands
display_commands() {
    echo ""
    print_info "Useful Fail2Ban Commands:"
    echo ""
    echo "  # Check Fail2Ban status"
    echo "  sudo fail2ban-client status"
    echo ""
    echo "  # Check specific jail status"
    echo "  sudo fail2ban-client status nginx-auth"
    echo ""
    echo "  # Ban an IP manually"
    echo "  sudo fail2ban-client set nginx-auth banip 1.2.3.4"
    echo ""
    echo "  # Unban an IP"
    echo "  sudo fail2ban-client set nginx-auth unbanip 1.2.3.4"
    echo ""
    echo "  # View banned IPs"
    echo "  sudo iptables -L -n | grep f2b"
    echo ""
    echo "  # View Fail2Ban logs"
    echo "  sudo tail -f /var/log/fail2ban.log"
    echo ""
    echo "  # Restart Fail2Ban"
    echo "  sudo systemctl restart fail2ban"
    echo ""
    echo "  # Reload configuration"
    echo "  sudo fail2ban-client reload"
    echo ""
}

# Main execution
main() {
    # Install Fail2Ban
    install_fail2ban
    
    # Create filters
    create_nginx_auth_filter
    create_nginx_bad_requests_filter
    create_nginx_rate_limit_filter
    create_backend_auth_filter
    
    # Create jail configuration
    create_jail_configuration
    
    # Configure Docker log access
    configure_docker_logs
    
    # Start service
    start_fail2ban
    
    # Display status
    display_status
    
    # Display commands
    display_commands
    
    echo ""
    print_success "Fail2Ban installation and configuration completed!"
    echo ""
    print_warning "Important Notes:"
    echo "  1. Fail2Ban is now protecting your server from brute-force attacks"
    echo "  2. IPs are banned for 1 hour by default (configurable in jail.local)"
    echo "  3. Check /var/log/fail2ban.log for activity"
    echo "  4. Adjust ban times and retry counts in /etc/fail2ban/jail.d/sumatic-local.conf"
    echo "  5. Whitelist trusted IPs in ignoreip directive"
    echo ""
}

# Run main
main "$@"
