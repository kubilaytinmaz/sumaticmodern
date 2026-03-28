#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - SSH Tunnel User Creation Script
# =============================================================================
# This script creates a limited SSH user for tunneling MQTT connections
# Run this on the REMOTE server (where MQTT broker is located)
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SSH_USER="sumatic-tunnel"
SSH_GROUP="sumatic-tunnel"
AUTHORIZED_KEYS_DIR="/home/${SSH_USER}/.ssh"
AUTHORIZED_KEYS_FILE="${AUTHORIZED_KEYS_DIR}/authorized_keys"

echo "============================================================================"
echo "Sumatic Modern IoT - SSH Tunnel User Setup"
echo "============================================================================"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root${NC}"
   exit 1
fi

# Check if user already exists
if id "$SSH_USER" &>/dev/null; then
    echo -e "${YELLOW}Warning: User $SSH_USER already exists${NC}"
    read -p "Do you want to recreate the user? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing user..."
        userdel -r "$SSH_USER" 2>/dev/null || true
        groupdel "$SSH_GROUP" 2>/dev/null || true
    else
        echo "Exiting..."
        exit 0
    fi
fi

# Create group
echo "Creating group: $SSH_GROUP"
groupadd "$SSH_GROUP"

# Create user with no shell access (for security)
echo "Creating user: $SSH_USER"
useradd -m -g "$SSH_GROUP" -s /usr/sbin/nologin "$SSH_USER"

# Set random password (user won't login with password anyway)
RANDOM_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
echo "$SSH_USER:$RANDOM_PASSWORD" | chpasswd

echo -e "${GREEN}✓ User created with random password (not used for SSH login)${NC}"

# Create .ssh directory
echo "Creating .ssh directory..."
mkdir -p "$AUTHORIZED_KEYS_DIR"
chmod 700 "$AUTHORIZED_KEYS_DIR"
chown "$SSH_USER:$SSH_GROUP" "$AUTHORIZED_KEYS_DIR"

# Create authorized_keys file
touch "$AUTHORIZED_KEYS_FILE"
chmod 600 "$AUTHORIZED_KEYS_FILE"
chown "$SSH_USER:$SSH_GROUP" "$AUTHORIZED_KEYS_FILE"

echo -e "${GREEN}✓ SSH directory configured${NC}"
echo ""
echo "============================================================================"
echo "IMPORTANT: Add your public SSH key to authorized_keys"
echo "============================================================================"
echo ""
echo "Run the following command on your LOCAL machine:"
echo ""
echo -e "${YELLOW}cat ~/.ssh/sumatic_tunnel_key.pub | ssh root@$(hostname) 'cat >> /home/${SSH_USER}/.ssh/authorized_keys'${NC}"
echo ""
echo "Or manually copy your public key to: $AUTHORIZED_KEYS_FILE"
echo ""
echo "============================================================================"
echo "Security Configuration"
echo "============================================================================"
echo ""

# Configure SSH to restrict this user
SSH_CONFIG="/etc/ssh/sshd_config.d/sumatic-tunnel.conf"

cat > "$SSH_CONFIG" << EOF
# SSH Tunnel Configuration for Sumatic IoT
# Restrict sumatic-tunnel user to port forwarding only

Match User $SSH_USER
    # Force command to prevent interactive shell
    ForceCommand /bin/echo 'This account is for SSH tunneling only'

    # Allow only port forwarding
    PermitOpen localhost:1883

    # Disable PTY allocation
    PermitTTY no

    # Disable X11 forwarding
    X11Forwarding no

    # Disable agent forwarding
    AllowAgentForwarding no

    # Set idle timeout (10 minutes)
    ClientAliveInterval 600
    ClientAliveCountMax 3

    # Limit authentication attempts
    MaxAuthTries 3
    MaxStartups 10:30:60
EOF

chmod 644 "$SSH_CONFIG"

echo -e "${GREEN}✓ SSH restrictions configured${NC}"
echo "Configuration file: $SSH_CONFIG"
echo ""

# Test SSH configuration
echo "Testing SSH configuration..."
if sshd -t 0>/dev/null 2>&1; then
    echo -e "${GREEN}✓ SSH configuration is valid${NC}"
else
    echo -e "${RED}✗ SSH configuration has errors${NC}"
    echo "Please check: $SSH_CONFIG"
    exit 1
fi

# Reload SSH
echo "Reloading SSH service..."
systemctl reload sshd || systemctl reload ssh

echo -e "${GREEN}✓ SSH service reloaded${NC}"
echo ""

# Summary
echo "============================================================================"
echo "Setup Complete!"
echo "============================================================================"
echo ""
echo "User: $SSH_USER"
echo "Group: $SSH_GROUP"
echo "Home: /home/$SSH_USER"
echo "Shell: /usr/sbin/nologin (no shell access)"
echo ""
echo "Security Features:"
echo "  • No shell access (nologin)"
echo "  • SSH key-based authentication only"
echo "  • Restricted to localhost:1883 (MQTT broker)"
echo "  • No PTY allocation"
echo "  • No X11 forwarding"
echo "  • No agent forwarding"
echo "  • Idle timeout: 10 minutes"
echo "  • Max auth attempts: 3"
echo ""
echo "============================================================================"
echo "Next Steps:"
echo "============================================================================"
echo ""
echo "1. Add your public SSH key to authorized_keys:"
echo "   $AUTHORIZED_KEYS_FILE"
echo ""
echo "2. Test the tunnel from your local machine:"
echo "   ssh -i ~/.ssh/sumatic_tunnel_key -N -L 1883:localhost:1883 ${SSH_USER}@$(hostname)"
echo ""
echo "3. Update your production .env file:"
echo "   SSH_USER=$SSH_USER"
echo "   SSH_KEY_PATH=/path/to/sumatic_tunnel_key"
echo "   SSH_PASSWORD=  # Leave empty"
echo ""
echo "============================================================================"
