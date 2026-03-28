# SSH Tünelinden Doğrudan MQTT'ye Geçiş Planı

## 📋 İçindekiler

1. [Genel Bakış](#genel-bakış)
2. [Güvenlik Analizi](#güvenlik-analizi)
3. [Ön Hazırlık](#ön-hazırlık)
4. [Geçiş Adımları](#geçiş-adımları)
5. [Test ve Doğrulama](#test-ve-doğrulama)
6. [Geri Dönüş Planı](#geri-dönüş-planı)
7. [Sorun Giderme](#sorun-giderme)

---

## Genel Bakış

### Mevcut Durum (SSH Tüneli)
```
Modemler → Uzak MQTT Broker → SSH Tüneli → Local Backend
```

### Hedef Durum (Doğrudan MQTT)
```
Modemler → Internet → MQTT Broker (TLS) → Backend
```

### Avantajlar
- ✅ Daha az karmaşıklık (SSH tüneli yok)
- ✅ Daha iyi performans (tünel overhead'i yok)
- ✅ Daha kolay monitoring ve debugging
- ✅ Ölçeklenebilirlik

### Dezavantajlar
- ⚠️ Daha fazla güvenlik önlemi gerekli
- ⚠️ TLS sertifikası yönetimi gerekli
- ⚠️ IP beyaz listesi yönetimi gerekli

---

## Güvenlik Analizi

### Riskler ve Önlemler

| Risk | Seviye | Önlem |
|------|-------|--------|
| Açık port eksposürü | Yüksek | TLS + Güvenlik duvarı |
| Kaba kuvvet saldırısı | Orta | Fail2ban + Rate limiting |
| Veri dinlenmesi | Yüksek | TLS/SSL şifreleme |
| DDoS saldırısı | Orta | Rate limiting + Firewall |
| Yetkisiz erişim | Yüksek | ACL + Güçlü parolalar |

### Zorunlu Güvenlik Katmanları

1. **TLS/SSL Şifreleme** (Port 8883)
   - Sertifika: Let's Encrypt veya self-signed
   - TLS versiyonu: 1.2 veya üzeri
   - Cipher suite: Güçlü şifreler

2. **Kimlik Doğrulama**
   - Benzersiz kullanıcı adı/şifre her cihaz için
   - Minimum 16 karakter parola
   - ACL ile yetkilendirme

3. **Güvenlik Duvarı**
   - Sadece TLS portları açık (8883, 9883)
   - Plain MQTT portları kapalı (1883, 9001)
   - IP beyaz listesi

4. **Saldırı Önleme**
   - Fail2ban ile IP banlama
   - Rate limiting ile istek sınırlama
   - Log monitoring

---

## Ön Hazırlık

### 1. Sertifika Oluşturma

```bash
cd deployment
sudo ./generate_mqtt_certs.sh
```

Oluşturulan dosyalar:
- `mqtt-broker/certs/ca.crt` - CA sertifika
- `mqtt-broker/certs/mqtt-server.crt` - Sunucu sertifikası
- `mqtt-broker/certs/mqtt-server.key` - Sunucu private key
- `mqtt-broker/certs/client.crt` - İstemci sertifikası
- `mqtt-broker/certs/client.key` - İstemci private key

### 2. MQTT Kullanıcıları Oluşturma

```bash
cd deployment
sudo ./create_mqtt_users.sh
```

Oluşturulacak kullanıcılar:
- `sumatic-backend` - Backend servisi için
- `dashboard` - Frontend için
- `admin` - Yönetici için
- `device_xxx` - Her cihaz için

### 3. Güvenlik Duvarı Kurulumu

```bash
cd deployment
sudo ./setup_mqtt_firewall.sh
```

### 4. Fail2ban Kurulumu

```bash
cd deployment
sudo ./setup_fail2ban.sh
```

### 5. Cihaz IP'lerini Belirleme

Modemlerin IP adreslerini listeleyin ve `TRUSTED_NETWORKS`'e ekleyin:

```bash
# deployment/setup_mqtt_firewall.sh dosyasında
TRUSTED_NETWORKS=(
    "192.168.1.0/24"      # Local network
    "10.0.0.0/8"          # Private network
    "203.0.113.0/24"      # Modem IP range (örnek)
)
```

---

## Geçiş Adımları

### Adım 1: Yedekleme

```bash
# Mevcut yapılandırmaları yedekle
mkdir -p backups/pre-migration-$(date +%Y%m%d)
cp backend/.env backups/pre-migration-$(date +%Y%m%d)/
cp docker-compose.prod.yml backups/pre-migration-$(date +%Y%m%d)/
cp mqtt-broker/mosquitto.conf backups/pre-migration-$(date +%Y%m%d)/
```

### Adım 2: Backend Yapılandırması

`backend/.env` dosyasını güncelleyin:

```bash
# SSH tünelini devre dışı bırak
SSH_ENABLED=false

# MQTT TLS etkinleştir
MQTT_TLS_ENABLED=true
MQTT_BROKER_HOST=your-server-ip
MQTT_BROKER_PORT=8883
MQTT_TLS_CA_CERT=/app/mqtt-certs/ca.crt
MQTT_TLS_CLIENT_CERT=/app/mqtt-certs/client.crt
MQTT_TLS_CLIENT_KEY=/app/mqtt-certs/client.key
MQTT_TLS_INSECURE=false
```

### Adım 3: Mosquitto Yapılandırması

Production config'i kullanın:

```bash
cp mqtt-broker/mosquitto.conf.production mqtt-broker/mosquitto.conf
```

### Adım 4: ACL Güncelleme

```bash
cp mqtt-broker/acl.production mqtt-broker/acl
```

### Adım 5: Docker Compose Güncelleme

`docker-compose.prod.yml` dosyası zaten güncellendi. Kontrol edin:

```yaml
mqtt:
  ports:
    # - "1883:1883"  # DISABLED
    - "8883:8883"    # MQTTS enabled
    # - "9001:9001"  # DISABLED
    - "9883:9883"    # WSS enabled

backend:
  volumes:
    - ./mqtt-broker/certs:/app/mqtt-certs:ro
  environment:
    - MQTT_TLS_ENABLED=true
```

### Adım 6: Servisleri Yeniden Başlatma

```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Adım 7: Bağlantı Testi

```bash
cd deployment
./test_mqtt_connection.sh localhost 8883
```

---

## Test ve Doğrulama

### 1. MQTT Broker Testi

```bash
# Broker durumunu kontrol et
docker logs sumatic-mqtt-prod

# TLS bağlantısını test et
openssl s_client -connect localhost:8883
```

### 2. Backend Testi

```bash
# Backend loglarını kontrol et
docker logs sumatic-backend-prod

# MQTT bağlantısını kontrol et
docker logs sumatic-backend-prod | grep MQTT
```

### 3. Cihaz Bağlantı Testi

Her cihaz için:
1. Modem yapılandırmasını güncelleyin
2. MQTT Broker IP: Yeni sunucu IP
3. MQTT Broker Port: 8883 (TLS)
4. TLS: Etkin
5. CA Certificate: Sunucu CA sertifikası

### 4. Veri Akışı Testi

```bash
# MQTT topic'lerini dinle
mosquitto_sub -h localhost -p 8883 \
  --cafile mqtt-broker/certs/ca.crt \
  -u sumatic-backend -P your-password \
  -t "Alldatas" -v
```

---

## Geri Dönüş Planı

Sorun olursa SSH tüneline geri dönün:

### 1. Backend Yapılandırmasını Geri Al

```bash
# backend/.env dosyasında
SSH_ENABLED=true
MQTT_TLS_ENABLED=false
MQTT_BROKER_PORT=1883
```

### 2. Servisleri Yeniden Başlat

```bash
docker-compose -f docker-compose.prod.yml restart backend
```

### 3. Kontrol

```bash
docker logs sumatic-backend-prod | grep -i ssh
```

---

## Sorun Giderme

### Sorun: TLS Sertifika Hatası

**Çözüm:**
```bash
# Sertifika geçerliliğini kontrol et
openssl x509 -in mqtt-broker/certs/mqtt-server.crt -text -noout

# Sertifikaları yeniden oluştur
cd deployment
sudo ./generate_mqtt_certs.sh
```

### Sorun: Kimlik Doğrulama Hatası

**Çözüm:**
```bash
# Password dosyasını kontrol et
mosquitto_passwd -c mqtt-broker/passwd new-user

# ACL dosyasını kontrol et
cat mqtt-broker/acl
```

### Sorun: Güvenlik Duvarı Bağlantıyı Engelliyor

**Çözüm:**
```bash
# Güvenlik duvarı kurallarını kontrol et
sudo ufw status
sudo iptables -L -n

# MQTT portuna izin ver
sudo ufw allow 8883/tcp
```

### Sorun: Cihazlar Bağlanamıyor

**Çözüm:**
1. Cihaz IP'sini beyaz listeye ekleyin
2. CA sertifikasını cihaza yükleyin
3. TLS yapılandırmasını kontrol edin
4. MQTT loglarını inceleyin

### Sorun: Veri Gelmiyor

**Çözüm:**
```bash
# Backend loglarını kontrol et
docker logs sumatic-backend-prod -f

# MQTT loglarını kontrol et
docker logs sumatic-mqtt-prod -f

# Topic aboneliklerini kontrol et
mosquitto_sub -h localhost -p 8883 \
  --cafile mqtt-broker/certs/ca.crt \
  -u sumatic-backend -P your-password \
  -t "\$SYS/#" -C 10
```

---

## Checklist

### Geçiş Öncesi
- [ ] TLS sertifikaları oluşturuldu
- [ ] MQTT kullanıcıları oluşturuldu
- [ ] ACL dosyası yapılandırıldı
- [ ] Güvenlik duvarı kurulumu yapıldı
- [ ] Fail2ban kurulumu yapıldı
- [ ] Cihaz IP'leri belirlendi
- [ ] Yedekleme alındı

### Geçiş Sırası
- [ ] Backend .env güncellendi
- [ ] Mosquitto.conf güncellendi
- [ ] ACL güncellendi
- [ ] Docker compose güncellendi
- [ ] Servisler yeniden başlatıldı
- [ ] Bağlantı testi başarılı

### Geçiş Sonrası
- [ ] Tüm cihazlar bağlandı
- [ ] Veri akışı normal
- [ ] Loglar temiz
- [ ] Performans kabul edilebilir
- [ ] Güvenlik önlemleri aktif

---

## İletişim ve Destek

Sorun yaşarsanız:
1. Log dosyalarını kontrol edin
2. Test script'lerini çalıştırın
3. Bu dokümantasyonu inceleyin
4. Geri dönüş planını uygulayın

---

## Sonraki Adımlar

Geçiş tamamlandıktan sonra:
1. 1 hafta boyunca logları izleyin
2. Performans metriklerini kaydedin
3. Güvenlik loglarını düzenli kontrol edin
4. Olay response planını hazırlayın
5. Yedekleme stratejisini güncelleyin
