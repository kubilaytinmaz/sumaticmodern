#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - MQTT TLS Certificate Generator
# =============================================================================
# This script generates self-signed TLS certificates for MQTT broker
# For production, use certificates from a trusted CA (Let's Encrypt, etc.)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="$SCRIPT_DIR/../mqtt-broker/certs"
CONFIG_DIR="$SCRIPT_DIR/../mqtt-broker"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================================"
echo "Sumatic Modern IoT - MQTT TLS Certificate Generator"
echo "============================================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}[ERROR] This script must be run as root${NC}"
    exit 1
fi

# Create certificates directory
echo -e "${GREEN}[INFO] Creating certificates directory...${NC}"
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

# Certificate configuration
COUNTRY="TR"
STATE="Istanbul"
CITY="Istanbul"
ORGANIZATION="Sumatic"
ORGANIZATIONAL_UNIT="IoT"
COMMON_NAME="sumatic-mqtt-broker"
EMAIL="admin@sumatic.local"

# Generate CA private key and certificate
echo -e "${GREEN}[INFO] Generating CA private key and certificate...${NC}"
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$COMMON_NAME CA/emailAddress=$EMAIL"

# Generate server private key
echo -e "${GREEN}[INFO] Generating server private key...${NC}"
openssl genrsa -out server.key 2048

# Generate server certificate signing request (CSR)
echo -e "${GREEN}[INFO] Generating server certificate signing request...${NC}"
openssl req -new -key server.key -out server.csr -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$COMMON_NAME/emailAddress=$EMAIL"

# Create a certificate configuration file for SAN (Subject Alternative Names)
echo -e "${GREEN}[INFO] Creating certificate configuration with SAN...${NC}"
cat > server_cert.cnf <<EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $CITY
O = $ORGANIZATION
OU = $ORGANIZATIONAL_UNIT
CN = $COMMON_NAME
emailAddress = $EMAIL

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.sumatic.local
DNS.3 = sumatic-mqtt-broker
DNS.4 = *.sumatic-mqtt-broker
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

# Sign the server certificate with CA
echo -e "${GREEN}[INFO] Signing server certificate with CA...${NC}"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 3650 -sha256 -extfile server_cert.cnf -extensions v3_req

# Generate client private key and certificate (for backend)
echo -e "${GREEN}[INFO] Generating client private key and certificate...${NC}"
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=sumatic-backend/emailAddress=$EMAIL"

# Sign the client certificate with CA
echo -e "${GREEN}[INFO] Signing client certificate with CA...${NC}"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 3650 -sha256

# Set appropriate permissions
echo -e "${GREEN}[INFO] Setting file permissions...${NC}"
chmod 600 ca.key server.key client.key
chmod 644 ca.crt server.crt client.crt

# Clean up temporary files
rm -f server.csr client.csr server_cert.cnf

# Verify certificates
echo -e "${GREEN}[INFO] Verifying certificates...${NC}"
openssl verify -CAfile ca.crt server.crt
openssl verify -CAfile ca.crt client.crt

echo ""
echo -e "${GREEN}[OK] Certificates generated successfully!${NC}"
echo ""
echo "Generated files:"
echo "  - CA Certificate:     $CERT_DIR/ca.crt"
echo "  - Server Certificate: $CERT_DIR/server.crt"
echo "  - Server Key:         $CERT_DIR/server.key"
echo "  - Client Certificate: $CERT_DIR/client.crt"
echo "  - Client Key:         $CERT_DIR/client.key"
echo ""
echo -e "${YELLOW}[WARN] For production use, obtain certificates from a trusted CA${NC}"
echo -e "${YELLOW}[WARN] Self-signed certificates are suitable for development/testing only${NC}"
echo ""
echo "Next steps:"
echo "  1. Copy ca.crt to all MQTT clients"
echo "  2. Update mosquitto.conf to use the certificates"
echo "  3. Restart the MQTT broker"
echo ""
