# Sumatic Modern IoT - Coolify Deployment Kimlik Bilgileri

⚠️ **GÜVENLİK UYARISI**: Bu dosya hassas bilgiler içerir. Git'e commit etmeyin!

## 📋 Admin Kullanıcı Bilgileri

```
Username: admin
Email: admin@sumatic.io
Password: YOUR_ADMIN_PASSWORD_HERE
```

## 🔐 Database (PostgreSQL)

```
User: sumatic_user
Password: YOUR_DB_PASSWORD_HERE
Database: sumatic_production
```

## 📦 Redis

```
Password: YOUR_REDIS_PASSWORD_HERE
```

## 📡 MQTT (SSH Tunnel üzerinden)

```
Username: sumatic-backend-prod
Password: YOUR_MQTT_PASSWORD_HERE
Broker: 127.0.0.1:1883 (via SSH tunnel)
```

## 🔑 JWT Secret

```
Secret Key: YOUR_JWT_SECRET_KEY_HERE
Algorithm: HS256
```

## 🌐 SSH Tunnel

```
Remote Host: YOUR_SSH_HOST_IP_HERE
SSH User: sumatic-tunnel
SSH Port: 22
Remote MQTT: 127.0.0.1:1883
Local MQTT: 127.0.0.1:1883
```

### SSH Keys

**Public Key** (Remote sunucuya ekleyin):
```
YOUR_SSH_PUBLIC_KEY_HERE
```

**Private Key** (Coolify'da secret olarak ekleyin):
```
YOUR_SSH_PRIVATE_KEY_HERE
```

**Key Files:**
- Private: `deployment/coolify/sumatic_tunnel_key`
- Public: `deployment/coolify/sumatic_tunnel_key.pub`

## 🚀 Hızlı Giriş

1. **Admin Panel**: `https://your-domain.com/login`
2. **Username**: `admin`
3. **Password**: (Yukarıda belirlediğiniz şifre)

## 📝 Notlar

- İlk girişten sonra şifrenizi değiştirin
- Bu bilgileri güvenli bir yerde saklayın
- Production ortamında ek güvenlik önlemleri alın
- Düzenli backup yapın
- SSL sertifikası kullanın

## 🔧 SSH Key Kurulumu

### Remote Sunucuya Public Key Ekleme

```bash
# Remote sunucuya bağlanın
ssh root@YOUR_SSH_HOST_IP

# Public key'i authorized_keys'e ekleyin
echo 'YOUR_SSH_PUBLIC_KEY_HERE' >> /home/sumatic-tunnel/.ssh/authorized_keys

# İzinleri ayarla
chmod 600 /home/sumatic-tunnel/.ssh/authorized_keys
chown sumatic-tunnel:sumatic-tunnel /home/sumatic-tunnel/.ssh/authorized_keys
```

### Coolify'a Private Key Secret Olarak Ekleme

1. Coolify dashboard > Backend servisi > Environment Variables
2. **Add Secret** butonuna tıklayın
3. Name: `SSH_PRIVATE_KEY`
4. Value: (Yukarıdaki private key içeriğini yapıştırın)
5. **Add** butonuna tıklayın

### SSH Bağlantı Testi

```bash
ssh -i deployment/coolify/sumatic_tunnel_key sumatic-tunnel@YOUR_SSH_HOST_IP
```

## 🔧 Şifre Değiştirme

Şifreleri değiştirmek için:

1. Coolify dashboard > Environment Variables
2. İlgili değişkeni güncelleyin
3. Redeploy yapın
4. Admin şifresi için `create_admin_coolify.sh` script'ini çalıştırın

---

*Otomatik olarak oluşturuldu - 2026-03-28*
