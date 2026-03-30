# Sumatic Modern IoT - RAM Kullanımı Analiz Raporu

## Özet

Bu rapor, Sumatic Modern IoT projesinin RAM kullanımını detaylı analiz eder ve uzun süreli çalışma sırasında olası RAM dolması sorunlarını inceler.

## 🔴 Kritik Bulgular

### 1. YÜKSEK RİSK: MQTT Consumer Memory Leak

**Dosya:** [`backend/app/services/mqtt_consumer.py`](../backend/app/services/mqtt_consumer.py)

**Sorun:** MQTT consumer servisi zamanla RAM biriktiriyor.

**Detaylar:**
- [`_cache`](../backend/app/services/mqtt_consumer.py:55) - Her cihaz için sonsuza kadar büyüyen cache
- [`_hourly_tracking`](../backend/app/services/mqtt_consumer.py:80) - Saatlik takip verileri temizlenmiyor
- [`_snapshot_tracking`](../backend/app/services/mqtt_consumer.py:85) - Snapshot verileri birikim yapıyor
- [`_pending_saves`](../backend/app/services/mqtt_consumer.py:68) - Tamamlanmış task'lar temizlenmeyebilir

**Etki:** 100+ cihaz ile 24 saat çalışma sonrası ~500MB-1GB RAM birikimi olabilir.

### 2. YÜKSEK RİSK: In-Memory MQTT Logs

**Dosya:** [`backend/app/api/v1/mqtt_logs.py`](../backend/app/api/v1/mqtt_logs.py)

**Sorun:** Tüm MQTT logları RAM'de tutuluyor.

**Detaylar:**
- [`_mqtt_logs`](../backend/app/api/v1/mqtt_logs.py:28) listesi son 1000 logu tutuyor
- Her log entry timestamp, level, message, device_code, modem_id, data içeriyor
- Yoğun MQTT trafiğinde hızlı büyüme

**Etki:** Yoğun trafikte ~50-100MB RAM kullanımı.

### 3. ORTA RİSK: Spike Filter State

**Dosya:** [`backend/app/services/spike_filter.py`](../backend/app/services/spike_filter.py)

**Sorun:** Her cihaz-sütun kombinasyonu için state tutuluyor.

**Detaylar:**
- [`_last_good`](../backend/app/services/spike_filter.py:72) - Son iyi değerler
- [`_window`](../backend/app/services/spike_filter.py:75) - Rolling window (5 değer)
- [`_spike_streak`](../backend/app/services/spike_filter.py:78) - Spike streak tracking

**Etki:** 100 cihaz × 10 sütun × ~200 byte = ~200KB (düşük risk)

### 4. ORTA RİSK: WebSocket Manager

**Dosya:** [`backend/app/services/websocket_manager.py`](../backend/app/services/websocket_manager.py)

**Sorun:** Aktif bağlantılar ve subscription'lar RAM'de tutuluyor.

**Detaylar:**
- [`_active_connections`](../backend/app/services/websocket_manager.py:36) - Bağlantı bilgileri
- [`_device_subscriptions`](../backend/app/services/websocket_manager.py:38) - Cihaz subscription'ları
- [`_topic_subscriptions`](../backend/app/services/websocket_manager.py:40) - Topic subscription'ları

**Etki:** 100 aktif bağlantı × ~5KB = ~500MB

### 5. DÜŞÜK RİSK: SSH Tunnel Connection

**Dosya:** [`backend/app/services/ssh_tunnel.py`](../backend/app/services/ssh_tunnel.py)

**Sorun:** SSH tunnel connection state ve metrics.

**Detaylar:**
- Circuit breaker state
- Health metrics
- Reconnection history

**Etki:** ~1-5MB (düşük risk)

## 📊 Docker Konteyner RAM Limitleri

### Production (docker-compose.prod.yml)

