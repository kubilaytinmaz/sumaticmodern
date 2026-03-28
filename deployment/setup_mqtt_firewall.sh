#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - MQTT Broker Firewall Setup Script
# =============================================================================
# This script sets up firewall rules to restrict MQTT broker access to
# trusted IP addresses only.
#
# Usage:
#   sudo ./setup_mqtt_firewall.sh
#
# For production deployment, modify the TRUSTED_NETWORKS array below.
# =============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# MQTT Broker Ports
MQTT_PORT=1883
MQTTS_PORT=8883
WS_PORT=9001
WSS_PORT=9883

# Trusted networks (CIDR notation)
# Modify these values for your production environment
TRUSTED_NETWORKS=(
    "192.168.1.0/24"      # Local network
    "10.0.0.0/8"          # Private network
    "172.16.0.0/12"       # Private network
    # Add your specific IP addresses or networks here
    # "203.0.113.0/24"    # Example: Specific public IP range
)

# Docker network (allow connections from Docker containers)
DOCKER_NETWORK="172.17.0.0/16"

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}============================================${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

detect_firewall() {
    if command -v ufw &> /dev/null; then
        echo "ufw"
    elif command -v firewall-cmd &> /dev/null; then
        echo "firewalld"
    elif command -v iptables &> /dev/null; then
        echo "iptables"
    else
        echo "none"
    fi
}

setup_ufw() {
    print_header "Setting up UFW (Uncomplicated Firewall)"
    
    # Reset UFW to default (optional - comment out if you want to keep existing rules)
    # ufw --force reset
    
    # Set default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (important: don't lock yourself out!)
    ufw allow 22/tcp comment 'Allow SSH'
    
    # Allow Docker network
    ufw allow from $DOCKER_NETWORK comment 'Allow Docker network'
    
    # Allow trusted networks for MQTT ports
    for network in "${TRUSTED_NETWORKS[@]}"; do
        ufw allow from $network to any port $MQTT_PORT comment "Allow MQTT from $network"
        ufw allow from $network to any port $MQTTS_PORT comment "Allow MQTTS from $network"
        ufw allow from $network to any port $WS_PORT comment "Allow MQTT WebSocket from $network"
        ufw allow from $network to any port $WSS_PORT comment "Allow MQTT WebSocket Secure from $network"
        print_success "Allowed $network for MQTT ports"
    done
    
    # Allow HTTP/HTTPS (if needed)
    ufw allow 80/tcp comment 'Allow HTTP'
    ufw allow 443/tcp comment 'Allow HTTPS'
    
    # Enable UFW
    ufw --force enable
    
    print_success "UFW configuration completed"
    ufw status verbose
}

setup_firewalld() {
    print_header "Setting up firewalld"
    
    # Create a new zone for MQTT (optional)
    # firewall-cmd --permanent --new-zone=mqtt
    
    # Allow Docker network
    firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="'$DOCKER_NETWORK'" accept'
    
    # Allow trusted networks for MQTT ports
    for network in "${TRUSTED_NETWORKS[@]}"; do
        firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="'$network'" port protocol="tcp" port="'$MQTT_PORT'" accept'
        firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="'$network'" port protocol="tcp" port="'$MQTTS_PORT'" accept'
        firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="'$network'" port protocol="tcp" port="'$WS_PORT'" accept'
        firewall-cmd --permanent --add-rich-rule='rule family="ipv4" source address="'$network'" port protocol="tcp" port="'$WSS_PORT'" accept'
        print_success "Allowed $network for MQTT ports"
    done
    
    # Reload firewalld
    firewall-cmd --reload
    
    print_success "firewalld configuration completed"
    firewall-cmd --list-all
}

setup_iptables() {
    print_header "Setting up iptables"
    
    # Flush existing rules (optional - comment out if you want to keep existing rules)
    # iptables -F
    # iptables -X
    # iptables -t nat -F
    # iptables -t nat -X
    
    # Default policies
    iptables -P INPUT DROP
    iptables -P FORWARD DROP
    iptables -P OUTPUT ACCEPT
    
    # Allow established connections
    iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
    
    # Allow loopback
    iptables -A INPUT -i lo -j ACCEPT
    
    # Allow SSH (important: don't lock yourself out!)
    iptables -A INPUT -p tcp --dport 22 -j ACCEPT
    
    # Allow Docker network
    iptables -A INPUT -s $DOCKER_NETWORK -j ACCEPT
    
    # Allow trusted networks for MQTT ports
    for network in "${TRUSTED_NETWORKS[@]}"; do
        iptables -A INPUT -s $network -p tcp --dport $MQTT_PORT -j ACCEPT
        iptables -A INPUT -s $network -p tcp --dport $MQTTS_PORT -j ACCEPT
        iptables -A INPUT -s $network -p tcp --dport $WS_PORT -j ACCEPT
        iptables -A INPUT -s $network -p tcp --dport $WSS_PORT -j ACCEPT
        print_success "Allowed $network for MQTT ports"
    done
    
    # Allow HTTP/HTTPS (if needed)
    iptables -A INPUT -p tcp --dport 80 -j ACCEPT
    iptables -A INPUT -p tcp --dport 443 -j ACCEPT
    
    # Save iptables rules
    if command -v iptables-save &> /dev/null; then
        iptables-save > /etc/iptables/rules.v4
        print_success "iptables rules saved"
    fi
    
    print_success "iptables configuration completed"
    iptables -L -n -v
}

show_docker_compose_example() {
    print_header "Docker Compose Network Isolation Example"
    
    cat << 'EOF'
# For additional security, use Docker networks to isolate the MQTT broker:

version: '3.8'

services:
  mqtt-broker:
    image: eclipse-mosquitto:2.0
    networks:
      - mqtt-internal  # Only backend can access
    ports:
      - "1883:1883"    # Comment this out in production
      # - "8883:8883"  # Only expose MQTTS in production
    # ... other configuration

  backend:
    image: sumatic-backend:latest
    networks:
      - mqtt-internal
      - frontend
    depends_on:
      - mqtt-broker
    # ... other configuration

  frontend:
    image: sumatic-frontend:latest
    networks:
      - frontend
    ports:
      - "80:80"
      - "443:443"
    # ... other configuration

networks:
  mqtt-internal:
    driver: bridge
    internal: true  # No external access
  frontend:
    driver: bridge

EOF
}

# =============================================================================
# Main Script
# =============================================================================

main() {
    print_header "MQTT Broker Firewall Setup"
    
    check_root
    
    # Detect firewall system
    FIREWALL=$(detect_firewall)
    
    if [[ $FIREWALL == "none" ]]; then
        print_error "No firewall system detected (ufw, firewalld, or iptables required)"
        exit 1
    fi
    
    print_success "Detected firewall: $FIREWALL"
    
    # Show current configuration
    echo ""
    echo "Trusted networks:"
    for network in "${TRUSTED_NETWORKS[@]}"; do
        echo "  - $network"
    done
    echo ""
    echo "MQTT Ports to be protected:"
    echo "  - MQTT: $MQTT_PORT"
    echo "  - MQTTS: $MQTTS_PORT"
    echo "  - WebSocket: $WS_PORT"
    echo "  - WebSocket Secure: $WSS_PORT"
    echo ""
    
    # Confirm before proceeding
    read -p "Continue with firewall setup? (yes/no): " CONFIRM
    if [[ $CONFIRM != "yes" ]]; then
        print_warning "Setup cancelled by user"
        exit 0
    fi
    
    # Setup firewall based on detected system
    case $FIREWALL in
        "ufw")
            setup_ufw
            ;;
        "firewalld")
            setup_firewalld
            ;;
        "iptables")
            setup_iptables
            ;;
    esac
    
    # Show Docker Compose example
    echo ""
    show_docker_compose_example
    
    print_success "Firewall setup completed!"
    echo ""
    echo "Next steps:"
    echo "1. Test MQTT connectivity from trusted networks"
    echo "2. Verify that untrusted networks cannot connect"
    echo "3. Consider using Docker network isolation for additional security"
    echo "4. Review and update TRUSTED_NETWORKS as needed"
}

# Run main function
main "$@"
