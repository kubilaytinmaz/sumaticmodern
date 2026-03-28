# Sumatic Modern IoT - Coolify Hızlı Başlangıç

Bu rehber, Sumatic Modern IoT uygulamasını Coolify'a hızlıca deploy etmek için temel adımları içerir.

## 🚀 Hızlı Deploy (5 Dakika)

### 1. SSH Key Hazırlama

SSH key'ler zaten oluşturuldu ve `deployment/coolify/` dizininde mevcut:

**Public Key** (Remote sunucuya ekleyin):
```bash
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHGEHfNti/WiHV6+593Aq4/JQsILyQbop9O3QxOUgOTH sumatic-tunnel@coolify
```

**Remote sunucuya eklemek için:**
```bash
ssh root@31.58.236.246
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHGEHfNti/WiHV6+593Aq4/JQsILyQbop9O3QxOUgOTH sumatic-tunnel@coolify' >> /home/sumatic-tunnel/.ssh/authorized_keys
chmod 600 /home/sumatic-tunnel/.ssh/authorized_keys
chown sumatic-tunnel:sumatic-tunnel /home/sumatic-tunnel/.ssh/authorized_keys
```

**Private Key** (Coolify'da secret olarak ekleyin):
- Dosya: `deployment/coolify/sumatic_tunnel_key`
- Coolify'da: Backend servisi > Environment Variables > Add Secret
- Name: `SSH_PRIVATE_KEY`
- Value: (dosya içeriğini yapıştırın)

### 2. Coolify Proje Oluşturma

1. Coolify dashboard > **New Project**
2. **Add Resource** > **Docker Compose**
3. Repository: `sumaticmodern`
4. Branch: `main`
5. Compose path: `deployment/coolify/docker-compose.coolify.yml`

### 3. Environment Variables

Coolify'da backend servisi için şu değişkenleri ekleyin:

```env
# Admin (İlk kurulum için)
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@sumatic.io
ADMIN_PASSWORD=oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc

# Database
POSTGRES_USER=sumatic_user
POSTGRES_PASSWORD=fFRYbPqdXFzn4KwV0spAW4IUhL39b8PVXhI2gE022rE
POSTGRES_DB=sumatic_production

# Redis
REDIS_PASSWORD=bEYDCdeQRh204E_OkjxxC_Oze_8XHueljdxR8pXUFIY

# JWT
JWT_SECRET_KEY=037f148dd3367297c31571a0483c6d7e0a9f00e1413b5c87e226a3ef3dba91e5

# Domain
CORS_ORIGINS=https://your-domain.com

# SSH Tunnel
SSH_HOST=31.58.236.246
SSH_USER=sumatic-tunnel
```

Frontend servisi için:

```env
NEXT_PUBLIC_API_URL=https://api.your-domain.com
NEXT_PUBLIC_WS_URL=wss://api.your-domain.com
```

### 4. SSH Private Key Secret

1. Backend servisi > **Environment Variables**
2. **Add Secret**
3. Name: `SSH_PRIVATE_KEY`
4. Value: (`deployment/coolify/sumatic_tunnel_key` dosyasının içeriğini yapıştırın)

### 5. Deploy

1. **Deploy** butonuna tıklayın
2. Build loglarını izleyin
3. Deploy tamamlandıktan sonra admin oluşturun

### 6. Admin Kullanıcı Oluşturma

```bash
cd deployment/coolify
chmod +x create_admin_coolify.sh
export ADMIN_PASSWORD=oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc
./create_admin_coolify.sh
```

### 7. Giriş Yapın

- URL: `https://your-domain.com/login`
- Username: `admin`
- Password: `oPf_6th1lXwOIBKQpTcVC64z8b-ZwzF8w-mTiZcQwfc`

---

## 📋 Kontrol Listesi

Deploy öncesi kontrol listesi:

- [ ] SSH key oluşturuldu
- [ ] Public key remote sunucuya eklendi
- [ ] SSH bağlantısı test edildi
- [ ] Coolify projesi oluşturuldu
- [ ] Environment variables eklendi
- [ ] SSH private key secret olarak eklendi
- [ ] Domain DNS ayarları yapıldı
- [ ] Deploy başlatıldı
- [ ] Admin kullanıcısı oluşturuldu
- [ ] Giriş test edildi

---

## 🔧 Yaygın Sorunlar

### SSH Tunnel Çalışmıyor

```bash
# SSH bağlantısını test edin
ssh -i ~/.ssh/sumatic_tunnel_key sumatic-tunnel@31.58.236.246

# Backend container loglarını kontrol edin
docker logs sumatic-backend-coolify | grep -i ssh
```

### Admin Giriş Hatası

```bash
# Admin kullanıcısını yeniden oluşturun
cd deployment/coolify
./create_admin_coolify.sh
```

### MQTT Bağlantı Hatası

```bash
# Tunnel durumunu kontrol edin
docker exec sumatic-backend-coolify ps aux | grep ssh

# MQTT portunu kontrol edin
docker exec sumatic-backend-coolify netstat -tlnp | grep 1883
```

---

## 📚 Detaylı Bilgi

Detaylı bilgi için [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) dosyasına bakın.

## 🔐 Güvenlik Notları

1. İlk girişten sonra şifrenizi değiştirin
2. SSH private key'i güvenli saklayın
3. Güçlü şifreler kullanın
4. HTTPS kullanın
5. Düzenli backup alın

---

## 🆘 Destek

Sorun yaşarsanız:
- GitHub Issues
- Deployment rehberi: [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md)
- MQTT güvenlik: [`../MQTT_SECURITY_README.md`](../MQTT_SECURITY_README.md)