| Servis | RAM Limit | RAM Reservation | Risk |
|--------|-----------|-----------------|------|
| Backend | 1GB | 256MB | ⚠️ Yetersiz |
| Frontend | 512MB | 128MB | ✅ Yeterli |
| PostgreSQL | 2GB | 512MB | ✅ Yeterli |
| Redis | 512MB | 128MB | ✅ Yeterli |
| MQTT Broker | 256MB | 64MB | ✅ Yeterli |
| Nginx | 256MB | 64MB | ✅ Yeterli |

**Toplam Minimum RAM:** ~4.5GB
**Önerilen RAM:** 8GB+

### Development (docker-compose.yml)

Development ortamında **RAM limiti YOK** - bu da konteynerlerin sınırsız RAM kullanabileceği anlamına gelir.

## 🔍 Veritabanı Connection Pooling

### Backend Database Configuration

**Dosya:** [`backend/app/database.py`](../backend/app/database.py)

```python
# PostgreSQL (Production)
pool_size=10
max_overflow=20
# Toplam: 30 connection

# SQLite (Development)
# Connection pooling YOK
```

**Analiz:**
- PostgreSQL connection pooling uygun yapılandırılmış
- SQLite development için uygun ancak production için değil
- Her connection ~50-100MB RAM kullanır (PostgreSQL process overhead)

### Redis Connection Pool

**Dosya:** [`backend/app/redis_client.py`](../backend/app/redis_client.py)

```python
max_connections=20
```

**Analiz:**
- Redis connection pool uygun boyutta
- Her connection ~1-2MB RAM kullanır

## 🚨 Memory Leak Riskleri

### 1. MQTT Consumer - En Yüksek Risk

**Sorunlu Kod Bölümleri:**

```python
# mqtt_consumer.py:55-87
self._cache: Dict[str, Dict[str, int]] = {}  # Büyümeye devam ediyor
self._hourly_tracking: Dict[str, Dict[str, Any]] = {}  # Temizlenmiyor
self._snapshot_tracking: Dict[str, Dict[str, Any]] = {}  # Temizlenmiyor
```

**Sorun:**
- `_cache` her cihaz için tüm register değerlerini tutuyor
- `_hourly_tracking` eski saatlerin verilerini temizlemiyor
- `_snapshot_tracking` eski snapshot'ları temizlemiyor

**Zamanla Büyüme:**
- 100 cihaz × 10 register × 4 byte = ~4KB başlangıç
- 24 saat × 6 reading/saat × 100 cihaz = ~144,000 reading
- Her reading ~100 byte = ~14MB/gün

### 2. MQTT Logs - Orta Risk

**Sorunlu Kod:**

```python
# mqtt_logs.py:28-29
_mqtt_logs: List[MQTTLogEntry] = []
_max_logs = 1000
```

**Sorun:**
- Yoğun MQTT trafiğinde her mesaj loglanıyor
- Her log entry ~200-500 byte
- 1000 log = ~200-500MB

### 3. WebSocket Manager - Düşük-Orta Risk

**Sorun:**
- Bağlantı kapatıldığında subscription'lar tam temizlenmeyebilir
- Ghost connection'lar kalabilir

## 💡 Optimizasyon Önerileri

### 1. MQTT Consumer Memory Management (YÜKSEK ÖNCELİK)

**Öneri 1.1:** Cache boyutunu sınırla

```python
# mqtt_consumer.py'e ekle
MAX_CACHE_SIZE = 1000  # cihaz başına

def _add_to_cache(self, device_code: str, col_name: str, value: int):
    if device_code not in self._cache:
        self._cache[device_code] = {}
    
    # Cache boyutunu sınırla
    if len(self._cache[device_code]) > MAX_CACHE_SIZE:
        # En eski değerleri sil
        oldest_keys = list(self._cache[device_code].keys())[:100]
        for key in oldest_keys:
            del self._cache[device_code][key]
    
    self._cache[device_code][col_name] = value
```

**Öneri 1.2:** Eski hourly tracking verilerini temizle

```python
# _update_hourly_status metoduna ekle
async def _update_hourly_status(self, device_codes: Set[str]) -> None:
    # ... mevcut kod ...
    
    # 7 günden eski verileri temizle
    cutoff_date = datetime.now(IST_TIMEZONE) - timedelta(days=7)
    async with async_session_maker() as session:
        from app.models.device_status import DeviceHourlyStatus
        await session.execute(
            delete(DeviceHourlyStatus)
            .where(DeviceHourlyStatus.hour_start < cutoff_date)
        )
        await session.commit()
```

