# CORS Hatası Çözümü - "Failed to fetch"

## Sorun
Frontend `http://46.225.231.44:3001` üzerinden backend `http://46.225.231.44:8001`'e istek atarken CORS hatası alıyorsunuz.

```
Origin: http://46.225.231.44:3001
Access-Control-Request-Method: POST
```

Backend bu origin'i izin verilen listede bulamadığı için OPTIONS preflight request'i reddediyor.

## Çözüm

### Coolify'da Backend Servisini Güncelleyin:

1. **Backend** servisine gidin
2. **Environment Variables** sekmesini açın
3. `CORS_ORIGINS` variable'ını bulun ve şu şekilde güncelleyin:

```bash
CORS_ORIGINS=http://46.225.231.44:3001,http://46.225.231.44:8001,http://localhost:3000
```

### Alternatif (Daha Geniş):
```bash
CORS_ORIGINS=http://46.225.231.44:3001,http://46.225.231.44:3000,http://46.225.231.44:8001,http://46.225.231.44:8000,http://localhost:3000,http://localhost:8000
```

4. **Backend servisini restart edin** (Restart butonu)

## Test

Değişiklikten sonra tekrar login deneyin:
- URL: `http://46.225.231.44:3001/login`
- Username: `admin`
- Password: `SumaticAdmin2024!SecurePass@66xA`

## Alternatif Test (cURL ile)

Backend'in çalıştığını doğrulamak için healthcheck:
```bash
curl http://46.225.231.44:8001/health
```

CORS'u test etmek için OPTIONS request:
```bash
curl -X OPTIONS "http://46.225.231.44:8001/api/v1/auth/login" \
  -H "Origin: http://46.225.231.44:3001" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -v
```

Başarılı olursa şu header'ları görmeli siniz:
```
< Access-Control-Allow-Origin: http://46.225.231.44:3001
< Access-Control-Allow-Methods: POST
< Access-Control-Allow-Headers: content-type
```

## Güvenlik Notu

Production'da sadece gerçekten kullandığınız origin'leri ekleyin. `*` (wildcard) kullanmayın çünkü güvenlik riski oluşturur.
