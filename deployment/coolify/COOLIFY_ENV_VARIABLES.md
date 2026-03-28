# Coolify Environment Variables - IP Adresi ile Kullanım

Bu dosya, Coolify'da Production ve Preview Environment Variables olarak gireceğiniz tüm değerleri içerir.

## 📝 Production Environment Variables

Coolify'da **Production** sekmesinde aşağıdaki değişkenleri tek tek ekleyin:

### Database Variables

```
POSTGRES_USER=sumatic_user
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE
POSTGRES_DB=sumatic_production
DATABASE_URL=postgresql+asyncpg://sumatic_user:YOUR_SECURE_PASSWORD_HERE@postgres:5432/sumatic_production
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

### Redis Variables

```
REDIS_PASSWORD=YOUR_REDIS_PASSWORD_HERE
REDIS_URL=redis://:YOUR_REDIS_PASSWORD_HERE@redis:6379/0
```

### MQTT Variables

```
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1883
MQTT_USERNAME=sumatic-backend-prod
MQTT_PASSWORD=YOUR_MQTT_PASSWORD_HERE
MQTT_CLIENT_ID=sumatic-backend-prod
MQTT_TOPIC_ALLDATAS=Alldatas
MQTT_TOPIC_COMMANDS=Commands
```

### SSH Tunnel Variables

```
SSH_ENABLED=true
SSH_HOST=YOUR_SSH_HOST_IP_HERE
SSH_PORT=22
SSH_USER=sumatic-tunnel
SSH_KEY_PATH=/app/.ssh/sumatic_tunnel_key
SSH_REMOTE_MQTT_HOST=127.0.0.1
SSH_REMOTE_MQTT_PORT=1883
SSH_LOCAL_MQTT_HOST=127.0.0.1
SSH_LOCAL_MQTT_PORT=1883
SSH_KEEPALIVE=30
```

### JWT Variables

```
JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY_HERE
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Admin Variables

```
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@sumatic.io
ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD_HERE
```

### Security Variables

```
CORS_ORIGINS=http://your-coolify-server-ip:3000,http://your-coolify-server-ip
RATE_LIMIT_PER_MINUTE=100
```

**Not**: `your-coolify-server-ip` kısmını Coolify sunucusunun IP adresi ile değiştirin.
Örneğin: `CORS_ORIGINS=http://192.168.1.100:3000,http://192.168.1.100`

### Application Variables

```
APP_NAME=Sumatic Modern IoT
APP_VERSION=1.0.0
DEBUG=false
API_V1_PREFIX=/api/v1
TIMEZONE=Europe/Istanbul
```

### Device Monitoring Variables

```
DEVICE_OFFLINE_THRESHOLD_SECONDS=600
DEVICE_RETRY_INTERVAL_SECONDS=60
DEVICE_MAX_RETRIES=5
SNAPSHOT_INTERVAL_MINUTES=10
SPIKE_STREAK_THRESHOLD=5
SPIKE_WINDOW_SIZE=5
```

### Frontend Variables

```
NEXT_PUBLIC_API_URL=http://your-coolify-server-ip:8000
NEXT_PUBLIC_WS_URL=ws://your-coolify-server-ip:8000
NODE_ENV=production
```

**Not**: `your-coolify-server-ip` kısmını Coolify sunucusunun IP adresi ile değiştirin.
Örneğin: `NEXT_PUBLIC_API_URL=http://192.168.1.100:8000`

---

## 🔐 Secrets (Production)

Coolify'da **Secrets** olarak eklemeniz gereken hassas değerler:

### SSH Private Key Secret

1. **Add Secret** butonuna tıklayın
2. **Name**: `SSH_PRIVATE_KEY`
3. **Value**: Kendi SSH private key'inizi buraya yapıştırın

**Not**: SSH key'inizi `ssh-keygen -t ed25519` komutu ile oluşturabilirsiniz.

---

## 📋 Preview Environment Variables

Coolify'da **Preview** sekmesinde aşağıdaki değişkenleri tek tek ekleyin:

### Database Variables

