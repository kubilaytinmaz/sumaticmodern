# WebSocket 403 ve Monthly Stats 500 Hata Düzeltme Planı

## 📋 Genel Bakış

Bu planda iki kritik sorunun çözümü ele alınmaktadır:

1. **WebSocket 403 Forbidden Hatası**: Frontend ve backend arasında WebSocket URL path uyuşmazlığı
2. **Monthly Stats 500 Internal Server Error**: SQLite veritabanında PostgreSQL-özgü `func.extract()` kullanımı

---

## 🔍 Sorun 1: WebSocket 403 Forbidden

### Kök Neden

**Frontend URL**: `ws://localhost:8000/ws?token=...`
- Dosya: [`frontend/src/lib/websocket.ts:59`](frontend/src/lib/websocket.ts:59)
- WebSocket client doğrudan `/ws` endpoint'ine bağlanmaya çalışıyor

**Backend Endpoint**: `/api/v1/ws`
- Dosya: [`backend/app/api/v1/websocket.py:19`](backend/app/api/v1/websocket.py:19)
- Router prefix: `/ws`
- Ana app include: `/api/v1` prefix ile ([`backend/app/main.py:282`](backend/app/main.py:282))
- Gerçek endpoint: `/api/v1` + `/ws` = **`/api/v1/ws`**

### Çözüm

Frontend WebSocket client'ın bağlantı URL'ini güncelle:

**Değiştirilecek Satır**: [`frontend/src/lib/websocket.ts:59`](frontend/src/lib/websocket.ts:59)

```typescript
// ❌ ÖNCE (Yanlış)
const wsUrl = this.token
  ? `${this.url}/ws?token=${this.token}`
  : `${this.url}/ws`;

// ✅ SONRA (Doğru)
const wsUrl = this.token
  ? `${this.url}/api/v1/ws?token=${this.token}`
  : `${this.url}/api/v1/ws`;
```

### Beklenen Sonuç

WebSocket bağlantısı başarılı olacak ve terminal loglarında şu mesaj görülecek:
```
INFO: 127.0.0.1:xxxxx - "WebSocket /api/v1/ws?token=..." [ACCEPTED]
[WebSocket] Connected
```

---

## 🔍 Sorun 2: Monthly Stats 500 Internal Server Error

### Kök Neden

**Dosya**: [`backend/app/api/v1/charts.py:1484-1485`](backend/app/api/v1/charts.py:1484)

```python
offline_readings_result = await db.execute(
    select(DeviceReading.timestamp, DeviceReading.status)
    .where(
        (DeviceReading.device_id == device.id) &
        (func.extract('year', DeviceReading.timestamp) == year) &  # ❌ SQLite desteklemiyor
        (func.extract('month', DeviceReading.timestamp) == month)   # ❌ SQLite desteklemiyor
    )
    .order_by(DeviceReading.timestamp.asc())
)
```

**Sorun**: 
- `func.extract()` sadece PostgreSQL'de çalışır
- SQLite bu SQL fonksiyonunu desteklemez
- Geliştirme ortamında SQLite kullanılıyor

**Mevcut Çalışan Örnek**: Aynı dosyada başka endpoint'ler zaten doğru yaklaşımı kullanıyor:
- Terminal loglarında görülen `monthly-breakdown` endpoint başarılı: `CAST(STRFTIME('%Y', ...) AS INTEGER)`

### Çözüm

`func.extract()` kullanımını SQLite uyumlu `CAST(func.strftime())` ile değiştir:

**Değiştirilecek Satırlar**: [`backend/app/api/v1/charts.py:1480-1488`](backend/app/api/v1/charts.py:1480)

```python
# ❌ ÖNCE (PostgreSQL-only)
offline_readings_result = await db.execute(
    select(DeviceReading.timestamp, DeviceReading.status)
    .where(
        (DeviceReading.device_id == device.id) &
        (func.extract('year', DeviceReading.timestamp) == year) &
        (func.extract('month', DeviceReading.timestamp) == month)
    )
    .order_by(DeviceReading.timestamp.asc())
)

# ✅ SONRA (SQLite ve PostgreSQL uyumlu)
offline_readings_result = await db.execute(
    select(DeviceReading.timestamp, DeviceReading.status)
    .where(
        (DeviceReading.device_id == device.id) &
        (func.cast(func.strftime('%Y', DeviceReading.timestamp), Integer) == year) &
        (func.cast(func.strftime('%m', DeviceReading.timestamp), Integer) == month)
    )
    .order_by(DeviceReading.timestamp.asc())
)
```

**Import Gereksinimi**: `Integer` type'ı zaten import edilmiş durumda (satır 13: `from sqlalchemy import select, func, and_`)

### Alternatif Çözümler (Önerilmez)

1. **Timestamp karşılaştırması**: Mevcut kodda zaten kullanılan ancak timezone sorunlarına yol açabilen yaklaşım
2. **Raw SQL**: Platform bağımlılığı yaratır
3. **Python-side filtering**: Performans sorunlarına yol açar

### Beklenen Sonuç

Endpoint başarılı yanıt dönecek ve terminal loglarında:
```
INFO: 127.0.0.1:xxxxx - "GET /api/v1/charts/devices/monthly-stats?year=2026&month=3 HTTP/1.1" 200 OK
```