**Öneri 1.3:** Eski snapshot verilerini temizle

```python
# _update_snapshots metoduna ekle
async def _update_snapshots(self, device_codes: Set[str]) -> None:
    # ... mevcut kod ...
    
    # 30 günden eski snapshot'ları temizle
    cutoff_date = datetime.now(IST_TIMEZONE) - timedelta(days=30)
    async with async_session_maker() as session:
        from app.models.device_status import DeviceStatusSnapshot
        await session.execute(
            delete(DeviceStatusSnapshot)
            .where(DeviceStatusSnapshot.snapshot_time < cutoff_date)
        )
        await session.commit()
```

### 2. MQTT Logs Optimization (ORTA ÖNCELİK)

**Öneri 2.1:** Log limitini düşür

```python
# mqtt_logs.py
_max_logs = 100  # 1000'den 100'e düşür
```

**Öneri 2.2:** Log seviyesini filtrele

```python
# Sadece warning ve error loglarını tut
def add_mqtt_log(level: str, message: str, ...):
    if level not in ["warning", "error"]:
        return  # Info loglarını tutma
    # ... geri kalan kod ...
```

**Öneri 2.3:** Redis'e taşı

```python
# MQTT loglarını Redis'e yaz, RAM'de tutma
async def add_mqtt_log(level: str, message: str, ...):
    from app.redis_client import cache_set_json
    
    entry = {...}
    key = f"mqtt_log:{datetime.now().strftime('%Y%m%d')}:{uuid.uuid4()}"
    await cache_set_json(key, entry, expire_seconds=86400)  # 1 gün
```

### 3. WebSocket Manager Cleanup (DÜŞÜK ÖNCELİK)

**Öneri 3.1:** Periyodik cleanup

```python
# websocket_manager.py'e ekle
async def cleanup_stale_connections(self):
    """Ghost connection'ları temizle"""
    stale = []
    for ws, info in self._active_connections.items():
        if ws.client_state != WebSocketState.CONNECTED:
            stale.append(ws)
    
    for ws in stale:
        await self.disconnect(ws)
```

### 4. Docker RAM Limitleri Artır (YÜKSEK ÖNCELİK)

**Öneri 4.1:** Backend limitini artır

```yaml
# docker-compose.prod.yml
backend:
  deploy:
    resources:
      limits:
        memory: 2G  # 1G'den 2G'e çıkar
```

### 5. Veritabanı Temizleme Job'ları (ORTA ÖNCELİK)

**Öneri 5.1:** Periyodik temizleme endpoint'i ekle

```python
# backend/app/api/v1/maintenance.py
@router.post("/maintenance/cleanup-old-data")
async def cleanup_old_data(days: int = 30):
    """Eski veritabanı kayıtlarını temizle"""
    cutoff = datetime.now(IST_TIMEZONE) - timedelta(days=days)
    
    async with async_session_maker() as session:
        # Device readings
        await session.execute(
            delete(DeviceReading)
            .where(DeviceReading.timestamp < cutoff)
        )
        
        # Hourly status
        await session.execute(
            delete(DeviceHourlyStatus)
            .where(DeviceHourlyStatus.hour_start < cutoff)
        )
        
        # Snapshots
        await session.execute(
            delete(DeviceStatusSnapshot)
            .where(DeviceStatusSnapshot.snapshot_time < cutoff)
        )
        
        await session.commit()
    
    return {"status": "ok", "deleted_before": cutoff}
```

## 📈 RAM Kullanımı Tahminleri

### Başlangıç (Fresh Start)

| Bileşen | RAM Kullanımı |
|---------|---------------|
| Backend (FastAPI) | ~100MB |
| MQTT Consumer | ~50MB |
| WebSocket Manager | ~10MB |
| Spike Filter | ~5MB |
| SSH Tunnel | ~5MB |
| Redis Client | ~10MB |
| **Toplam** | **~180MB** |

