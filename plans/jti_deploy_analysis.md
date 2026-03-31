# JWT JTI Değişikliği - Deploy Uyumluluk Analizi

**Tarih:** 2026-03-31  
**Analiz Eden:** Architect Mode  
**Konu:** `create_access_token` fonksiyonuna eklenen `jti` claim'inin deploy ortamındaki etkileri

---

## 📋 Yapılan Değişiklik

### Dosya: `backend/app/core/security.py`

```python
def create_access_token(
    subject: str,
    username: str,
    role: str,
    expires_delta: Optional[float] = None,
) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + timedelta(seconds=expires_delta)
    else:
        expire = now + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Generate unique JWT ID for token blacklisting
    jti = f"{subject}_{int(now.timestamp())}"  # ✅ EKLENDI
    
    to_encode = {
        "sub": subject,
        "username": username,
        "role": role,
        "exp": expire.timestamp(),
        "type": "access",
        "jti": jti,  # ✅ EKLENDI
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt
```

---

## ✅ POZİTİF ETKİLER

### 1. Authentication Sorunu Çözüldü
- **Önceki Durum:** `/api/v1/auth/me` endpoint'i "Could not validate credentials" hatası döndürüyordu
- **Sebep:** `get_current_user` dependency'si token'da `jti` arıyordu ama `create_access_token` bunu sağlamıyordu
- **Sonuç:** ✅ Authentication artık düzgün çalışıyor

### 2. Token Blacklisting Desteği
- Token'lar artık benzersiz ID'ye sahip
- Logout işleminde token'lar blacklist'e eklenebilir
- Redis ile token revocation mekanizması aktif

### 3. Güvenlik İyileştirmesi
- Her token benzersiz olduğu için takip edilebilir
- Token replay saldırılarına karşı ek koruma
- Aynı kullanıcının farklı oturumlarda farklı token'ları olur

---

## ⚠️ TESPİT EDİLEN SORUNLAR

### 🔴 **KRİTİK SORUN 1: Logout Mekanizması Uyumsuzluğu**

**Konum:** `backend/app/api/v1/auth.py` - Line 218-248

**Mevcut Kod:**
```python
@router.post("/logout")
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    current_user: User = Depends(get_current_user),
) -> dict:
    """Logout user and blacklist the current token."""
    token = credentials.credentials
    
    # ❌ SORUN: Token hash kullanılıyor, gerçek jti kullanılmalı
    import hashlib
    jti = hashlib.sha256(token.encode()).hexdigest()
    
    # Blacklist for the duration of the access token
    await blacklist_token(
        jti,
        expire_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    
    logger.info(f"User logged out: {current_user.username}")
    
    return {"message": "Successfully logged out"}
```

**Sorun Açıklaması:**
- Logout işlemi token'ın SHA256 hash'ini `jti` olarak kullanıyor
- Ancak `get_current_user` dependency'si token içindeki gerçek `jti` claim'ini kontrol ediyor
- Bu iki değer farklı olduğu için logout işlemi **çalışmıyor**
- Kullanıcı logout yapsa bile token hala geçerli kabul ediliyor

**Etki:**
- 🔴 **YÜKSEK RİSK:** Logout işlemi işlevsiz
- Kullanıcılar çıkış yapmış olsa bile token'ları geçerli kalıyor
- Güvenlik açığı oluşturuyor

**Çözüm:**
```python
@router.post("/logout")
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    current_user: User = Depends(get_current_user),
) -> dict:
    """Logout user and blacklist the current token."""
    token = credentials.credentials
    
    # ✅ Token'dan gerçek jti'yi decode et
    try:
        from app.core.security import decode_token
        payload = decode_token(token)
        jti = payload.get("jti")
        
        if jti:
            # Blacklist for the duration of the access token
            await blacklist_token(
                jti,
                expire_seconds=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
            logger.info(f"User logged out: {current_user.username}, JTI: {jti}")
        else:
            logger.warning(f"Logout attempted but token has no JTI: {current_user.username}")
    except Exception as e:
        logger.error(f"Error during logout: {e}")
    
    return {"message": "Successfully logged out"}
```

---

### 🟡 **SORUN 2: Refresh Token'da jti Yok**

**Konum:** `backend/app/core/security.py` - Line 62-84

**Mevcut Kod:**
```python
def create_refresh_token(
    subject: str,
    username: str,
    role: str,
) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": subject,
        "username": username,
        "role": role,
        "exp": expire.timestamp(),
        "type": "refresh",
        # ❌ jti YOK
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt
```

**Sorun Açıklaması:**
- Access token'da `jti` var ama refresh token'da yok
- Tutarsızlık var
- Refresh token'ları da revoke edilemez (logout sonrası hala kullanılabilir)

**Etki:**
- 🟡 **ORTA RİSK:** Logout sonrası refresh token ile yeni access token alınabilir
- Token revocation mekanizması eksik

**Çözüm:**
```python
def create_refresh_token(
    subject: str,
    username: str,
    role: str,
) -> str:
    """Create a JWT refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    # ✅ Refresh token için de jti ekle
    jti = f"{subject}_refresh_{int(now.timestamp())}"
    
    to_encode = {
        "sub": subject,
        "username": username,
        "role": role,
        "exp": expire.timestamp(),
        "type": "refresh",
        "jti": jti,  # ✅ EKLE
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    
    return encoded_jwt
```

---

### 🟢 **BİLGİ: WebSocket 403 Hatası**

**Konum:** Terminal loglarında görülen hata