---

## 📝 İmplementasyon Adımları

### Adım 1: Frontend WebSocket URL Düzeltmesi

1. [`frontend/src/lib/websocket.ts`](frontend/src/lib/websocket.ts) dosyasını aç
2. Satır 59'daki WebSocket URL'ini güncelle
3. `/ws` yerine `/api/v1/ws` kullan

### Adım 2: Backend Monthly Stats SQLite Uyumluluğu

1. [`backend/app/api/v1/charts.py`](backend/app/api/v1/charts.py) dosyasını aç
2. Satır 1484-1485'teki `func.extract()` kullanımını kaldır
3. `func.cast(func.strftime(...), Integer)` ile değiştir

### Adım 3: Test

1. **WebSocket Testi**:
   - Frontend uygulamasını yenile
   - Browser console'da `[WebSocket] Connected` mesajını kontrol et
   - Backend terminal'de 403 yerine başarılı bağlantı logunu gör

2. **Monthly Stats Testi**:
   - Dashboard'da monthly stats widget'ını yenile
   - 500 hatası yerine veri geldiğini kontrol et
   - Backend terminal'de 200 OK görmeli

---

## 🎯 Etki Analizi

### WebSocket Düzeltmesi
- **Etkilenen Dosyalar**: 1 dosya (frontend)
- **Risk Seviyesi**: Düşük
- **Geri Dönüş**: Kolayca geri alınabilir
- **Yan Etkiler**: Yok

### Monthly Stats Düzeltmesi
- **Etkilenen Dosyalar**: 1 dosya (backend)
- **Risk Seviyesi**: Çok düşük (sadece sorgu değişikliği)
- **Geri Dönüş**: Kolayca geri alınabilir
- **PostgreSQL Uyumluluğu**: `STRFTIME()` her iki veritabanında da çalışır
- **Yan Etkiler**: Yok

---

## ✅ Doğrulama Kriterleri

### WebSocket
- [ ] Frontend terminal loglarında `[WebSocket] Connected` mesajı
- [ ] Backend terminal'de 403 hatası yok
- [ ] WebSocket status endpoint `/api/v1/ws/status` aktif bağlantıları gösteriyor
- [ ] Gerçek zamanlı veri güncellemeleri çalışıyor

### Monthly Stats
- [ ] `/api/v1/charts/devices/monthly-stats?year=2026&month=3` 200 OK döndürüyor
- [ ] Response body'de doğru veriler var
- [ ] Backend terminal'de 500 hatası yok
- [ ] Dashboard widget'ı verileri gösteriyor

---

## 📚 Teknik Notlar

### WebSocket URL Pattern
- FastAPI router prefix'leri birleşerek nihai endpoint'i oluşturur
- Ana app: `/api/v1` + Router: `/ws` = `/api/v1/ws`
- WebSocket bağlantıları HTTP upgrade kullanır, normal HTTP endpoint'leriyle aynı routing kurallarına tabi

### SQLite vs PostgreSQL
- `func.extract()` PostgreSQL-specific SQL fonksiyonu
- `STRFTIME()` SQLite'ın tarih/saat işleme fonksiyonu
- SQLAlchemy'nin `func.strftime()` her iki veritabanında da çalışır
- `CAST(..., Integer)` tip dönüşümü için gerekli

### Veritabanı Uyumluluğu
Aynı dosyada zaten kullanılan başarılı pattern'ler:
- `monthly-breakdown` endpoint (satır 1760+)
- `weekly-stats` endpoint (satır 1547+)
- Her ikisi de `CAST(STRFTIME(...), INTEGER)` kullanıyor

---

## 🔄 Deployment Notları

### Geliştirme (SQLite)
- Her iki düzeltme de doğrudan uygulanabilir
- Veritabanı migration'ı gerekmez
- Yeniden başlatma: Frontend için npm, Backend için uvicorn reload

### Production (PostgreSQL)
- `STRFTIME()` PostgreSQL'de de destekleniyor
- Kod değişikliği dışında ek adım gerekmez
- Zero-downtime deployment yapılabilir

---

## 📞 İlgili Dosyalar

1. [`frontend/src/lib/websocket.ts`](frontend/src/lib/websocket.ts) - WebSocket client
2. [`backend/app/api/v1/websocket.py`](backend/app/api/v1/websocket.py) - WebSocket endpoint
3. [`backend/app/main.py`](backend/app/main.py) - API router configuration
4. [`backend/app/api/v1/charts.py`](backend/app/api/v1/charts.py) - Chart data endpoints

---

## ⚠️ Dikkat Edilmesi Gerekenler

1. WebSocket URL değişikliğinden sonra aktif bağlantılar kopar - kullanıcılar sayfayı yenilemelidir
2. Backend değişikliği hot-reload ile otomatik uygulanır
3. Her iki değişiklik de geriye dönük uyumludur
4. Production'da aynı fix'ler uygulanabilir

---

**Plan Tarihi**: 2026-03-31  
**Tahmini Süre**: 10-15 dakika  
**Zorluk**: Düşük  
**Öncelik**: Yüksek
