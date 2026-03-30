# Coolify 404 Hatası Çözümü

## Sorun Analizi

Frontend login sayfasında 404 hatası alınıyor:
```
POST http://46.225.231.44:8000/api/v1/auth/login 404 (Not Found)
```

**Neden?**
- Backend artık port **8001**'de çalışıyor (port 8000 başka proje tarafından kullanılıyor)
- Frontend hala eski port **8000**'e istek atıyor
- `NEXT_PUBLIC_API_URL` environment variable'ı güncel değil

## Çözüm Adımları

### 1. Coolify Dashboard'a Giriş

1. Coolify'a giriş yapın
2. **Sumatic Modern IoT** projenizi bulun
3. **Frontend** servisini seçin

### 2. Environment Variables'ları Güncelle

Frontend servisinde aşağıdaki environment variable'ları düzenleyin:

```bash
# Eski değer (yanlış):
NEXT_PUBLIC_API_URL=http://46.225.231.44:8000

# Yeni değer (doğru):
NEXT_PUBLIC_API_URL=http://46.225.231.44:8001
```

```bash
# Eski değer (yanlış):
NEXT_PUBLIC_WS_URL=ws://46.225.231.44:8000

# Yeni değer (doğru):
NEXT_PUBLIC_WS_URL=ws://46.225.231.44:8001
```

### 3. Backend Environment Variables (Opsiyonel Kontrol)

Backend servisinde CORS ayarlarını kontrol edin:

```bash
# Frontend'in yeni portunu da CORS'a ekleyin:
CORS_ORIGINS=http://46.225.231.44:3001,http://localhost:3000,http://127.0.0.1:3000
```

### 4. Servisleri Yeniden Başlat

1. **Frontend** servisini yeniden deploy edin (Redeploy butonu)
2. **Backend** servisini de yeniden başlatın (varsa sorun olması ihtimaline karşı)

### 5. Test

Deployment tamamlandıktan sonra:

1. Tarayıcı cache'ini temizleyin (Ctrl+Shift+Delete)
2. Siteyi yeniden açın: `http://46.225.231.44:3001`
3. Login formunu test edin:
   - **Username:** admin
   - **Password:** (ADMIN_PASSWORD environment variable'ında belirlediğiniz şifre)

## Port Eşleştirme Tablosu

| Servis | Container Port | Host Port | URL |
|--------|---------------|-----------|-----|
| Backend | 8000 | 8001 | http://46.225.231.44:8001 |
| Frontend | 3000 | 3001 | http://46.225.231.44:3001 |
| PostgreSQL | 5432 | - (internal) | - |
| Redis | 6379 | - (internal) | - |

## Alternatif: Domain ile Erişim

Eğer bir domain adınız varsa (örn: `sumatic.example.com`), Coolify'da:

1. Domain ayarlarını yapın
2. Environment variable'ları domain ile güncelleyin:
   ```bash
   NEXT_PUBLIC_API_URL=https://api.sumatic.example.com
   NEXT_PUBLIC_WS_URL=wss://api.sumatic.example.com
   ```

## Güvenlik Notu

- Production'da mutlaka **HTTPS** kullanın (Coolify SSL sertifikası otomatik sağlar)
- `ADMIN_PASSWORD` environment variable'ını güçlü bir şifre ile değiştirin
- `JWT_SECRET_KEY` environment variable'ını kriptografik olarak güçlü bir key ile değiştirin

## Sorun Devam Ederse

1. Coolify loglarını kontrol edin (Logs sekmesi)
2. Backend healthcheck'i test edin: `http://46.225.231.44:8001/health`
3. Frontend build loglarında hata var mı kontrol edin
4. Browser developer console'da network sekmesini açıp request URL'ini doğrulayın

## Admin Şifresini Değiştirmek

Eğer admin şifresini değiştirmek isterseniz:

1. Backend servisine SSH ile bağlanın veya Coolify terminal'ini açın
2. Şu scripti çalıştırın:

```bash
cd /app
python -c "
import asyncio
from app.database import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def change_password():
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.username == 'admin'))
        admin = result.scalar_one_or_none()
        if admin:
            admin.password_hash = get_password_hash('YeniSifreniz123!')
            await session.commit()
            print('Admin password updated successfully!')

asyncio.run(change_password())
"
```

Ya da `ADMIN_PASSWORD` environment variable'ını değiştirip backend'i yeniden başlatın (ilk başlatmada admin kullanıcısı varsa güncellenmez, sadece yoksa oluşturulur).
