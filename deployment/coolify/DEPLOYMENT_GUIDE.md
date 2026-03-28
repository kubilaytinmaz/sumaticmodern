# Sumatic Modern IoT - Coolify Deployment Rehberi

Bu rehber, Sumatic Modern IoT uygulamasını Coolify platformuna deploy etmek için adım adım talimatlar içerir.

## İçindekiler

1. [Ön Hazırlık](#ön-hazırlık)
2. [SSH Key Yapılandırması](#ssh-key-yapılandırması)
3. [Coolify Proje Oluşturma](#coolify-proje-oluşturma)
4. [Environment Variables](#environment-variables)
5. [Deployment](#deployment)
6. [Admin Kullanıcı Oluşturma](#admin-kullanıcı-oluşturma)
7. [SSH Tunnel Kontrolü](#ssh-tunnel-kontrolü)
8. [Sorun Giderme](#sorun-giderme)

---

## Ön Hazırlık

### Gereksinimler

- Coolify kurulu bir VPS sunucu
- Domain name (opsiyonel ama önerilir)
- Git repository (GitHub/GitLab)
- Remote MQTT sunucu erişimi

### Dosyalar

Bu rehberde kullanılan dosyalar:

```
deployment/coolify/
├── .env.coolify.example          # Environment variables şablonu
├── docker-compose.coolify.yml    # Docker compose yapılandırması
├── create_admin_coolify.sh       # Admin kullanıcı oluşturma script'i
├── setup_ssh_key_coolify.sh      # SSH key kurulum script'i
└── DEPLOYMENT_GUIDE.md           # Bu rehber
```

---

## SSH Key Yapılandırması

SSH key, remote MQTT sunucusuna tunnel oluşturmak için gereklidir.

### 1. SSH Key'ler Hazırlandı

SSH key'ler zaten oluşturuldu ve `deployment/coolify/` dizininde mevcut:

- **Private Key**: `deployment/coolify/sumatic_tunnel_key`
- **Public Key**: `deployment/coolify/sumatic_tunnel_key.pub`

### 2. Public Key (Remote Sunucuya Ekleyin)

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHGEHfNti/WiHV6+593Aq4/JQsILyQbop9O3QxOUgOTH sumatic-tunnel@coolify
```

### 3. Remote Sunucuya Key Ekleme

```bash
# Remote sunucuya bağlanın
ssh root@31.58.236.246

# Public key'i authorized_keys'e ekleyin
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHGEHfNti/WiHV6+593Aq4/JQsILyQbop9O3QxOUgOTH sumatic-tunnel@coolify' >> /home/sumatic-tunnel/.ssh/authorized_keys

# İzinleri ayarla
chmod 600 /home/sumatic-tunnel/.ssh/authorized_keys
chown sumatic-tunnel:sumatic-tunnel /home/sumatic-tunnel/.ssh/authorized_keys
```

### 4. SSH Bağlantı Testi

```bash
ssh -i deployment/coolify/sumatic_tunnel_key sumatic-tunnel@31.58.236.246
```

---

## Coolify Proje Oluşturma

### 1. Yeni Proje

1. Coolify dashboard'a gidin
2. **"New Project"** butonuna tıklayın
3. Proje adı: `Sumatic Modern IoT`
4. Git repository'nizi bağlayın

### 2. Docker Compose Kaynağı

1. **"Add Resource"** > **"Docker Compose"**
2. Repository seçin
3. Branch: `main`
4. Docker Compose path: `deployment/coolify/docker-compose.coolify.yml`
5. Build context: `.` (root)

---

## Environment Variables

### Backend Environment Variables

Coolify'da backend servisi için şu environment variables'ları ekleyin:

#### Database

```env
POSTGRES_USER=sumatic_user
POSTGRES_PASSWORD=fFRYbPqdXFzn4KwV0spAW4IUhL39b8PVXhI2gE022rE
POSTGRES_DB=sumatic_production
DATABASE_URL=postgresql+asyncpg://sumatic_user:fFRYbPqdXFzn4KwV0spAW4IUhL39b8PVXhI2gE022rE@postgres:5432/sumatic_production
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

#### Redis

```env
REDIS_PASSWORD=bEYDCdeQRh204E_OkjxxC_Oze_8XHueljdxR8pXUFIY
REDIS_URL=redis://:bEYDCdeQRh204E_OkjxxC_Oze_8XHueljdxR8pXUFIY@redis:6379/0
```

#### MQTT (SSH Tunnel üzerinden)

```env
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1883
MQTT_USERNAME=sumatic-backend-prod
MQTT_PASSWORD=1CsDlPIgPPXA0y2FuOIRLJHytrjZdxxFemQGmd42wM0
MQTT_CLIENT_ID=sumatic-backend-prod
MQTT_TOPIC_ALLDATAS=Alldatas
MQTT_TOPIC_COMMANDS=Commands
```

#### SSH Tunnel

```env
SSH_ENABLED=true
SSH_HOST=31.58.236.246
SSH_PORT=22
SSH_USER=sumatic-tunnel
SSH_KEY_PATH=/app/.ssh/sumatic_tunnel_key
SSH_REMOTE_MQTT_HOST=127.0.0.1
SSH_REMOTE_MQTT_PORT=1883
SSH_LOCAL_MQTT_HOST=127.0.0.1
SSH_LOCAL_MQTT_PORT=1883
SSH_KEEPALIVE=30
```

#### JWT Authentication

```env
JWT_SECRET_KEY=<openssl rand -hex 32 ile oluşturun>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### Security

```env
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
RATE_LIMIT_PER_MINUTE=100
```

#### Admin User

```env
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@sumatic.io
ADMIN_PASSWORD=ChangeThisAdminPassword123!@#
```

### Frontend Environment Variables

```env
NEXT_PUBLIC_API_URL=https://api.your-domain.com
NEXT_PUBLIC_WS_URL=wss://api.your-domain.com
NODE_ENV=production
```

### SSH Private Key Secret

SSH private key'i Coolify secret olarak ekleyin:

1. Backend servisi > Environment Variables
2. **"Add Secret"** butonuna tıklayın
3. Name: `SSH_PRIVATE_KEY`
4. Value: (`deployment/coolify/sumatic_tunnel_key` dosyasının içeriğini yapıştırın)
5. **"Add"** butonuna tıklayın

**Private Key içeriği:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBxhB3zbYv1oh1evufdwKuPyULCC8kG6KfTt0MTlIDkxwAAAKAfBMDKHwTA
ygAAAAtzc2gtZWQyNTUxOQAAACBxhB3zbYv1oh1evufdwKuPyULCC8kG6KfTt0MTlIDkxw
AAAEB43xz2hGs2GRpQir3ZiNNlUsoOOrha0VFREwB6cnMynnGEHfNti/WiHV6+593Aq4/J
QsILyQbop9O3QxOUgOTHAAAAFnN1bWF0aWMtdHVubmVsQGNvb2xpZnkBAgMEBQYH
-----END OPENSSH PRIVATE KEY-----
```

---

## Deployment

### 1. Deploy Başlatma

1. Coolify'da projenize gidin
2. **"Deploy"** butonuna tıklayın
3. Build loglarını izleyin

### 2. Deploy Kontrolü

Deploy tamamlandıktan sonra servislerin durumunu kontrol edin:

```bash
# Container durumları
docker ps

# Backend logları
docker logs sumatic-backend-coolify -f

# Frontend logları
docker logs sumatic-frontend-coolify -f
```

### 3. Health Check

Servislerin sağlıklı olduğunu kontrol edin:

```bash
# Backend health check
curl https://api.your-domain.com/health

# Frontend
curl https://your-domain.com/
```

---

## Admin Kullanıcı Oluşturma

Deploy tamamlandıktan sonra admin kullanıcısı oluşturun:

### 1. Script ile Oluşturma

```bash
cd deployment/coolify
chmod +x create_admin_coolify.sh

# Environment variables ile
export ADMIN_USERNAME=admin
export ADMIN_EMAIL=admin@sumatic.io
export ADMIN_PASSWORD=oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc

./create_admin_coolify.sh
```

### 2. Manuel Oluşturma

Backend container'ına bağlanın:

```bash
docker exec -it sumatic-backend-coolify python3 -c "
import asyncio
from app.database import async_session_maker, init_db
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_admin():
    await init_db()
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == 'admin'))
        if result.scalar_one_or_none():
            print('Admin zaten mevcut')
            return
        admin = User(
            username='admin',
            email='admin@sumatic.io',
            password_hash=get_password_hash('YourPassword123!'),
            full_name='Admin User',
            role='admin',
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print('Admin oluşturuldu')

asyncio.run(create_admin())
"
```

### 3. Giriş

Admin kullanıcı oluşturulduktan sonra:

1. URL: `https://your-domain.com/login`
2. Username: `admin`
3. Password: `oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc`

---

## SSH Tunnel Kontrolü

SSH tunnel'ın çalıştığını kontrol edin:

### 1. Tunnel Durumu

```bash
# Backend container'ında tunnel kontrolü
docker exec sumatic-backend-coolify ps aux | grep ssh

# Tunnel logları
docker logs sumatic-backend-coolify | grep -i tunnel
```

### 2. MQTT Bağlantı Testi

```bash
# Backend container'ında MQTT bağlantı testi
docker exec sumatic-backend-coolify python3 -c "
import asyncio
from app.services.ssh_tunnel import create_ssh_tunnel
from app.services.mqtt_consumer import MQTTConsumer

async def test():
    # Tunnel oluştur
    await create_ssh_tunnel()
    print('SSH tunnel oluşturuldu')
    
    # MQTT bağlantı testi
    consumer = MQTTConsumer()
    await consumer.connect()
    print('MQTT bağlantısı başarılı')
    await consumer.disconnect()

asyncio.run(test())
"
```

### 3. Port Kontrolü

```bash
# Local MQTT portunun dinlendiğini kontrol edin
docker exec sumatic-backend-coolify netstat -tlnp | grep 1883
```

---

## Sorun Giderme

### Container Başlamıyor

```bash
# Container loglarını kontrol edin
docker logs sumatic-backend-coolify
docker logs sumatic-frontend-coolify

# Container durumunu kontrol edin
docker ps -a
```

### Database Bağlantı Hatası

```bash
# PostgreSQL'in çalıştığını kontrol edin
docker exec sumatic-postgres-coolify pg_isready

# Bağlantıyı test edin
docker exec sumatic-postgres-coolify psql -U sumatic_user -d sumatic_production
```

### SSH Tunnel Çalışmıyor

```bash
# SSH key kontrolü
docker exec sumatic-backend-coolify ls -la /app/.ssh/

# SSH bağlantı testi
docker exec sumatic-backend-coolify ssh -i /app/.ssh/sumatic_tunnel_key -v sumatic-tunnel@31.58.236.246
```

### MQTT Bağlantı Hatası

```bash
# Tunnel durumunu kontrol edin
docker exec sumatic-backend-coolify ps aux | grep ssh

# MQTT broker'a erişim testi
docker exec sumatic-backend-coolify nc -zv 127.0.0.1 1883
```

### Admin Giriş Hatası

```bash
# Admin kullanıcısını yeniden oluşturun
cd deployment/coolify
./create_admin_coolify.sh
```

---

## Güvenlik Önerileri

1. **Güçlü Şifreler**: Tüm password'ları güçlü ve benzersiz yapın
2. **SSH Key**: Private key'i güvenli saklayın
3. **HTTPS**: SSL sertifikası kullanın
4. **Firewall**: Gereksiz portları kapatın
5. **Backup**: Düzenli backup alın
6. **Monitoring**: Servisleri izleyin
7. **Updates**: Düzenli güncelleme yapın

---

## İletişim

Sorularınız için:
- GitHub Issues
- Dokümantasyon: `deployment/coolify/README.md`
