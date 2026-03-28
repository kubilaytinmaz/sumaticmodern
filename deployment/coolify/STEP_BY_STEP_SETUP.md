# Sumatic Modern IoT - Coolify Adım Adım Kurulum Rehberi

Bu rehber, Coolify'ı yeni kurduktan sonra Sumatic Modern IoT uygulamasını deploy etmek için yapmanız gereken tüm adımları sırasıyla anlatır.

## 📋 İçindekiler

1. [Coolify İlk Kurulum](#1-coolify-ilk-kurulum)
2. [Remote Sunucu SSH Ayarları](#2-remote-sunucu-ssh-ayarları)
3. [Coolify Proje Oluşturma](#3-coolify-proje-oluşturma)
4. [Environment Variables Ayarlama](#4-environment-variables-ayarlama)
5. [SSH Key Yapılandırma](#5-ssh-key-yapılandırma)
6. [Deploy Başlatma](#6-deploy-başlatma)
7. [Admin Kullanıcı Oluşturma](#7-admin-kullanıcı-oluşturma)
8. [Domain ve SSL Ayarlama](#8-domain-ve-ssl-ayarlama)
9. [Test ve Doğrulama](#9-test-ve-doğrulama)

---

## 1. Coolify İlk Kurulum

### 1.1. Coolify'a Erişim

1. Tarayıcınızda Coolify sunucusunun IP adresine gidin:
   ```
   http://your-coolify-server-ip:3000
   ```

2. İlk kurulum ekranında admin hesabı oluşturun:
   - **Admin Email**: sizin@email.com
   - **Admin Password**: Güçlü bir şifre belirleyin
   - **Confirm Password**: Şifreyi tekrar girin

3. **Create Account** butonuna tıklayın

### 1.2. Coolify Dashboard

Giriş yaptıktan sonra Coolify dashboard'unu göreceksiniz.

---

## 2. Remote Sunucu SSH Ayarları

### 2.1. Remote MQTT Sunucusuna Bağlanın

```bash
# Local bilgisayarınızdan terminal açın
ssh root@31.58.236.246
```

### 2.2. SSH Kullanıcısı Oluşturun

```bash
# SSH kullanıcısı oluştur
useradd -m -s /bin/bash sumatic-tunnel

# SSH dizini oluştur
mkdir -p /home/sumatic-tunnel/.ssh
chmod 700 /home/sumatic-tunnel/.ssh
chown sumatic-tunnel:sumatic-tunnel /home/sumatic-tunnel/.ssh
```

### 2.3. Public Key'i Ekleyin

```bash
# Public key'i authorized_keys'e ekle
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHGEHfNti/WiHV6+593Aq4/JQsILyQbop9O3QxOUgOTH sumatic-tunnel@coolify' >> /home/sumatic-tunnel/.ssh/authorized_keys

# İzinleri ayarla
chmod 600 /home/sumatic-tunnel/.ssh/authorized_keys
chown sumatic-tunnel:sumatic-tunnel /home/sumatic-tunnel/.ssh/authorized_keys
```

### 2.4. SSH Bağlantısını Test Edin

Remote sunucundan çıkın ve local bilgisayarınızda test edin:

```bash
# Remote sunucundan çıkın
exit

# SSH bağlantısını test edin
ssh -i deployment/coolify/sumatic_tunnel_key sumatic-tunnel@31.58.236.246
```

Başarılı olursa remote sunucuya bağlanacaksınız.

---

## 3. Coolify Proje Oluşturma

### 3.1. Yeni Proje Oluşturun

1. Coolify dashboard'da **"New Project"** butonuna tıklayın
2. Proje bilgilerini girin:
   - **Project Name**: `Sumatic Modern IoT`
   - **Description**: `IoT Device Monitoring Platform`
3. **Create Project** butonuna tıklayın

### 3.2. Git Repository Bağlayın

1. Proje içinde **"Add Resource"** > **"Git Repository"** seçeneğine tıklayın
2. Git sağlayıcınızı seçin (GitHub/GitLab/Gitea)
3. Repository'nizi seçin: `sumaticmodern`
4. Branch: `main`
5. **Connect** butonuna tıklayın

---

## 4. Environment Variables Ayarlama

### 4.1. Docker Compose Kaynağı Oluşturun

1. Proje içinde **"Add Resource"** > **"Docker Compose"** seçeneğine tıklayın
2. Aşağıdaki bilgileri girin:
   - **Resource Name**: `sumatic-modern-stack`
   - **Repository**: `sumaticmodern`
   - **Branch**: `main`
   - **Docker Compose Path**: `deployment/coolify/docker-compose.coolify.yml`
   - **Build Context**: `.`
3. **Continue** butonuna tıklayın

### 4.2. Backend Environment Variables

Backend servisi için şu environment variables'ları ekleyin:

#### Database Variables

```
POSTGRES_USER=sumatic_user
POSTGRES_PASSWORD=fFRYbPqdXFzn4KwV0spAW4IUhL39b8PVXhI2gE022rE
POSTGRES_DB=sumatic_production
DATABASE_URL=postgresql+asyncpg://sumatic_user:fFRYbPqdXFzn4KwV0spAW4IUhL39b8PVXhI2gE022rE@postgres:5432/sumatic_production
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

#### Redis Variables

```
REDIS_PASSWORD=bEYDCdeQRh204E_OkjxxC_Oze_8XHueljdxR8pXUFIY
REDIS_URL=redis://:bEYDCdeQRh204E_OkjxxC_Oze_8XHueljdxR8pXUFIY@redis:6379/0
```

#### MQTT Variables

```
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1883
MQTT_USERNAME=sumatic-backend-prod
MQTT_PASSWORD=1CsDlPIgPPXA0y2FuOIRLJHytrjZdxxFemQGmd42wM0
MQTT_CLIENT_ID=sumatic-backend-prod
MQTT_TOPIC_ALLDATAS=Alldatas
MQTT_TOPIC_COMMANDS=Commands
```

#### SSH Tunnel Variables

```
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

#### JWT Variables

```
JWT_SECRET_KEY=037f148dd3367297c31571a0483c6d7e0a9f00e1413b5c87e226a3ef3dba91e5
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### Admin Variables

```
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@sumatic.io
ADMIN_PASSWORD=oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc
```

#### Security Variables

```
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
RATE_LIMIT_PER_MINUTE=100
```

#### Application Variables

```
APP_NAME=Sumatic Modern IoT
APP_VERSION=1.0.0
DEBUG=false
API_V1_PREFIX=/api/v1
TIMEZONE=Europe/Istanbul
```

### 4.3. Frontend Environment Variables

Frontend servisi için şu environment variables'ları ekleyin:

```
NEXT_PUBLIC_API_URL=https://api.your-domain.com
NEXT_PUBLIC_WS_URL=wss://api.your-domain.com
NODE_ENV=production
```

---

## 5. SSH Key Yapılandırma

### 5.1. SSH Private Key Secret Olarak Ekleyin

1. Backend servisi > **Environment Variables** sekmesine gidin
2. **"Add Secret"** butonuna tıklayın
3. Aşağıdaki bilgileri girin:
   - **Name**: `SSH_PRIVATE_KEY`
   - **Value**: (Aşağıdaki private key içeriğini yapıştırın)
4. **Add** butonuna tıklayın

**Private Key:**
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

## 6. Deploy Başlatma

### 6.1. Deploy'i Başlatın

1. Coolify dashboard'da projenize gidin
2. Docker Compose servisine tıklayın
3. **"Deploy"** butonuna tıklayın
4. Build loglarını izleyin

### 6.2. Deploy Durumunu Kontrol Edin

Deploy tamamlandıktan sonra servislerin durumunu kontrol edin:

```bash
# Coolify sunucusuna SSH ile bağlanın
ssh root@coolify-server-ip

# Container durumlarını kontrol edin
docker ps

# Backend loglarını kontrol edin
docker logs sumatic-backend-coolify -f

# Frontend loglarını kontrol edin
docker logs sumatic-frontend-coolify -f
```

### 6.3. Health Check

Servislerin sağlıklı olduğunu kontrol edin:

```bash
# Backend health check
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000/
```

---

## 7. Admin Kullanıcı Oluşturma

### 7.1. Admin Kullanıcısı Oluşturun

Deploy tamamlandıktan sonra admin kullanıcısı oluşturun:

```bash
# Coolify sunucusuna bağlanın
ssh root@coolify-server-ip

# Backend container'ına bağlanın
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
            password_hash=get_password_hash('oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc'),
            full_name='Admin User',
            role='admin',
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        print('Admin oluşturuldu: admin / oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc')

asyncio.run(create_admin())
"
```

### 7.2. Admin Giriş Bilgileri

- **URL**: `http://your-coolify-server-ip:3000` (veya domain'iniz)
- **Username**: `admin`
- **Password**: `oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc`

---

## 8. Domain ve SSL Ayarlama

### 8.1. Domain Ekleme

1. Coolify dashboard'da projenize gidin
2. Frontend servisine tıklayın
3. **"Domains"** sekmesine tıklayın
4. **"Add Domain"** butonuna tıklayın
5. Domain bilgilerinizi girin:
   - **Domain**: `sumatic.yourdomain.com`
   - **Type**: `Production`
6. **Add** butonuna tıklayın

### 8.2. DNS Ayarları

Domain sağlayıcınızda DNS kaydı oluşturun:

```
Type: A
Name: sumatic
Value: your-coolify-server-ip
TTL: 3600
```

### 8.3. SSL Sertifika

1. Domain ayarlarında **"SSL"** seçeneğini etkinleştirin
2. **"Let's Encrypt"** seçin
3. **"Save"** butonuna tıklayın
4. SSL sertifikası otomatik olarak oluşturulacaktır

---

## 9. Test ve Doğrulama

### 9.1. Uygulamaya Erişim

1. Tarayıcınızda domain adresine gidin:
   ```
   https://sumatic.yourdomain.com
   ```

2. Login sayfası görmeniz gerekiyor

### 9.2. Admin Girişi

1. Admin bilgileriyle giriş yapın:
   - Username: `admin`
   - Password: `oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc`

2. Dashboard'u görmeniz gerekiyor

### 9.3. SSH Tunnel Kontrolü

SSH tunnel'ın çalıştığını kontrol edin:

```bash
# Coolify sunucusuna bağlanın
ssh root@coolify-server-ip

# Backend container'ında tunnel kontrolü
docker exec sumatic-backend-coolify ps aux | grep ssh

# MQTT bağlantı testi
docker exec sumatic-backend-coolify python3 -c "
import asyncio
from app.services.ssh_tunnel import create_ssh_tunnel

async def test():
    await create_ssh_tunnel()
    print('SSH tunnel başarılı')

asyncio.run(test())
"
```

### 9.4. MQTT Bağlantı Testi

```bash
# MQTT portunun dinlendiğini kontrol edin
docker exec sumatic-backend-coolify netstat -tlnp | grep 1883
```

---

## 🔧 Sorun Giderme

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

### Admin Giriş Hatası

```bash
# Admin kullanıcısını yeniden oluşturun
# (Bölüm 7.1'deki komutu tekrar çalıştırın)
```

---

## ✅ Kontrol Listesi

Deploy öncesi kontrol listesi:

- [ ] Coolify kuruldu ve admin hesabı oluşturuldu
- [ ] Remote sunucuda SSH kullanıcısı oluşturuldu
- [ ] Public key remote sunucuya eklendi
- [ ] SSH bağlantısı test edildi
- [ ] Coolify projesi oluşturuldu
- [ ] Git repository bağlandı
- [ ] Environment variables eklendi
- [ ] SSH private key secret olarak eklendi
- [ ] Deploy başlatıldı
- [ ] Servisler çalışıyor
- [ ] Admin kullanıcısı oluşturuldu
- [ ] Domain eklendi
- [ ] SSL sertifikası oluşturuldu
- [ ] Uygulamaya erişim test edildi
- [ ] SSH tunnel çalışıyor
- [ ] MQTT bağlantısı başarılı

---

## 📞 Destek

Sorun yaşarsanız:
- GitHub Issues
- Detaylı rehber: [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md)
- SSH key rehberi: [`SSH_KEY_WINDOWS_GUIDE.md`](SSH_KEY_WINDOWS_GUIDE.md)
- Kimlik bilgileri: [`CREDENTIALS.md`](CREDENTIALS.md)

---

**Tebrikler! Sumatic Modern IoT uygulamanız Coolify üzerinde başarıyla deploy edildi.** 🎉
