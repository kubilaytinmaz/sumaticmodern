#!/usr/bin/env python3
"""
Coolify Environment Variables Generator
Tüm şifreleri otomatik oluşturur ve Coolify'a direk yapıştırılabilir formatta verir.
"""

import secrets
import sys
from urllib.parse import quote


def generate_secure_password(length=32):
    """URL-safe güvenli şifre üretir"""
    return secrets.token_urlsafe(length)


def url_encode_password(password):
    """Şifreyi URL encode eder (özel karakterler için)"""
    return quote(password, safe='')


def main():
    # Tüm şifreleri oluştur
    print("🔐 Şifreler oluşturuluyor...\n")
    
    postgres_user = "sumatic_user"
    postgres_password = generate_secure_password(32)
    postgres_db = "sumatic_production"
    
    redis_password = generate_secure_password(32)
    mqtt_password = generate_secure_password(32)
    jwt_secret = generate_secure_password(64)
    admin_password = generate_secure_password(32)
    
    # URL encode edilmiş versiyonlar
    postgres_password_encoded = url_encode_password(postgres_password)
    redis_password_encoded = url_encode_password(redis_password)
    
    # DATABASE_URL'i oluştur
    database_url = f"postgresql+asyncpg://{postgres_user}:{postgres_password_encoded}@postgres:5432/{postgres_db}"
    redis_url = f"redis://:{redis_password_encoded}@redis:6379/0"
    
    print("="*80)
    print("COOLIFY ENVIRONMENT VARIABLES")
    print("="*80)
    print("\n📋 Aşağıdaki tüm satırları kopyalayıp Coolify'a yapıştırın:\n")
    print("-"*80)
    
    # PostgreSQL için
    print("\n# PostgreSQL Servisi İçin:")
    print(f"POSTGRES_USER={postgres_user}")
    print(f"POSTGRES_PASSWORD={postgres_password}")
    print(f"POSTGRES_DB={postgres_db}")
    
    # Redis için
    print("\n# Redis Servisi İçin:")
    print(f"REDIS_PASSWORD={redis_password}")
    
    # Backend için - Tüm environment variables
    print("\n# Backend Servisi İçin (Tümünü kopyalayın):")
    print(f"POSTGRES_USER={postgres_user}")
    print(f"POSTGRES_PASSWORD={postgres_password}")
    print(f"POSTGRES_DB={postgres_db}")
    print(f"DATABASE_URL={database_url}")
    print("DATABASE_POOL_SIZE=20")
    print("DATABASE_MAX_OVERFLOW=40")
    print(f"REDIS_PASSWORD={redis_password}")
    print(f"REDIS_URL={redis_url}")
    print("MQTT_BROKER_HOST=127.0.0.1")
    print("MQTT_BROKER_PORT=1883")
    print("MQTT_USERNAME=sumatic-backend-prod")
    print(f"MQTT_PASSWORD={mqtt_password}")
    print("MQTT_CLIENT_ID=sumatic-backend-prod")
    print("MQTT_TOPIC_ALLDATAS=Alldatas")
    print("MQTT_TOPIC_COMMANDS=Commands")
    print("SSH_ENABLED=true")
    print("SSH_HOST=31.58.236.246")
    print("SSH_PORT=22")
    print("SSH_USER=sumatic-tunnel")
    print("SSH_KEY_PATH=/app/.ssh/sumatic_tunnel_key")
    print("SSH_REMOTE_MQTT_HOST=127.0.0.1")
    print("SSH_REMOTE_MQTT_PORT=1883")
    print("SSH_LOCAL_MQTT_HOST=127.0.0.1")
    print("SSH_LOCAL_MQTT_PORT=1883")
    print("SSH_KEEPALIVE=30")
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print("JWT_ALGORITHM=HS256")
    print("JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30")
    print("JWT_REFRESH_TOKEN_EXPIRE_DAYS=7")
    print("ADMIN_USERNAME=admin")
    print("ADMIN_EMAIL=admin@sumatic.io")
    print(f"ADMIN_PASSWORD={admin_password}")
    print("CORS_ORIGINS=http://46.225.231.44:3001,http://46.225.231.44:8001,http://localhost:3000")
    print("RATE_LIMIT_PER_MINUTE=100")
    print("APP_NAME=Sumatic Modern IoT")
    print("APP_VERSION=1.0.0")
    print("DEBUG=false")
    print("API_V1_PREFIX=/api/v1")
    print("TIMEZONE=Europe/Istanbul")
    print("DEVICE_OFFLINE_THRESHOLD_SECONDS=600")
    print("DEVICE_RETRY_INTERVAL_SECONDS=60")
    print("DEVICE_MAX_RETRIES=5")
    print("SNAPSHOT_INTERVAL_MINUTES=10")
    print("SPIKE_STREAK_THRESHOLD=5")
    print("SPIKE_WINDOW_SIZE=5")
    
    # Frontend için
    print("\n# Frontend Servisi İçin:")
    print("NEXT_PUBLIC_API_URL=http://46.225.231.44:8001")
    print("NEXT_PUBLIC_WS_URL=ws://46.225.231.44:8001")
    
    print("\n" + "-"*80)
    print("\n✅ Tüm environment variables hazır!")
    print("\n⚠️  ÖNEMLİ NOTLAR:")
    print("1. PostgreSQL, Redis ve Backend servislerine yukarıdaki değerleri yapıştırın")
    print("2. Frontend servisine sadece NEXT_PUBLIC_* değerlerini yapıştırın")
    print("3. Servisleri şu sırada yeniden başlatın: PostgreSQL → Redis → Backend → Frontend")
    print("4. Admin giriş bilgileri:")
    print(f"   Username: admin")
    print(f"   Password: {admin_password}")
    print("\n💾 Bu bilgileri güvenli bir yerde saklayın!")
    print("="*80)
    
    # Şifre güncelleme komutları
    print("\n" + "="*80)
    print("TÜM ŞİFRELERİ GÜNCELLEME KOMUTLARI")
    print("="*80)
    
    print("\n🔐 1. POSTGRESQL KULLANICI ŞİFRESİNİ GÜNCELLEME")
    print("-" * 80)
    print("\nCoolify Terminal'de **postgres** container'ını seçin ve şu komutu çalıştırın:\n")
    print(f"psql -U {postgres_user} -d {postgres_db} -c \"ALTER USER {postgres_user} WITH PASSWORD '{postgres_password}';\"")
    
    print("\n\n🔑 2. REDIS ŞİFRESİNİ GÜNCELLEME")
    print("-" * 80)
    print("\nCoolify Terminal'de **redis** container'ını seçin ve şu komutu çalıştırın:\n")
    print(f"redis-cli CONFIG SET requirepass '{redis_password}'")
    print(f"redis-cli AUTH '{redis_password}'")
    print(f"redis-cli CONFIG REWRITE")
    print(f"redis-cli SAVE")
    
    print("\n\n👤 3. ADMİN KULLANICI ŞİFRESİNİ GÜNCELLEME")
    print("-" * 80)
    print("\nCoolify Terminal'de **backend** container'ını seçin ve şu komutu çalıştırın:\n")
    print(f"cd /app && python change_admin_password.py \"{admin_password}\"")
    
    print("\n\n🔄 4. TÜM SERVİSLERİ YENİDEN BAŞLATMA SIRASI")
    print("-" * 80)
    print("\n1. PostgreSQL → Restart")
    print("2. Redis → Restart")
    print("3. Backend → Restart (admin kullanıcısı otomatik oluşturulur)")
    print("4. Frontend → Rebuild (NEXT_PUBLIC_* değişkenler build time'da bake edilir)")
    
    print("\n\n💻 5. GİRİŞ BİLGİLERİ")
    print("-" * 80)
    print(f"\n   URL: http://46.225.231.44:3001/login")
    print(f"   Username: admin")
    print(f"   Password: {admin_password}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    # Windows encoding fix
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
    
    main()
