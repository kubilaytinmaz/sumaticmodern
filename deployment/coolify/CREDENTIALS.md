# Sumatic Modern IoT - Coolify Deployment Kimlik Bilgileri

⚠️ **GÜVENLİK UYARISI**: Bu dosya hassas bilgiler içerir. Git'e commit etmeyin!

## 📋 Admin Kullanıcı Bilgileri

```
Username: admin
Email: admin@sumatic.io
Password: oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc
```

## 🔐 Database (PostgreSQL)

```
User: sumatic_user
Password: fFRYbPqdXFzn4KwV0spAW4IUhL39b8PVXhI2gE022rE
Database: sumatic_production
```

## 📦 Redis

```
Password: bEYDCdeQRh204E_OkjxxC_Oze_8XHueljdxR8pXUFIY
```

## 📡 MQTT (SSH Tunnel üzerinden)

```
Username: sumatic-backend-prod
Password: 1CsDlPIgPPXA0y2FuOIRLJHytrjZdxxFemQGmd42wM0
Broker: 127.0.0.1:1883 (via SSH tunnel)
```

## 🔑 JWT Secret

```
Secret Key: 037f148dd3367297c31571a0483c6d7e0a9f00e1413b5c87e226a3ef3dba91e5
Algorithm: HS256
```

## 🌐 SSH Tunnel

```
Remote Host: 31.58.236.246
SSH User: sumatic-tunnel
SSH Port: 22
Remote MQTT: 127.0.0.1:1883
Local MQTT: 127.0.0.1:1883
```

### SSH Keys

**Public Key** (Remote sunucuya ekleyin):
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHGEHfNti/WiHV6+593Aq4/JQsILyQbop9O3QxOUgOTH sumatic-tunnel@coolify
```

**Private Key** (Coolify'da secret olarak ekleyin):
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBxhB3zbYv1oh1evufdwKuPyULCC8kG6KfTt0MTlIDkxwAAAKAfBMDKHwTA
ygAAAAtzc2gtZWQyNTUxOQAAACBxhB3zbYv1oh1evufdwKuPyULCC8kG6KfTt0MTlIDkxw
AAAEB43xz2hGs2GRpQir3ZiNNlUsoOOrha0VFREwB6cnMynnGEHfNti/WiHV6+593Aq4/J
QsILyQbop9O3QxOUgOTHAAAAFnN1bWF0aWMtdHVubmVsQGNvb2xpZnkBAgMEBQYH
-----END OPENSSH PRIVATE KEY-----
```

**Key Files:**
- Private: `deployment/coolify/sumatic_tunnel_key`
- Public: `deployment/coolify/sumatic_tunnel_key.pub`

## 🚀 Hızlı Giriş

1. **Admin Panel**: `https://your-domain.com/login`
2. **Username**: `admin`
3. **Password**: `oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc`

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
ssh root@31.58.236.246

# Public key'i authorized_keys'e ekleyin
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHGEHfNti/WiHV6+593Aq4/JQsILyQbop9O3QxOUgOTH sumatic-tunnel@coolify' >> /home/sumatic-tunnel/.ssh/authorized_keys

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
ssh -i deployment/coolify/sumatic_tunnel_key sumatic-tunnel@31.58.236.246
```

## 🔧 Şifre Değiştirme

Şifreleri değiştirmek için:

1. Coolify dashboard > Environment Variables
2. İlgili değişkeni güncelleyin
3. Redeploy yapın
4. Admin şifresi için `create_admin_coolify.sh` script'ini çalıştırın

---

*Otomatik olarak oluşturuldu - 2026-03-28*
