#!/bin/bash
# =============================================================================
# Sumatic Modern IoT - Backend Container Entrypoint
# =============================================================================
# Bu script container başladığında çalışır.
# SSH_PRIVATE_KEY varsa key dosyasına yazar.
# SSH_PASSWORD varsa password authentication kullanılır.
# =============================================================================

set -e

echo "[INFO] Sumatic Backend Container Starting..."

# SSH key'i environment variable'dan dosyaya yaz (key-based auth için)
if [ -n "$SSH_PRIVATE_KEY" ]; then
    echo "[INFO] SSH_PRIVATE_KEY detected, creating key file..."
    
    # SSH dizini oluştur
    mkdir -p /app/.ssh
    chmod 700 /app/.ssh
    
    # Private key'i dosyaya yaz
    echo "$SSH_PRIVATE_KEY" > /app/.ssh/sumatic_tunnel_key
    chmod 600 /app/.ssh/sumatic_tunnel_key
    
    # SSH config dosyası oluştur
    cat > /app/.ssh/config <<EOF
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ServerAliveInterval 30
    ServerAliveCountMax 3
EOF
    chmod 600 /app/.ssh/config
    
    echo "[OK] SSH key file created at /app/.ssh/sumatic_tunnel_key"
    
elif [ -n "$SSH_PASSWORD" ]; then
    echo "[INFO] SSH_PASSWORD detected, will use password authentication."
    echo "[INFO] SSH_KEY_PATH not required for password authentication."
    
    # SSH config dizini oluştur (gerekli)
    mkdir -p /app/.ssh
    chmod 700 /app/.ssh
    
    # SSH config dosyası oluştur
    cat > /app/.ssh/config <<EOF
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ServerAliveInterval 30
    ServerAliveCountMax 3
EOF
    chmod 600 /app/.ssh/config
    
else
    if [ "$SSH_ENABLED" = "true" ]; then
        echo "[WARN] SSH_ENABLED=true but neither SSH_PRIVATE_KEY nor SSH_PASSWORD is set!"
        echo "[WARN] SSH tunnel will fail to connect."
    else
        echo "[INFO] SSH tunnel disabled (SSH_ENABLED != true)."
    fi
fi

# Uygulamayı başlat
echo "[INFO] Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