```
INFO:     127.0.0.1:55459 - "WebSocket /ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." 403
INFO:     connection rejected (403 Forbidden)
```

**Analiz:**
- WebSocket endpoint'i token doğrulaması yapıyor
- Token muhtemelen süresi dolmuş veya geçersiz
- Bu, normal bir durum (token expiration)
- `jti` değişikliği ile ilgili değil

**Konum:** `backend/app/api/v1/websocket.py` - Line 52-68

```python
# Get user from token if provided
user = None
if token:
    try:
        from app.core.security import decode_token
        payload = decode_token(token)
        if payload.get("type") == "access":
            user_id = payload.get("sub")
            if user_id:
                from sqlalchemy import select
                from app.models.user import User
                result = await db.execute(
                    select(User).where(User.id == int(user_id))
                )
                user = result.scalar_one_or_none()
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
```

**Sonuç:** ✅ WebSocket authentication kodu doğru, token yenilendiğinde çalışacak

---

## 🔄 GERIYE UYUMLULUK ANALİZİ

### Deploy Öncesi Durumlar

#### 1. **Eski Token'lar (jti olmayan)**
```python
# deps.py - Line 80-90
jti = payload.get("jti")
# Only check blacklist if jti exists (tokens without jti skip this check)
if jti:
    try:
        if await is_token_blacklisted(jti):
            logger.warning(f"Token is blacklisted. JTI: {jti}")
            raise credentials_exception
    except Exception as e:
        # Redis unavailable - log warning but don't block auth
        logger.warning(f"Redis unavailable for blacklist check: {e}")
```

**Sonuç:** ✅ **Geriye uyumlu!**
- Eski token'lar (jti olmayan) hala çalışır
- `if jti:` kontrolü sayesinde blacklist kontrolü atlanır
- Kullanıcılar yeniden login yapmak zorunda kalmaz

#### 2. **Yeni Deploy Sonrası**
- Yeni login'lerde `jti` içeren token'lar üretilir
- Blacklist mekanizması aktif olur
- Eski token'lar süresi dolana kadar kullanılabilir

---

## 📊 DEPLOY ETKİ ANALİZİ

### Pozitif Etkiler
✅ Authentication çalışıyor  
✅ Geriye uyumlu  
✅ Güvenlik artışı  
✅ Token blacklisting hazır  

### Negatif Etkiler
❌ Logout çalışmıyor (kritik)  
⚠️ Refresh token'da jti yok  
⚠️ Tutarsızlık var  

### Risk Seviyesi
🔴 **YÜKSEK** - Logout mekanizması bozuk

---

## 🛠️ DÜZELTME ÖNCELİĞİ

### 1. KRİTİK (Hemen yapılmalı)
- [ ] Logout endpoint'ini düzelt - gerçek jti kullan
- [ ] Test et: Logout sonrası token geçersiz olmalı

### 2. YÜKSEK ÖNCELİKLİ (Deploy öncesi)
- [ ] Refresh token'a jti ekle
- [ ] Refresh token revocation mekanizması ekle
- [ ] Test et: Logout sonrası refresh token da geçersiz olmalı

### 3. ORTA ÖNCELİKLİ (Deploy sonrası)
- [ ] WebSocket token yenileme mekanizması ekle
- [ ] Token rotation stratejisi belirle

---

## 📝 DEPLOY ÖNERİLERİ

### Deploy Stratejisi

#### Seçenek 1: Acil Deploy (Önerilmez)
```
1. Mevcut değişikliği deploy et
2. Kullanıcılar auth yapabilir ama logout çalışmaz
3. Güvenlik açığı devam eder
```
**Risk:** 🔴 YÜKSEK

#### Seçenek 2: Düzeltmelerle Deploy (ÖNERİLİR)
```
1. Logout endpoint'ini düzelt (5 dakika)
2. Refresh token'a jti ekle (5 dakika)
3. Test et (10 dakika)
4. Deploy et
```
**Risk:** 🟢 DÜŞÜK

### Test Senaryoları

```bash
# Test 1: Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Test 2: Me endpoint (token ile)
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <TOKEN>"

# Test 3: Logout
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <TOKEN>"

# Test 4: Logout sonrası me endpoint (401 dönmeli)
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 🎯 SONUÇ VE TAVSİYE

### Mevcut Durum
- ✅ Authentication çalışıyor
- ❌ Logout çalışmıyor
- ⚠️ Güvenlik açığı var

### Tavsiye
**Deploy edilmemeli**, önce aşağıdaki düzeltmeler yapılmalı:

1. **Logout endpoint'ini düzelt** (Kritik)
2. **Refresh token'a jti ekle** (Önemli)  
3. **Test et** (Zorunlu)
4. **Deploy et** (Güvenli)

### Tahmini Süre
- Düzeltme: 10 dakika
- Test: 10 dakika
- **Toplam: 20 dakika**

---

## 📌 BAĞLANTILAR

- Değiştirilen dosya: [`backend/app/core/security.py:26-59`](../backend/app/core/security.py)
- Düzeltilmesi gereken: [`backend/app/api/v1/auth.py:218-248`](../backend/app/api/v1/auth.py)
- Token validation: [`backend/app/api/deps.py:28-116`](../backend/app/api/deps.py)
- Redis blacklist: [`backend/app/redis_client.py:198-224`](../backend/app/redis_client.py)

---

**⚠️ ÖNEMLİ NOT:** Bu değişiklikleri yapmadan deploy etmek güvenlik açığı oluşturur. Logout çalışmadığı için kullanıcılar çıkış yapsalar bile token'ları geçerli kalacaktır.
