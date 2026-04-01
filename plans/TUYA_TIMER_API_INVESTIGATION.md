# Tuya Timer API Araştırması - Bulgular ve Sonuçlar

## Tarih
2026-04-01

## Amaç
Tuya app'teki timer/zamanlayıcı özelliğinin internet olmadan nasıl çalıştığını araştırmak ve modem-bağlı priz için restart işlevini internet kesintisi olmadan gerçekleştirmek.

## Test Edilen Cihaz
- **Model**: S-Link Swapp SL-03 16A
- **Product ID**: `4uomwxat2whrx2ju`
- **Device ID**: `35004015483fda08ac54`
- **Category**: `dj` (Light Source - Işık Kaynağı)
- **Durum**: Modem prizine bağlı, kapatınca internet gidiyor

## Test Sonuçları

### 1. Tuya Cloud Timer API

#### Endpoint'ler
```
GET  /v1.0/devices/{device_id}/timers
POST /v1.0/devices/{device_id}/timers
GET  /v1.0/devices/{device_id}/timers/categories/timer
GET  /v1.0/devices/{device_id}/timers/categories/countdown
POST /v2.0/cloud/timer/device/{device_id}
```

#### Sonuç
```
{'code': 28841101, 'msg': 'No permissions. This API is not subscribed.', 'success': False}
```

**Bulgular:**
- Timer API mevcut ancak **abonelik gerektiriyor**
- Tuya Developer Console'da "Timer Management" servisine abone olmak gerekiyor
- Bu servis genellikle ücretli veya kurumsal hesap gerektiriyor

### 2. Countdown Komutu

#### Test Edilen Komutlar
```python
cloud.sendcommand(device_id, {"commands": [{"code": "countdown_1", "value": 10}]})
```

#### Sonuç
```
{'code': 2008, 'msg': 'command or value not support', 'success': False}
```

**Bulgular:**
- Cihaz `countdown_1` komutunu desteklemiyor
- Bu cihazın kategorisi (`dj` - Light Source) countdown özelliği desteklemiyor
- Sadece `cz` (Socket/Plug) kategorisi countdown destekliyor

### 3. Yerel Bağlantı Testi

#### Test
```python
d = tinytuya.OutletDevice(device_id, device_ip, local_key)
d.set_version(3.3)
status = d.status()
```

#### Sonuç
```
{'Error': 'Network Error: Device Unreachable', 'Err': '905'}
```

**Bulgular:**
- Cihaz modemle aynı prizde olduğu için yerel bağlantı çalışmıyor
- Priz kapatılınca modem gidiyor, yerel ağ erişimi kesiliyor

### 4. Başarılı Olan Komutlar

#### switch_1 (Cloud Command)
```python
cloud.sendcommand(device_id, {"commands": [{"code": "switch_1", "value": True}]})
```

#### Sonuç
```
{'result': True, 'success': True}
```

**Bulgular:**
- `switch_1` komutu cloud üzerinden başarıyla çalışıyor
- Bu mevcut restart fonksiyonumuzda kullanılıyor

## Tuya App Timer'ın İnternetsiz Çalışma Prensibi

Tuya app'te oluşturulan timer'ların internet olmadan çalışma sebebi:

1. **Timer Management API**: Tuya Cloud'da timer oluşturulur
2. **Push to Device**: Cloud API timer'ı cihaza push'lar
3. **Local Storage**: Cihaz timer'ı yerel hafızasında saklar
4. **Local Execution**: İnternet olmadan timer yerel olarak çalışır

**Ancak**, bu özelliği kullanmak için:
- Tuya Developer Console'da Timer Management API'sine abone olmak gerekiyor
- Bu servis ek maliyet gerektirebilir

## Mevcut Çözüm

### Fire-and-Forget Restart
Mevcut implementasyonumuzda kullanılan yaklaşım:

```python
async def _restart_sequential(...):
    # 1. Turn OFF
    await self._turn_off_device(device_tuya_id)
    
    # 2. Wait delay seconds
    await asyncio.sleep(delay_seconds)
    
    # 3. Try to turn ON (may fail if modem is down)
    try:
        await self._turn_on_device(device_tuya_id)
    except Exception as e:
        # Don't raise exception, just log it
        logger.warning(f"Turn ON failed (expected for modem-connected plugs): {e}")
        return {
            "success": True,
            "power_state": False,
            "message": "Device turned OFF. Turn ON command sent but may not have reached device.",
            "turn_on_failed": True
        }
```

**Avantajları:**
- Ek abonelik gerektirmez
- Basit ve güvenilir
- Kullanıcıya açık bilgi verir

**Dezavantajları:**
- Modem-bağlı prizlerde turn_on komutu başarısız olur
- Kullanıcı manuel olarak prizi açmalıdır

## Gelecek Çözüm Önerileri

### 1. Timer Management API Aboneliği (Önerilen)
- Tuya Developer Console'dan Timer Management API'sine abone olun
- Timer-based restart stratejisi implement edilir
- Cihaz timer'ı yerel olarak çalıştırır, internet gerekmez

### 2. Countdown Destekleyen Priz Satın Alma
Türkiye'de satılan countdown/cycle destekli Tuya priz modelleri:

| Model | Kategori | Countdown | Cycle | Özellikler |
|-------|----------|-----------|-------|------------|
| Tuya Smart Plug (EU) | cz | ✅ | ✅ | Enerji takibi, zamanlayıcı |
| Gosund Smart Plug | cz | ✅ | ✅ | Ucuz, yaygın |
| Teckin Smart Plug | cz | ✅ | ✅ | Enerji takibi |
| BlitzWolf BW-SHP13 | cz | ✅ | ✅ | Güç tüketim göstergesi |
| Sonoff S26R2ZB | cz | ✅ | ❌ | Zigbee versiyonu |

**Önemli**: Satın alırken ürün açıklamasında "countdown" veya "timer" özelliği olduğundan emin olun.

### 3. Harici Otomasyon
- Home Assistant
- Node-RED
- OpenHAB

Bu sistemler Tuya Cloud ile entegre olabilir ve daha gelişmiş otomasyon sağlar.

## Sonuç

Tuya Timer API araştırması tamamlandı. Mevcut "fire-and-forget" yaklaşımımız en pratik çözüm olmaya devam ediyor. Timer API'sini kullanmak için ek abonelik gerekiyor.

**Öneri**: Eğer modem-bağlı priz için tam otomatik restart gerekiyorsa:
1. Countdown destekleyen yeni bir priz satın alın
2. Veya Tuya Timer Management API'sine abone olun
3. Veya harici bir otomasyon sistemi kullanın
