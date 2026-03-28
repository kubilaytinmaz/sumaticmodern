# Sumatic Modern IoT - Coolify Deployment Guide

Bu rehber, Sumatic Modern IoT uygulamasını [Coolify](https://coolify.io/) kullanarak nasıl deploy edeceğinizi açıklar.

## İçindekiler

1. [Gereksinimler](#gereksinimler)
2. [Coolify Kurulumu](#coolify-kurulumu)
3. [Proje Yapılandırması](#proje-yapılandırması)
4. [Servis Dağıtımı](#servis-dağıtımı)
5. [Domain ve SSL Yapılandırması](#domain-ve-ssl-yapılandırması)
6. [Environment Variables](#environment-variables)
7. [Backup Stratejisi](#backup-stratejisi)
8. [Sorun Giderme](#sorun-giderme)

---

## Gereksinimler

- Bir VPS veya Dedicated Server (minimum 2GB RAM, 2 vCPU)
- Domain name (opsiyonel ama önerilir)
- Docker ve Docker Compose yüklü sunucu
- SSH erişimi

---

## Coolify Kurulumu

### 1. Sunucunuza Bağlanın

```bash
ssh root@your-server-ip
```

### 2. Coolify'ı Kurun

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

Kurulum tamamlandıktan sonra:
- Coolify UI: `http://your-server-ip:3000`
- İlk kurulumda admin şifresi oluşturmanız istenecektir.

### 3. Güvenlik Duvarı Ayarları

Gerekli portları açın:

```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

---

## Proje Yapılandırması

### 1. Yeni Proje Oluşturun

1. Coolify dashboard'da **"New Project"** butonuna tıklayın
2. Proje adı: `Sumatic Modern IoT`
3. Açıklama: `IoT Device Monitoring Platform`

### 2. Git Repository Bağlayın

1. Proje içinde **"Add Resource"** > **"Git Repository"**
2. GitHub/GitLab/Gitea repository'nizi bağlayın
3. Repository: `your-username/sumaticmodern`
4. Branch: `main`

---

## Servis Dağıtımı

### Docker Compose ile Dağıtım (Önerilen)

1. **"Add Resource"** > **"Docker Compose"**
2. Kaynak: Git Repository
3. Docker Compose dosyası: `docker-compose.prod.yml`
4. Build context: `.` (root)

### Manuel Servis Dağıtımı

Her servis için ayrı ayrı dağıtım yapabilirsiniz:

#### PostgreSQL + TimescaleDB

1. **"Add Resource"** > **"Database"** > **"PostgreSQL"**
2. Image: `timescale/timescaledb:latest-pg15`
3. Environment variables:
   ```env
   POSTGRES_USER=sumatic
   POSTGRES_PASSWORD=<secure-password>
   POSTGRES_DB=sumatic_db
   ```
4. Volume: `/var/lib/postgresql/data`

#### Redis

1. **"Add Resource"** > **"Database"** > **"Redis"**
2. Image: `redis:7-alpine`
3. Command: `redis-server --appendonly yes`

#### Backend (FastAPI)

1. **"Add Resource"** > **"Service"** > **"Docker"**
2. Build context: `./backend`
3. Dockerfile: `Dockerfile`
4. Target: `production`
5. Port: `8000`

#### Frontend (Next.js)

1. **"Add Resource"** > **"Service"** > **"Docker"**
2. Build context: `./frontend`
3. Dockerfile: `Dockerfile`
4. Target: `runner`
5. Port: `3000`

---

## Domain ve SSL Yapılandırması

### 1. Domain Ekleme

1. Coolify'da **"Domains"** bölümüne gidin
2. **"Add Domain"** butonuna tıklayın
3. Domain: `sumatic.yourdomain.com`
4. DNS kayıtlarını yapılandırın:
   ```
   A    sumatic    your-server-ip
   ```

### 2. SSL Sertifikası

Coolify otomatik Let's Encrypt SSL sertifikası sağlar:

1. Domain ayarlarında **"SSL"** seçeneğini etkinleştirin
2. **"Let's Encrypt"** seçin
3. Sertifika otomatik olarak yenilenecektir

### 3. Subdomain Yapılandırması (Opsiyonel)

Farklı servisler için subdomain kullanabilirsiniz:

| Subdomain | Servis | Açıklama |
|-----------|--------|----------|
| `sumatic.yourdomain.com` | Frontend | Ana uygulama |
| `api.sumatic.yourdomain.com` | Backend | API endpoint'leri |
| `mqtt.sumatic.yourdomain.com` | MQTT | WebSocket bağlantıları |

---

## Environment Variables

### Production Environment Variables

Coolify'da her servis için environment variables ekleyin:

#### Backend

```env
DATABASE_URL=postgresql+asyncpg://sumatic:<password>@postgres:5432/sumatic_db
REDIS_URL=redis://redis:6379/0
MQTT_BROKER_HOST=mqtt
MQTT_BROKER_PORT=1883
CORS_ORIGINS=https://sumatic.yourdomain.com
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
DEBUG=false
```

#### Frontend

```env
NEXT_PUBLIC_API_URL=https://api.sumatic.yourdomain.com
NEXT_PUBLIC_WS_URL=wss://api.sumatic.yourdomain.com
NODE_ENV=production
```

### Güvenli Secret Yönetimi

1. Hassas değerler için Coolify'nın **"Secrets"** özelliğini kullanın
2. JWT secret ve database password için güçlü, rastgele değerler oluşturun:
   ```bash
   openssl rand -hex 32
   ```

---

## Backup Stratejisi

### 1. Otomatik PostgreSQL Backup

Coolify'nın yerleşik backup özelliğini kullanın:

1. PostgreSQL servisine gidin
2. **"Backups"** sekmesine tıklayın
3. Backup ayarları:
   - Frequency: Daily
   - Retention: 7 days
   - Storage: Local veya S3

### 2. Manuel Backup Script

```bash
# deployment/backup.sh çalıştırın
./deployment/backup.sh
```

### 3. Backup'dan Geri Yükleme

```bash
# PostgreSQL backup'dan geri yükleme
docker exec -i sumatic-postgres-prod psql -U sumatic -d sumatic_db < backup_20240101.sql
```

---

## Monitoring ve Logs

### Servis Sağlığı

1. Coolify dashboard'da her servisin durumunu izleyin
2. Health check endpoint'leri:
   - Backend: `https://api.yourdomain.com/health`
   - Frontend: `https://sumatic.yourdomain.com/`

### Log Görüntüleme

1. Servis detaylarına gidin
2. **"Logs"** sekmesinden canlı logları izleyin

### Resource Kullanımı

Coolify, her servisin CPU ve RAM kullanımını gösterir.

---

## Sorun Giderme

### Yaygın Sorunlar

#### 1. Container Başlatılamıyor

```bash
# Container loglarını kontrol edin
docker logs sumatic-backend-prod

# Container durumunu kontrol edin
docker ps -a
```

#### 2. Database Bağlantı Hatası

```bash
# PostgreSQL'in çalıştığını kontrol edin
docker exec -it sumatic-postgres-prod pg_isready

# Bağlantıyı test edin
docker exec -it sumatic-postgres-prod psql -U sumatic -d sumatic_db
```

#### 3. SSL Sertifikası Hatası

```bash
# Let's Encrypt loglarını kontrol edin
docker logs coolify-proxy

# Sertifikayı yenileyin
docker exec coolify-proxy certbot renew
```

#### 4. Memory Hatası

```bash
# Docker resource kullanımını kontrol edin
docker stats

# Gerekirse resource limitlerini artırın
```

### Faydalı Komutlar

```bash
# Tüm servisleri yeniden başlat
docker-compose -f docker-compose.prod.yml restart

# Belirli bir servisi yeniden build et
docker-compose -f docker-compose.prod.yml up -d --build backend

# Volume'ları temizle (dikkat!)
docker-compose -f docker-compose.prod.yml down -v
```

---

## Güvenlik Önerileri

1. **Strong Passwords**: Tüm servisler için güçlü şifreler kullanın
2. **Firewall**: Gereksiz portları kapatın
3. **Updates**: Düzenli olarak image'leri güncelleyin
4. **Backups**: Günlük backup alın
5. **Monitoring**: Resource kullanımını izleyin
6. **SSL**: Tüm trafiği HTTPS üzerinden yönlendirin

---

## İletişim ve Destek

Sorun yaşarsanız:
- GitHub Issues: `https://github.com/your-username/sumaticmodern/issues`
- Dokümantasyon: `plans/MODERN_ARCHITECTURE_PLAN.md`
