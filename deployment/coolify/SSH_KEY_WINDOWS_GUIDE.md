# SSH Key Oluşturma - Windows için Coolify Deployment

Bu rehber, Windows üzerinde SSH key oluşturmanız için adım adım talimatlar içerir.

## ✅ SSH Key'ler Zaten Oluşturuldu!

SSH key'ler zaten oluşturuldu ve `deployment/coolify/` dizininde mevcut:

- **Private Key**: `deployment/coolify/sumatic_tunnel_key`
- **Public Key**: `deployment/coolify/sumatic_tunnel_key.pub`

### Public Key (Remote Sunucuya Ekleyin)

```
YOUR_SSH_PUBLIC_KEY_HERE
```

### Private Key (Coolify'da Secret Olarak Ekleyin)

```
YOUR_SSH_PRIVATE_KEY_HERE
```

---

## Remote Sunucuya Public Key Ekleme

### 1. Remote Sunucuya Bağlanın

```bash
ssh root@YOUR_SSH_HOST_IP
```

### 2. SSH Kullanıcısı Oluşturun (Henüz yoksa)

```bash
# SSH kullanıcısı oluştur
useradd -m -s /bin/bash sumatic-tunnel

# SSH dizini oluştur
mkdir -p /home/sumatic-tunnel/.ssh
chmod 700 /home/sumatic-tunnel/.ssh
chown sumatic-tunnel:sumatic-tunnel /home/sumatic-tunnel/.ssh
```

### 3. Public Key'i Ekleyin

```bash
# Public key'i authorized_keys'e ekle
echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHGEHfNti/WiHV6+593Aq4/JQsILyQbop9O3QxOUgOTH sumatic-tunnel@coolify' >> /home/sumatic-tunnel/.ssh/authorized_keys

# İzinleri ayarla
chmod 600 /home/sumatic-tunnel/.ssh/authorized_keys
chown sumatic-tunnel:sumatic-tunnel /home/sumatic-tunnel/.ssh/authorized_keys
```

### 4. SSH Bağlantısını Test Edin

Local bilgisayarınızda:

```bash
ssh -i deployment/coolify/sumatic_tunnel_key sumatic-tunnel@31.58.236.246
```

Başarılı olursa bağlantı kurulacaktır.

---

## Coolify'a SSH Private Key Ekleme

### 1. Coolify Dashboard'a Gidin

1. Projenizi seçin
2. Backend servisine gidin
3. "Environment Variables" sekmesine tıklayın

### 2. Secret Olarak Ekleyin

1. **"Add Secret"** butonuna tıklayın
2. **Name**: `SSH_PRIVATE_KEY`
3. **Value**: (Yukarıdaki private key içeriğini yapıştırın)
4. **"Add"** butonuna tıklayın

### 3. Environment Variables Ekleyin

Aşağıdaki environment variables'ları da ekleyin:

```env
SSH_ENABLED=true
SSH_HOST=31.58.236.246
SSH_PORT=22
SSH_USER=sumatic-tunnel
SSH_KEY_PATH=/app/.ssh/sumatic_tunnel_key
SSH_REMOTE_MQTT_HOST=127.0.0.1
SSH_REMOTE_MQTT_PORT=1883
SSH_LOCAL_MQTT_HOST=127.0.0.1
SSH_LOCAL_MQTT_PORT=1883
SSH_KEEPALIVE=30
```

---

## Docker Compose Güncelleme

Docker compose dosyasında SSH key'i mount etmek için şu volume'u eklediğimizden emin olun:

```yaml
volumes:
  # SSH key için volume
  - ssh_keys:/app/.ssh:ro
```

---

## Sorun Giderme

### SSH Key Oluşturma Hatası

```
Error: ssh-keygen not found
```

**Çözüm**: Git for Windows'u yükleyin veya Windows 10/11'de "OpenSSH Client" özelliğini etkinleştirin:
1. Settings > Apps > Optional Features
2. "OpenSSH Client" özelliğini aratın ve yükleyin

### Permission Denied Hatası

```
Permission denied (publickey)
```

**Çözüm**:
1. Public key'in remote sunucuda doğru yerde olduğundan emin olun
2. authorized_keys dosyasının izinlerini kontrol edin (600)
3. SSH kullanıcısının doğru olduğundan emin olun

### Connection Timeout Hatası

```
Connection timed out
```

**Çözüm**:
1. Firewall ayarlarını kontrol edin (port 22 açık olmalı)
2. SSH servisinin remote sunucuda çalıştığını kontrol edin
3. IP adresinin doğru olduğundan emin olun

---

## Kontrol Listesi

- [x] SSH key oluşturuldu
- [ ] Public key remote sunucuya eklendi
- [ ] SSH bağlantısı test edildi
- [ ] Private key Coolify'da secret olarak eklendi
- [ ] Environment variables eklendi
- [ ] Docker compose güncellendi
- [ ] Deploy başlatıldı

---

## Hızlı Komutlar

```powershell
# Public key görüntüle
cat deployment/coolify/sumatic_tunnel_key.pub

# Private key görüntüle
cat deployment/coolify/sumatic_tunnel_key

# SSH bağlantı testi
ssh -i deployment/coolify/sumatic_tunnel_key sumatic-tunnel@31.58.236.246
```

## Özet

1. ✅ SSH key'ler oluşturuldu (`deployment/coolify/` dizininde)
2. 📋 Public key: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHGEHfNti/WiHV6+593Aq4/JQsILyQbop9O3QxOUgOTH sumatic-tunnel@coolify`
3. 🔐 Private key: `deployment/coolify/sumatic_tunnel_key`
4. 🌐 Remote sunucuya public key'i ekleyin
5. 🚀 Coolify'da private key'i secret olarak ekleyin
