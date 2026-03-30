# Coolify Deployment Sorunları ve Çözümleri

## Tespit Edilen Sorunlar

Backend'inizde `/health` endpoint'inden alınan yanıt:

```json
{
  "status": "degraded",
  "database": "error: [Errno -2] Name or service not known",
  "redis": "error: invalid username-password pair or user is disabled.",
  "ssh_tunnel": {"active": false, "running": false},
  "mqtt": {"running": false, "connected": false}
}
```

## Kritik Sorunlar

### 1. PostgreSQL Bağlantı Hatası (EN ÖNEMLİ)
**Sorun:** `Name or service not known` - Database hostname çözümlenemiyor.

**Neden:** `DATABASE_URL` environment variable'ında hostname yanlış veya PostgreSQL servisi çalışmıyor.

**Çözüm:**
```bash
# Coolify'da Backend servisinde DATABASE_URL'i kontrol edin:
DATABASE_URL=postgresql+asyncpg://sumatic:POSTGRES_PASSWORD@postgres:5432/sumatic_db
```

**Önemli:** 
- `postgres` kısmı Docker network'teki PostgreSQL servisinin adı (docker-compose.coolify.yml'de tanımlı)
- Şifre `POSTGRES_PASSWORD` ile eşleşmeli
- PostgreSQL servisinin çalıştığından emin olun

### 2. Redis Kimlik Doğrulama Hatası
**Sorun:** `invalid username-password pair or user is disabled`

**Çözüm:**
```bash
# Coolify'da Backend servisinde:
REDIS_URL=redis://:REDIS_PASSWORD@redis:6379/0
```

**Not:** Redis'te username yok, sadece password var. URL formatı: `redis://:password@host:port/db`

### 3. CORS Hatası
**Sorun:** Frontend (3001) backend'e (8001) istek atarken CORS reddediyor.

**Çözüm:**
```bash
# Backend servisinde:
CORS_ORIGINS=http://46.225.231.44:3001,http://46.225.231.44:8001,http://localhost:3000
```

## Adım Adım Çözüm

### Adım 1: Servislerin Durumunu Kontrol Edin

Coolify dashboard'da şu servislerin **çalıştığından** emin olun:
- ✅ postgres
- ✅ redis  
- ✅ backend
- ✅ frontend

### Adım 2: PostgreSQL Environment Variables

**Backend servisinde** şu variable'ları set edin:

```bash
POSTGRES_USER=sumatic
POSTGRES_PASSWORD=<güçlü-şifre>
POSTGRES_DB=sumatic_db
DATABASE_URL=postgresql+asyncpg://sumatic:<güçlü-şifre>@postgres:5432/sumatic_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40
```

**PostgreSQL servisinde** aynı şifreleri kullanın:
```bash
POSTGRES_USER=sumatic
POSTGRES_PASSWORD=<güçlü-şifre>
POSTGRES_DB=sumatic_db
```

### Adım 3: Redis Environment Variables

**Backend servisinde:**
```bash
REDIS_PASSWORD=<redis-şifresi>
REDIS_URL=redis://:<redis-şifresi>@redis:6379/0
```

**Redis servisinde:**
```bash
REDIS_PASSWORD=<redis-şifresi>
```

### Adım 4: CORS Ayarları

**Backend servisinde:**
```bash
CORS_ORIGINS=http://46.225.231.44:3001,http://46.225.231.44:8001,http://localhost:3000
```

### Adım 5: JWT ve Admin Kullanıcı

**Backend servisinde:**
```bash
JWT_SECRET_KEY=<openssl-rand-hex-32-ile-oluşturulmuş-key>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@sumatic.io
ADMIN_PASSWORD=<güçlü-admin-şifresi>
```

### Adım 6: Frontend Environment Variables

**Frontend servisinde:**
```bash
NEXT_PUBLIC_API_URL=http://46.225.231.44:8001
NEXT_PUBLIC_WS_URL=ws://46.225.231.44:8001
```

### Adım 7: Servisleri Restart Edin

1. PostgreSQL'i restart
2. Redis'i restart  
3. Backend'i restart (bu sırada admin kullanıcısı otomatik oluşturulacak)
4. Frontend'i rebuild (NEXT_PUBLIC_* değişkenler build time'da bake edilir)

## Test

### Backend Health Check
```bash
curl http://46.225.231.44:8001/health
```

**Beklenen:** 
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected"
}
```

### Login Test
1. `http://46.225.231.44:3001/login` adresine gidin
2. Username: `admin`
3. Password: `<ADMIN_PASSWORD environment variable'ında ayarladığınız şifre>`

## Güvenlik Önerileri

1. **Güçlü Şifreler Kullanın:**
   - PostgreSQL password: En az 16 karakter, karışık
   - Redis password: En az 16 karakter, karışık
   - Admin password: En az 12 karakter, karışık
   - JWT secret: `openssl rand -hex 32` ile oluşturun

2. **Production'da:**
   - `DEBUG=false` set edin
   - CORS origins'i sadece gerçek domain'inizle sınırlayın
   - HTTPS kullanın (Coolify otomatik SSL sertifikası sağlar)

3. **Şifreleri Saklayın:**
   - Tüm şifreleri güvenli bir yerde (password manager) saklayın
   - `.env` dosyalarını asla git'e commit etmeyin

## Sorun Giderme

### Database hala bağlanamıyor
- PostgreSQL servisinin loglarını kontrol edin
- `postgres` hostname'inin DNS'te çözümlendiğini doğrulayın (container network içinde)
- Port 5432'nin açık olduğunu kontrol edin

### Redis hala kimlik doğrulama yapamıyor
- Redis servisinin loglarını kontrol edin
- REDIS_URL formatının doğru olduğundan emin olun: `redis://:password@host:port/db`
- Redis container'ının `requirepass` ile başlatıldığını doğrulayın

### CORS hala çalışmıyor
- Backend loglarında CORS hatalarını kontrol edin
- Browser developer console'da network sekmesinde response header'larını inceleyin
- `CORS_ORIGINS`'in backend'de doğru set edildiğinden emin olun

### Admin kullanıcısı oluşmamış
- Backend loglarını kontrol edin
- Database bağlantısının çalıştığından emin olun
- Backend'i restart edin (admin otomatik oluşturulur)
- Alternatif: `backend/change_admin_password.py` scriptini çalıştırın