```
POSTGRES_USER=sumatic_user_preview
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE
POSTGRES_DB=sumatic_preview
DATABASE_URL=postgresql+asyncpg://sumatic_user_preview:YOUR_SECURE_PASSWORD_HERE@postgres:5432/sumatic_preview
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

### Redis Variables

```
REDIS_PASSWORD=YOUR_REDIS_PASSWORD_HERE
REDIS_URL=redis://:YOUR_REDIS_PASSWORD_HERE@redis:6379/1
```

### MQTT Variables

```
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1883
MQTT_USERNAME=sumatic-backend-preview
MQTT_PASSWORD=YOUR_MQTT_PASSWORD_HERE
MQTT_CLIENT_ID=sumatic-backend-preview
MQTT_TOPIC_ALLDATAS=Alldatas
MQTT_TOPIC_COMMANDS=Commands
```

### SSH Tunnel Variables

```
SSH_ENABLED=true
SSH_HOST=YOUR_SSH_HOST_IP_HERE
SSH_PORT=22
SSH_USER=sumatic-tunnel
SSH_KEY_PATH=/app/.ssh/sumatic_tunnel_key
SSH_REMOTE_MQTT_HOST=127.0.0.1
SSH_REMOTE_MQTT_PORT=1883
SSH_LOCAL_MQTT_HOST=127.0.0.1
SSH_LOCAL_MQTT_PORT=1883
SSH_KEEPALIVE=30
```

### JWT Variables

```
JWT_SECRET_KEY=YOUR_JWT_SECRET_KEY_HERE
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Admin Variables

```
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@sumatic.io
ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD_HERE
```

### Security Variables

```
CORS_ORIGINS=http://your-coolify-server-ip:3000,http://your-coolify-server-ip
RATE_LIMIT_PER_MINUTE=100
```

**Not**: `your-coolify-server-ip` kısmını Coolify sunucusunun IP adresi ile değiştirin.

### Application Variables

```
APP_NAME=Sumatic Modern IoT (Preview)
APP_VERSION=1.0.0-preview
DEBUG=false
API_V1_PREFIX=/api/v1
TIMEZONE=Europe/Istanbul
```

### Device Monitoring Variables

```
DEVICE_OFFLINE_THRESHOLD_SECONDS=600
DEVICE_RETRY_INTERVAL_SECONDS=60
DEVICE_MAX_RETRIES=5
SNAPSHOT_INTERVAL_MINUTES=10
SPIKE_STREAK_THRESHOLD=5
SPIKE_WINDOW_SIZE=5
```

### Frontend Variables

```
NEXT_PUBLIC_API_URL=http://your-coolify-server-ip:8000
NEXT_PUBLIC_WS_URL=ws://your-coolify-server-ip:8000
NODE_ENV=development
```

**Not**: `your-coolify-server-ip` kısmını Coolify sunucusunun IP adresi ile değiştirin.

---

## 🔐 Secrets (Preview)

Preview için de aynı SSH Private Key secret'ini ekleyin:

### SSH Private Key Secret

1. **Add Secret** butonuna tıklayın
2. **Name**: `SSH_PRIVATE_KEY`
3. **Value**: Production ile aynı private key içeriğini yapıştırın (kendi key'inizi kullanın)

---

## 📝 Önemli Notlar

### IP Adresi Değiştirme

Tüm `your-coolify-server-ip` yazan yerleri kendi Coolify sunucunuzun IP adresi ile değiştirin:

**Örnek:**
- Eğer Coolify sunucunuzun IP adresi `192.168.1.100` ise:
  - `CORS_ORIGINS=http://192.168.1.100:3000,http://192.168.1.100`
  - `NEXT_PUBLIC_API_URL=http://192.168.1.100:8000`
  - `NEXT_PUBLIC_WS_URL=ws://192.168.1.100:8000`

### Port Bilgileri

- **Frontend Port**: 3000
- **Backend Port**: 8000
- **PostgreSQL Port**: 5432
- **Redis Port**: 6379
- **MQTT Port**: 1883 (SSH tunnel üzerinden)

### Preview vs Production

- **Production**: Ana deployment için kullanılır
- **Preview**: Test ve geliştirme için kullanılır (farklı database)
- Her ikisi de aynı SSH tunnel'ı kullanır
- Preview için ayrı bir database oluşturulur (`sumatic_preview`)

---

## ✅ Kontrol Listesi

Environment Variables eklerken:

- [ ] Production environment variables eklendi
- [ ] Preview environment variables eklendi
- [ ] SSH_PRIVATE_KEY secret eklendi (Production)
- [ ] SSH_PRIVATE_KEY secret eklendi (Preview)
- [ ] IP adresleri doğru şekilde değiştirildi
- [ ] CORS_ORIGINS doğru yapılandırıldı
- [ ] NEXT_PUBLIC_API_URL doğru yapılandırıldı
- [ ] NEXT_PUBLIC_WS_URL doğru yapılandırıldı

---

## 🚀 Sonraki Adım

Environment Variables'ları ekledikten sonra:

1. **Deploy** butonuna tıklayın
2. Build loglarını izleyin
3. Deploy tamamlandıktan sonra admin kullanıcısı oluşturun
4. `http://your-coolify-server-ip:3000` adresinden giriş yapın

Admin giriş bilgileri:
- **Username**: `admin`
- **Password**: (Yukarıda belirlediğiniz şifre)
