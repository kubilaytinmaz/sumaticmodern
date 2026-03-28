# Sumatic Modern IoT - Production Deployment Guide

**Tarih:** 28 Mart 2026  
**Status:** ✅ PHASE 1 TAMAMLANDI - Production'a hazır  
**Güvenlik Seviyesi:** Yüksek (Critical Security Measures Applied)

---

## 📋 Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Configuration](#environment-configuration)
3. [SSL/HTTPS Setup](#sslhttps-setup)
4. [Docker Deployment](#docker-deployment)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)
8. [Security Hardening](#security-hardening)

---

## Pre-Deployment Checklist

### Phase 1 Security Measures (✅ Completed)

```
[x] SSH authentication: SSH key-based (not password)
[x] JWT_SECRET_KEY: Strong cryptographic key set
[x] DEBUG mode: Disabled (DEBUG=false)
[x] Frontend auth: Middleware bypass closed
[x] MQTT: Anonymous access disabled + authentication enabled
[x] CORS: Restricted to production domains only
[x] API docs: Disabled in production (/docs, /redoc)
[x] HTTPS/SSL: Let's Encrypt with automatic renewal
[x] Backup automation: Daily backups scheduled
[x] Rate limiting: Implemented (IP & username-based)
[x] Security headers: CSP, HSTS, X-Frame-Options, etc.
[x] Input validation: Schema-based validation
```

### Pre-Deployment Tasks

Before deploying to production, ensure:

- [ ] **Domain**: Public domain configured and pointing to server
- [ ] **Server**: Linux server (Ubuntu 20.04+ or similar) with Docker
- [ ] **Ports**: 80 (HTTP) and 443 (HTTPS) open to internet
- [ ] **DNS**: A record pointing to your server IP
- [ ] **Email**: Valid email address for Let's Encrypt notifications
- [ ] **Database backup**: Full backup of current database
- [ ] **Configuration**: All `.env.production` variables set
- [ ] **SSH keys**: Private SSH key for tunnel authentication (if SSH_ENABLED)
- [ ] **MQTT credentials**: Username/password or certificate authentication

---

## Environment Configuration

### 1. Create `.env.production` File

```bash
# Copy production example
cp backend/.env.production.example backend/.env.production

# Edit with your values
nano backend/.env.production
```

### 2. Production Environment Variables

**Backend Configuration (`backend/.env.production`):**

```bash
# ─── Application ──────────────────────────────────────────────────
APP_NAME=Sumatic Modern IoT
APP_VERSION=1.0.0
DEBUG=false                                    # CRITICAL: Always false in production
API_V1_PREFIX=/api/v1
TIMEZONE=Europe/Istanbul

# ─── Database ─────────────────────────────────────────────────────
# SQLite (development only, acceptable for small-medium deployments)
DATABASE_URL=sqlite+aiosqlite:///./sumatic_modern.db

# PostgreSQL (recommended for production)
# DATABASE_URL=postgresql://username:password@db-host:5432/sumatic_modern

# ─── Security ─────────────────────────────────────────────────────
# CRITICAL: Change these values!
JWT_SECRET_KEY=<64-character-random-key>     # Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# ─── CORS ─────────────────────────────────────────────────────────
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# ─── Redis ────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ─── MQTT (Local - through SSH tunnel or direct) ──────────────────
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1883
MQTT_USERNAME=sumatic_user                   # Set in mosquitto.conf
MQTT_PASSWORD=<strong-password>              # Set in mosquitto.conf
MQTT_CLIENT_ID=sumatic-backend
MQTT_TOPIC_ALLDATAS=Alldatas
MQTT_TOPIC_COMMANDS=Commands
MQTT_TLS_ENABLED=false                       # Set true for MQTT TLS (Phase 3)

# ─── SSH Tunnel (for remote MQTT broker) ──────────────────────────
SSH_ENABLED=false                            # Set true only if needed
SSH_HOST=your.remote.host.com
SSH_PORT=22
SSH_USER=tunnel_user
SSH_KEY_PATH=/app/ssh_keys/id_ed25519        # Private key (mounted volume)
# SSH_PASSWORD should NOT be set in production
SSH_REMOTE_MQTT_HOST=127.0.0.1
SSH_REMOTE_MQTT_PORT=1883

# ─── Encryption ───────────────────────────────────────────────────
# ENCRYPTION_KEY: Base64-encoded 32-byte key
# Generate: python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
ENCRYPTION_KEY=<base64-encoded-32-byte-key>

# ─── Device Monitoring ────────────────────────────────────────────
DEVICE_OFFLINE_THRESHOLD_SECONDS=600
DEVICE_RETRY_INTERVAL_SECONDS=60
DEVICE_MAX_RETRIES=5
SNAPSHOT_INTERVAL_MINUTES=10

# ─── Rate Limiting ────────────────────────────────────────────────
RATE_LIMIT_PER_MINUTE=100
```

### 3. Frontend Configuration (`frontend/.env.local`)

```bash
# Production API URL
NEXT_PUBLIC_API_URL=https://yourdomain.com
NEXT_PUBLIC_WS_URL=wss://yourdomain.com
```

### 4. Generate Secure Keys

```bash
# Generate JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"

# Generate random password for MQTT
python3 -c "import secrets; print(secrets.token_urlsafe(16))"
```

---

## SSL/HTTPS Setup

### 1. Prepare Server

```bash
# SSH into production server
ssh -i your-ssh-key user@your-domain.com

# Install Docker and Docker Compose if not already installed
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Clone project repository
git clone https://github.com/yourusername/sumatic-modern.git
cd sumatic-modern
```

### 2. Run SSL Setup Script

```bash
# Make script executable
chmod +x deployment/setup_ssl_certbot.sh

# Run SSL setup (requires sudo)
sudo deployment/setup_ssl_certbot.sh yourdomain.com admin@yourdomain.com
```

**Script will:**
- ✅ Validate domain and email
- ✅ Create SSL directories
- ✅ Generate DH parameters (2048-bit)
- ✅ Request Let's Encrypt certificate
- ✅ Update Nginx configuration
- ✅ Setup automatic renewal cron job
- ✅ Restart Docker containers

### 3. Verify SSL Certificate

```bash
# Check certificate details
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/fullchain.pem -text -noout

# Check expiration date
openssl x509 -in /etc/letsencrypt/live/yourdomain.com/fullchain.pem -noout -dates

# Test SSL
curl -I https://yourdomain.com

# Test with openssl client
openssl s_client -connect yourdomain.com:443

# Check SSL Labs rating
# https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
```

---

## Docker Deployment

### 1. Prepare Docker Environment

```bash
# Copy production docker-compose file
cp docker-compose.prod.yml docker-compose.yml

# Create necessary directories
mkdir -p backend/logs
mkdir -p /var/lib/sumatic/backups
mkdir -p /var/lib/sumatic/data
```

### 2. Configure Docker Volumes

Ensure `docker-compose.prod.yml` has:

```yaml
services:
  backend:
    volumes:
      - ./backend:/app
      - /etc/letsencrypt:/etc/letsencrypt:ro          # SSL certificates
      - ./backend/logs:/app/logs
      - /var/lib/sumatic/data:/app/data              # Data volume
    environment:
      - ENVIRONMENT=production

  nginx:
    volumes:
      - ./deployment/nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/nginx/ssl:ro            # SSL certificates
      - /var/www/certbot:/var/www/certbot             # ACME challenges
    ports:
      - "80:80"
      - "443:443"
```

### 3. Deploy with Docker Compose

```bash
# Build images
docker-compose build

# Start services (detached mode)
docker-compose up -d

# View logs
docker-compose logs -f

# Check container status
docker-compose ps
```

### 4. Initialize Database (First Time)

```bash
# Create admin user
docker-compose exec backend python app/create_admin.py

# Run database migrations (if using Alembic)
docker-compose exec backend alembic upgrade head
```

---

## Post-Deployment Verification

### 1. Health Checks

```bash
# Check application health
curl https://yourdomain.com/health

# Check backend
curl https://yourdomain.com/api/health

# Check frontend (should return 200)
curl -I https://yourdomain.com
```

### 2. Verify Security Headers

```bash
curl -I https://yourdomain.com

# Should include:
# Strict-Transport-Security: max-age=63072000
# X-Frame-Options: SAMEORIGIN
# X-Content-Type-Options: nosniff
# Content-Security-Policy: ...
```

### 3. Test API Endpoints

```bash
# Login
curl -X POST https://yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'

# List devices
curl https://yourdomain.com/api/v1/devices \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Monitor Container Logs

```bash
# Backend logs
docker-compose logs backend

# Nginx logs
docker-compose logs nginx

# MQTT broker logs (if running in container)
docker-compose logs mqtt

# Real-time log streaming
docker-compose logs -f
```

### 5. Database Verification

```bash
# Check database connectivity
docker-compose exec backend python -c "from app.database import async_session_maker; import asyncio; asyncio.run(async_session_maker().__aenter__())"

# Check database tables
sqlite3 ./sumatic_modern.db ".tables"
```

---

## Monitoring & Maintenance

### 1. Automated Backups

```bash
# Verify backup script is executable
ls -la deployment/backup*.sh

# Manual backup
./deployment/backup.sh --full

# View backup status
ls -lh /var/lib/sumatic/backups/

# Restore from backup
./deployment/backup.sh --restore [backup-filename]
```

### 2. Certificate Renewal

```bash
# Check renewal status
sudo docker run --rm -it \
  -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot certificates

# Manual renewal
sudo docker run --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/www/certbot:/var/www/certbot \
  certbot/certbot renew --webroot --webroot-path /var/www/certbot

# Check cron job
sudo crontab -l | grep sumatic_ssl_renewal
```

### 3. Container Management

```bash
# Stop containers
docker-compose stop

# Start containers
docker-compose start

# Restart services
docker-compose restart backend
docker-compose restart nginx

# Remove containers (careful!)
docker-compose down

# View resource usage
docker stats

# Update containers
docker-compose pull
docker-compose up -d
```

### 4. Log Rotation

```bash
# Setup logrotate for application logs
sudo nano /etc/logrotate.d/sumatic-modern

# Add:
/var/lib/sumatic/backups/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
}
```

### 5. System Monitoring

```bash
# Monitor disk usage
df -h

# Check memory usage
free -h

# Monitor MQTT connections
mosquitto_sub -u sumatic_user -P "password" -t '$SYS/broker/clients/connected'

# Check Redis
redis-cli ping
```

---

## Troubleshooting

### Issue: SSL Certificate Not Loading

```bash
# Check certificate files exist
ls -la /etc/letsencrypt/live/yourdomain.com/

# Check Nginx configuration
docker-compose exec nginx nginx -t

# Check Nginx logs
docker-compose logs nginx | grep ssl
```

**Solution:**
```bash
# Re-run SSL setup
sudo deployment/setup_ssl_certbot.sh yourdomain.com admin@yourdomain.com
```

### Issue: 502 Bad Gateway

```bash
# Check backend service status
docker-compose ps backend

# Check backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Issue: MQTT Connection Failed

```bash
# Check MQTT container status
docker-compose ps mqtt

# Check MQTT logs
docker-compose logs mqtt

# Test MQTT connection
mosquitto_sub -h localhost -u sumatic_user -P "password" -t "test"
```

### Issue: Database Locked

```bash
# Restart database service
docker-compose restart backend

# Check database file permissions
ls -la ./sumatic_modern.db

# Ensure proper permissions
chmod 666 ./sumatic_modern.db
```

### Issue: High CPU/Memory Usage

```bash
# Check resource usage
docker stats

# Check for runaway processes
docker-compose logs --tail=100 backend | grep ERROR

# Restart services if needed
docker-compose restart backend nginx
```

---

## Security Hardening

### Additional Security Measures (Phase 2-3)

#### 1. MQTT TLS/SSL (Phase 3)

```bash
# Generate MQTT certificates
cd deployment
chmod +x generate_mqtt_certs.sh
./generate_mqtt_certs.sh

# Update mosquitto.conf with TLS settings
# listener 8883
# protocol mqtt
# tls_version tlsv1.2
# cafile /etc/mosquitto/certs/ca.crt
# certfile /etc/mosquitto/certs/server.crt
# keyfile /etc/mosquitto/certs/server.key
```

#### 2. Fail2Ban Installation (Phase 3)

```bash
# Install Fail2Ban
sudo apt-get install fail2ban

# Configure for Nginx
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local

# Enable jail for Nginx
# [nginx-http-auth]
# enabled = true
# filter = nginx-http-auth
# port = http,https
# logpath = /var/log/nginx/error.log

# Restart Fail2Ban
sudo systemctl restart fail2ban
```

#### 3. PostgreSQL Migration (Phase 2 - Optional)

```bash
# For production with high concurrency, consider PostgreSQL

# Migration script location: backend/app/migrate_doludb.py
docker-compose exec backend python app/migrate_doludb.py \
  --source sqlite:///./sumatic_modern.db \
  --target postgresql://user:pass@postgres:5432/sumatic_modern
```

#### 4. Logging Centralization (Phase 2 - Optional)

```bash
# Setup ELK Stack or send logs to external service
# Update backend logging configuration to send to centralized logging service
```

### Regular Security Checks

```bash
# Monthly: Check for security updates
docker-compose pull
docker-compose build --no-cache

# Quarterly: Security audit
# Review SECURITY_AUDIT_REPORT.md
# Check for new vulnerabilities in dependencies

# Annually: Penetration testing
# Consider hiring security firm for professional assessment
```

---

## Emergency Procedures

### Rollback to Previous Version

```bash
# If deployment fails, rollback:
git revert HEAD
docker-compose down
docker-compose up -d
```

### Emergency Backup

```bash
# If database corrupted
./deployment/backup.sh --restore [previous-backup]

# Restore from backup file
tar -xzf /var/lib/sumatic/backups/backup-20260328.tar.gz
```

### Disable Production Mode (Maintenance)

```bash
# Temporarily disable production
DEBUG=true docker-compose up -d

# Access API docs at /docs for debugging
curl https://yourdomain.com/docs
```

---

## Support & Resources

- **Documentation**: See `plans/SECURITY_AUDIT_REPORT.md` for full security details
- **GitHub**: [Repository URL]
- **Issues**: Report via GitHub issues
- **Security Reports**: security@yourdomain.com

---

## Deployment Success Checklist

```
Final Verification (Before Going Live):

[ ] SSL certificate active and valid
[ ] All security headers present
[ ] HTTPS redirect working (HTTP → HTTPS)
[ ] API endpoints responding with 200 OK
[ ] Database connectivity verified
[ ] MQTT connections established
[ ] Rate limiting functioning
[ ] Backups scheduled and working
[ ] Monitoring alerts configured
[ ] Team trained on operations
[ ] Incident response plan in place
[ ] 24/7 support contact info documented
[ ] Rollback procedure documented
[ ] Disaster recovery plan ready
```

**Status:** ✅ Ready for Production Deployment

---

**Last Updated:** 28 Mart 2026  
**Maintained By:** Security Team  
**Version:** 1.0.0
