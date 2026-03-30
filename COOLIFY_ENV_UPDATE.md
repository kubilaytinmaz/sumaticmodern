# Coolify Environment Variables Güncelleme Talimatları

## Login 401 Hatası Çözüldü ✅

Login artık çalışıyor! Backend logları `/auth/me` için 200 OK gösteriyor.

**Sorun:** `ResponseFilterMiddleware` login response'undaki `access_token` ve `refresh_token` alanlarını güvenlik gerekçesiyle `[REDACTED]` ile değiştiriyordu.

**Çözüm:** Auth endpoint'leri filtrelemeden muaf tutuldu (commit `0400a54`).

---

## 🔧 Yapılması Gerekenler

### Backend Environment Variables (ZORUNLU)

Coolify'da **backend service**'in Environment Variables bölümüne gidin ve aşağıdaki değişkeni ekleyin/güncelleyin:

```bash
# CORS - Production origin'leri (localhost'lar kaldırıldı)
CORS_ORIGINS=http://46.225.231.44:3001,http://46.225.231.44:8001
```

**Not:** `CORS_ORIGINS` varsayılan değeri development için localhost'ları içeriyor. Production'da sadece gerçek frontend URL'lerini kullanmalısınız.

### Redeploy

Backend environment variable'ı güncelledikten sonra:
1. Backend service'i **Redeploy** edin
2. Frontend'i **zaten çalışıyor**, redeploy gerekmez

---

## ✅ Test Adımları

1. `http://46.225.231.44:3001` adresine gidin
2. Username: `admin`
3. Password: (generate_coolify_env.py ile oluşturulan şifre)
4. Login butonuna tıklayın
5. Dashboard'a yönlendirilmelisiniz ✅

---

## 📝 Yapılan Değişiklikler Özeti

### Commit `0400a54` - ResponseFilterMiddleware Fix
- Auth endpoint'leri (`/api/v1/auth`) için token filtrelemesi devre dışı bırakıldı
- Login, refresh gibi endpoint'ler artık token'ları doğru döndürüyor

### Commit `8fb4f4f` - CORS & Debug Logging
- CORS_ORIGINS varsayılan değerine frontend URL eklendi (geçici)
- Token validation sürecine detaylı debug logging eklendi
- Artık 401 hatalarının nedeni backend loglarında görünüyor

---

## 🔒 Güvenlik Notları

1. **CORS_ORIGINS:** Production'da sadece gerçek frontend domain'lerini kullanın
2. **JWT_SECRET_KEY:** Production'da güçlü bir random key kullanın (min 32 karakter)
3. **ADMIN_PASSWORD:** Varsayılan şifreyi mutlaka değiştirin
4. **DEBUG=False:** Production'da debug mode kapalı olmalı

---

## 🚀 İleri Adımlar

Login çalışıyor! Artık şunları yapabilirsiniz:

1. Dashboard'u inceleyin
2. Device yönetimi yapın
3. Analytics'leri kontrol edin
4. MQTT log'larını görüntüleyin
5. Kullanıcı ayarlarını düzenleyin

---

## 🐛 Sorun Yaşarsanız

Eğer hala sorun varsa, backend loglarına bakın:

```bash
# Coolify'da backend container loglarını görüntüle
# "Logs" sekmesinde real-time logları görebilirsiniz

# Debug mesajları artık şunları içeriyor:
# - Token validation attempts
# - Token decode success/failure
# - User lookup operations
# - Authentication failures with reasons
```

Token validation hatası varsa, log şöyle görünecek:
```
2026-03-30 08:40:xx.xxx | WARNING  | app.api.deps:get_current_user:xx | Token decode failed: ...
```

---

Son güncelleme: 2026-03-30 11:42 (UTC+3)