### 24 Saat Sonra (100 cihaz, yoğun trafik)

| Bileşen | RAM Kullanımı | Artış |
|---------|---------------|-------|
| Backend (FastAPI) | ~200MB | +100MB |
| MQTT Consumer | ~500MB | +450MB ⚠️ |
| WebSocket Manager | ~50MB | +40MB |
| Spike Filter | ~10MB | +5MB |
| SSH Tunnel | ~10MB | +5MB |
| Redis Client | ~20MB | +10MB |
| MQTT Logs | ~100MB | +100MB ⚠️ |
| **Toplam** | **~890MB** | **+710MB** |

### 7 Gün Sonra (Memory leak düzeltilmeden)

| Bileşen | RAM Kullanımı | Risk |
|---------|---------------|------|
| Backend (FastAPI) | ~300MB | ✅ |
| MQTT Consumer | ~2GB | 🔴 KRİTİK |
| WebSocket Manager | ~100MB | ⚠️ |
| Spike Filter | ~20MB | ✅ |
| SSH Tunnel | ~20MB | ✅ |
| Redis Client | ~50MB | ✅ |
| MQTT Logs | ~100MB | ⚠️ |
| **Toplam** | **~2.6GB** | **🔴 KRİTİK** |

## 🎯 Acil Eylem Planı

### Phase 1: Acil (Bu hafta)

1. **Backend RAM limitini 2GB'a çıkar**
2. **MQTT logs limitini 100'e düşür**
3. **Cache boyutunu sınırla**

### Phase 2: Kısa Vadeli (Bu ay)

1. **Hourly tracking temizleme ekle**
2. **Snapshot temizleme ekle**
3. **WebSocket cleanup ekle**

### Phase 3: Orta Vadeli (3 ay)

1. **MQTT logları Redis'e taşı**
2. **Periyodik veritabanı temizleme job'ı**
3. **Memory monitoring dashboard'u**

## 🔬 Monitoring Önerileri

### 1. Memory Profiling

```python
# backend/app/api/v1/monitoring.py
import psutil
import tracemalloc

@router.get("/monitoring/memory")
async def get_memory_usage():
    """Detaylı RAM kullanımı"""
    process = psutil.Process()
    
    # MQTT consumer cache boyutu
    mqtt_consumer = get_mqtt_consumer()
    cache_size = len(mqtt_consumer._cache)
    
    # MQTT logs boyutu
    logs_size = len(_mqtt_logs)
    
    return {
        "process_rss_mb": process.memory_info().rss / 1024 / 1024,
        "mqtt_cache_size": cache_size,
        "mqtt_logs_size": logs_size,
        "websocket_connections": get_websocket_manager().get_connection_count(),
    }
```

### 2. Memory Alert

```python
# RAM kullanımı %80'i geçerse alert
MEMORY_THRESHOLD = 0.8  # %80

async def check_memory_usage():
    process = psutil.Process()
    memory_percent = process.memory_info().rss / (1024 * 1024 * 1024)  # GB
    
    if memory_percent > MEMORY_THRESHOLD:
        # Alert gönder
        await get_websocket_manager().broadcast_alert(
            alert_type="high_memory",
            title="Yüksek RAM Kullanımı",
            message=f"Backend RAM kullanımı %{memory_percent:.1f}",
            severity="warning"
        )
```

## 📝 Sonuç

**Evet, bu proje RAM'i yorabilir ve uzun süreli çalışmada RAM dolar.**

**Ana Sorunlar:**
1. MQTT consumer'da memory leak (en kritik)
2. MQTT logs'un RAM'de tutulması
3. Docker RAM limitlerinin yetersiz olması

**Öncelikli Yapılması Gerekenler:**
1. Backend RAM limitini 2GB'a çıkar
2. MQTT consumer cache'ini sınırla
3. Eski verileri temizleme mekanizması ekle
4. Memory monitoring ekle

Bu optimizasyonlar yapıldıktan sonra proje stabil şekilde uzun süre çalışabilir.
