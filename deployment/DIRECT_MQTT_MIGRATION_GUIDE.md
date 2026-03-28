# Doğrudan MQTT Geçiş Rehberi

## Özet

Bu rehber, SSH tüneli üzerinden MQTT bağlantısından doğrudan MQTT bağlantısına geçiş için tam bir hazırlık ve uygulama kılavuzu sağlar.

## Güvenlik Riskleri ve Önlemler

### Riskler
1. **Açık Port Eksposürü** - MQTT portları internete açık hale gelir
2. **Kaba Kuvvet Saldırıları** - Kimlik doğrulama saldırıları
3. **Veri Dinlenmesi** - TLS kullanılmazsa veriler şifresiz iletilir
4. **DDoS Saldırıları** - Kaynak tüketme saldırıları

### Zorunlu Güvenlik Önlemleri
- ✅ TLS/SSL şifreleme (Port 8883)
- ✅ Güçlü kimlik doğrulama (benzersiz kullanıcı adı/şifre)
- ✅ ACL ile yetkilendirme
- ✅ Güvenlik duvarı kuralları
- ✅ Fail2ban ile saldırı önleme
- ✅ Rate limiting

## Geçiş Öncesi Kontrol Listesi

### 1. Sertifika Hazırlığı
```bash
# Sertifikaları oluştur
cd deployment
sudo ./generate_mqtt_certs.sh
```

### 2. MQTT Kullanıcıları Oluştur
```bash
# Password dosyası oluştur
cd mqtt-broker
mosquitto_passwd -c passwd sumatic-backend
mosquitto_passwd -b passwd dashboard
mosquitto_passwd -b passwd admin
```

### 3. Güvenlik Duvarı Kuralları
```bash
# Güvenlik duvarını kur
cd deployment
sudo ./setup_mqtt_firewall.sh
```

### 4. Fail2ban Kurulumu
```bash
# Fail2ban'ı kur
cd deployment
sudo ./setup_fail2ban.sh
```

### 5. Cihaz IP Adreslerini Belirle
Modemlerin IP adreslerini belirleyin ve `TRUSTED_NETWORKS` listesine ekleyin.

## Geçiş Adımları

### Adım 1: SSH Tüneli Devre Dışı Bırakma

Backend `.env` dosyasında:
```bash
# SSH tünelini devre dışı bırak
SSH_ENABLED=false
```

### Adım 2: MQTT TLS Etkinleştirme

Backend `.env` dosyasında:
```bash
# MQTT TLS etkinleştir
MQTT_TLS_ENABLED=true
MQTT_BROKER_HOST=your-server-ip
MQTT_BROKER_PORT=8883
MQTT_TLS_CA_CERT=/app/mqtt-certs/ca.crt
MQTT_TLS_CLIENT_CERT=/app/mqtt-certs/client.crt
MQTT_TLS_CLIENT_KEY=/app/mqtt-certs/client.key
MQTT_TLS_INSECURE=false
```

### Adım 3: Modem Yapılandırması

Her modem için:
1. MQTT Broker IP: `your-server-ip`
2. MQTT Broker Port: `8883` (TLS)
3. Kullanıcı Adı: `device_xxx` (her cihaz için benzersiz)
4. Şifre: Güçlü, benzersiz şifre
5. TLS: Etkin
6. CA Certificate: Sunucu CA sertifikası

### Adım 4: Docker Compose Güncelleme

Production docker-compose dosyasını kullanın:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Adım 5: Test ve Doğrulama

```bash
# Test script'ini çal��ştır
cd deployment
./test_mqtt_connection.sh
```

## Geri Dönüş Planı

Sorun olursa SSH tüneline geri dönün:

```bash
# SSH tünelini tekrar etkinleştir
SSH_ENABLED=true
MQTT_TLS_ENABLED=false

# Servisleri yeniden başlat
docker-compose -f docker-compose.prod.yml restart backend
```

## Güvenlik İpuçları

1. **Sertifika Yönetimi**: Let's Encrypt sertifikaları kullanın
2. **Parola Gücü**: Minimum 16 karakter, karmaşık parolalar
3. **IP Beyaz Listesi**: Sadece güvenilir IP'lere izin verin
4. **Log İzleme**: MQTT loglarını düzenli kontrol edin
5. **Yedekleme**: Yapılandırma dosyalarını yedekleyin

## Destek

Sorun yaşarsanız:
1. Log dosyalarını kontrol edin: `docker logs sumatic-mqtt-prod`
2. Güvenlik duvarı kurallarını doğrulayın
3. Sertifika geçerliliğini kontrol edin
