# Tuya Timer API - Başarılı Implementasyon

## Tarih
2026-04-01

## Sonuç: BAŞARILI

Timer API abone olundu, test edildi ve production'a implement edildi.

## Timer API Detayları

### Endpoint
```
POST /v2.0/cloud/timer/device/{device_id}
```

### Request Body
```json
{
  "alias_name": "Restart OFF",
  "time": "12:00",
  "timezone_id": "Europe/Istanbul",
  "date": "20260401",
  "loops": "0000000",
  "functions": [{"code": "power", "value": false}]
}
```

### Önemli Bulgular
- **Function code**: `"power"` (bu cihaz için `switch_1` değil!)
- **`enable` alanı yanıltıcı**: API'de `enable=false` görünse de timer'lar çalışıyor
- **Minimum 2 dakika**: Timer'lar en az 2 dakika ileriye ayarlanmalı
- **Timer'lar cihazda yerel çalışır**: İnternet kesintisinde bile çalışır

### Restart Stratejisi
1. **Timer** (öncelik) - Cloud Timer API ile OFF/ON timer oluşturur
2. **Countdown** - Cihaz destekliyorsa countdown DP kullanır
3. **Relay Status** - Power-on recovery kullanır
4. **Sequential** - Klasik OFF -> bekle -> ON yaklaşımı

### Timing
- OFF timer: 2 dakika sonra
- ON timer: 3 dakika sonra
- Toplam restart süresi: ~3 dakika

## Implementasyon Dosyaları
- Backend: `backend/app/services/tuya_service.py` - `_restart_with_cloud_timer()`
- Frontend: `frontend/src/types/tuya.ts` - `strategy: 'timer'` tipi
- Frontend: `frontend/src/app/(dashboard)/tuya-devices/page.tsx` - Timer mesajı
