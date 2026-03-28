#!/usr/bin/env python3
"""
Sumatic Modern IoT - Production Security Setup Script

Bu script production ortamı için güvenli random değerler üretir
ve .env.production dosyasını oluşturur.

Kullanım:
    python setup_production_secrets.py

⚠️ UYARI: Bu script sadece production deployment öncesi bir kez çalıştırılmalıdır.
Üretilen değerler güvenli bir şekilde saklanmalı ve git'e commit edilmemelidir.
"""

import secrets
import os
import sys
from pathlib import Path


def generate_jwt_secret() -> str:
    """Güvenli JWT secret key üretir (64 bytes = ~86 chars base64url encoded)"""
    return secrets.token_urlsafe(64)


def generate_mqtt_password() -> str:
    """Güvenli MQTT password üretir (32 bytes = ~43 chars)"""
    return secrets.token_urlsafe(32)


def generate_database_password() -> str:
    """Güvenli database password üretir (32 bytes = ~43 chars)"""
    return secrets.token_urlsafe(32)


def generate_redis_password() -> str:
    """Güvenli Redis password üretir (32 bytes = ~43 chars)"""
    return secrets.token_urlsafe(32)


def create_production_env(
    production_domain: str = "sumatic.example.com",
    db_host: str = "localhost",
    db_port: str = "5432",
    db_name: str = "sumatic_production",
    db_user: str = "sumatic_user",
    ssh_host: str = "31.58.236.246",
    ssh_user: str = "sumatic-tunnel",
    ssh_key_path: str = "/path/to/ssh/private/key"
):
    """Production .env dosyasını oluşturur
    
    Args:
        production_domain: Production domain adresi
        db_host: PostgreSQL host adresi
        db_port: PostgreSQL port numarası
        db_name: Veritabanı adı
        db_user: Veritabanı kullanıcı adı
        ssh_host: SSH tunnel host adresi
        ssh_user: SSH tunnel kullanıcı adı
        ssh_key_path: SSH private key dosya yolu
    """
    
    # Güvenli değerleri üret
    jwt_secret = generate_jwt_secret()
    mqtt_password = generate_mqtt_password()
    db_password = generate_database_password()
    redis_password = generate_redis_password()
    
    www_domain = f"www.{production_domain}"
    
    # .env.production dosyasini olustur
    env_content = f"""# ==============================================================================
# Sumatic Modern IoT - Production Environment Configuration
# ==============================================================================
# KRITIK GUVENLIK UYARISI: Bu dosya production icin olusturulmustur.
# Bu dosyayi asla git'e commit etmeyin ve guvenli bir sekilde saklayin.
# ==============================================================================

# -----------------------------------------------------------------------------
# Application Settings
# -----------------------------------------------------------------------------
APP_NAME=Sumatic Modern IoT
APP_VERSION=1.0.0
DEBUG=false
API_V1_PREFIX=/api/v1

# -----------------------------------------------------------------------------
# Database (PostgreSQL - Production)
# -----------------------------------------------------------------------------
DATABASE_URL=postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# -----------------------------------------------------------------------------
# Redis (Production - Rate Limiting)
# -----------------------------------------------------------------------------
REDIS_URL=redis://:{redis_password}@localhost:6379/0

# -----------------------------------------------------------------------------
# MQTT Configuration (SSH Tunnel uzerinden)
# -----------------------------------------------------------------------------
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1883
MQTT_USERNAME=sumatic-backend-prod
MQTT_PASSWORD={mqtt_password}
MQTT_CLIENT_ID=sumatic-backend-prod
MQTT_TOPIC_ALLDATAS=Alldatas
MQTT_TOPIC_COMMANDS=Commands

# -----------------------------------------------------------------------------
# SSH Tunnel Configuration
# -----------------------------------------------------------------------------
# GUVENLIK: SSH key-based authentication kullaniliyor
SSH_ENABLED=true
SSH_HOST={ssh_host}
SSH_PORT=22
SSH_USER={ssh_user}
# SSH_PASSWORD=  # Production'da kullanılmıyor
SSH_KEY_PATH={ssh_key_path}
SSH_REMOTE_MQTT_HOST=127.0.0.1
SSH_REMOTE_MQTT_PORT=1883
SSH_LOCAL_MQTT_HOST=127.0.0.1
SSH_LOCAL_MQTT_PORT=1883
SSH_KEEPALIVE=30

# -----------------------------------------------------------------------------
# JWT Authentication - KRITIK GUVENLIK
# -----------------------------------------------------------------------------
# Bu key guvenli bir sekilde saklanmali ve asla degistirilmemelidir
JWT_SECRET_KEY={jwt_secret}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# -----------------------------------------------------------------------------
# Security Settings
# -----------------------------------------------------------------------------
# CORS_ORIGINS sadece production domain'lerini iceriyor
CORS_ORIGINS=https://{production_domain},https://{www_domain}

# Rate limiting (requests per minute per IP)
RATE_LIMIT_PER_MINUTE=100

# -----------------------------------------------------------------------------
# Timezone
# -----------------------------------------------------------------------------
TIMEZONE=Europe/Istanbul

# -----------------------------------------------------------------------------
# Device Monitoring
# -----------------------------------------------------------------------------
DEVICE_OFFLINE_THRESHOLD_SECONDS=600
DEVICE_RETRY_INTERVAL_SECONDS=60
DEVICE_MAX_RETRIES=5

# -----------------------------------------------------------------------------
# Snapshot Settings
# -----------------------------------------------------------------------------
SNAPSHOT_INTERVAL_MINUTES=10

# -----------------------------------------------------------------------------
# Spike Filter Settings
# -----------------------------------------------------------------------------
SPIKE_STREAK_THRESHOLD=5
SPIKE_WINDOW_SIZE=5
"""
    
    # Dosyayi yaz
    env_path = Path(__file__).parent / ".env.production"
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    
    # Guvenli bir sekilde yedekle
    backup_path = Path(__file__).parent / ".env.production.backup"
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print("\n" + "="*70)
    print("[OK] Production .env dosyasi basariyla olusturuldu!")
    print("="*70)
    print(f"\n[DOSYA] Dosya konumu: {env_path}")
    print(f"[DOSYA] Yedek konumu: {backup_path}")
    print("\n[UYARI] KRITIK GUVENLIK UYARILARI:")
    print("   1. Bu dosyalari asla git'e commit etmeyin!")
    print("   2. .gitignore dosyasina '.env.production' ekleyin")
    print("   3. Bu dosyalari guvenli bir yerde saklayin")
    print("   4. Production sunucusuna guvenli bir sekilde transfer edin")
    print("   5. SSH key'i remote sunucuya ekleyin:")
    print(f"      ssh-copy-id -i {ssh_key_path} {ssh_user}@{ssh_host}")
    print("\n[BILGI] Database kurulum komutlari:")
    print(f"   CREATE USER {db_user} WITH PASSWORD '{db_password}';")
    print(f"   CREATE DATABASE {db_name} OWNER {db_user};")
    print(f"   GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};")
    print("\n[BILGI] Redis kurulum (sifreli):")
    print(f"   Redis config'e: requirepass {redis_password}")
    print("\n" + "="*70)
    
    # Guvenlik ozeti
    print("\n[KILIT] URETILEN GUVENLIK DEGERLERI (Yedekleme icin):")
    print("-" * 70)
    print(f"JWT_SECRET_KEY:     {jwt_secret}")
    print(f"MQTT_PASSWORD:      {mqtt_password}")
    print(f"DATABASE_PASSWORD:  {db_password}")
    print(f"REDIS_PASSWORD:     {redis_password}")
    print("-" * 70)
    print("\n[UYARI] Bu degerleri guvenli bir yerde saklayin ve bu ciktiyi silin!")
    print("="*70 + "\n")


def check_gitignore():
    """Gitignore dosyasini kontrol eder ve gerekirse ekler"""
    gitignore_path = Path(__file__).parent.parent / ".gitignore"
    
    entries_to_add = [
        "# Production environment files",
        ".env.production",
        ".env.production.backup",
        "backend/.env.production",
        "backend/.env.production.backup",
    ]
    
    if gitignore_path.exists():
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        missing_entries = []
        for entry in entries_to_add:
            if entry not in content:
                missing_entries.append(entry)
        
        if missing_entries:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(missing_entries) + "\n")
            print("[OK] .gitignore dosyasina production dosyalari eklendi")
        else:
            print("[OK] .gitignore dosyasi zaten guncel")
    else:
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("\n".join(entries_to_add) + "\n")
        print("[OK] .gitignore dosyasi olusturuldu")


if __name__ == "__main__":
    import argparse
    
    # Windows encoding fix
    if sys.platform == "win32":
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")
    
    # Argüman parser
    parser = argparse.ArgumentParser(
        description="Sumatic Modern IoT - Production Security Setup Script"
    )
    parser.add_argument(
        "--domain",
        default="sumatic.example.com",
        help="Production domain adresi (default: sumatic.example.com)"
    )
    parser.add_argument(
        "--db-host",
        default="localhost",
        help="PostgreSQL host adresi (default: localhost)"
    )
    parser.add_argument(
        "--db-port",
        default="5432",
        help="PostgreSQL port numarası (default: 5432)"
    )
    parser.add_argument(
        "--db-name",
        default="sumatic_production",
        help="Veritabanı adı (default: sumatic_production)"
    )
    parser.add_argument(
        "--db-user",
        default="sumatic_user",
        help="Veritabanı kullanıcı adı (default: sumatic_user)"
    )
    parser.add_argument(
        "--ssh-host",
        default="31.58.236.246",
        help="SSH tunnel host adresi (default: 31.58.236.246)"
    )
    parser.add_argument(
        "--ssh-user",
        default="sumatic-tunnel",
        help="SSH tunnel kullanıcı adı (default: sumatic-tunnel)"
    )
    parser.add_argument(
        "--ssh-key-path",
        default="/path/to/ssh/private/key",
        help="SSH private key dosya yolu (default: /path/to/ssh/private/key)"
    )
    
    args = parser.parse_args()
    
    print("\n[LOCK] Production Security Setup Script baslatiliyor...\n")
    
    # Gitignore kontrolü
    check_gitignore()
    
    # Production .env oluştur
    create_production_env(
        production_domain=args.domain,
        db_host=args.db_host,
        db_port=args.db_port,
        db_name=args.db_name,
        db_user=args.db_user,
        ssh_host=args.ssh_host,
        ssh_user=args.ssh_user,
        ssh_key_path=args.ssh_key_path
    )
    
    print("\n[OK] Setup tamamlandi! Production deployment için hazirsiniz.")
    print("\n[NOT] Lutfen asagidaki adimlari takip edin:")
    print("1. SSH key-based authentication'i yapilandirin")
    print("2. PostgreSQL veritabanini olusturun")
    print("3. Redis'i sifreli olarak yapilandirin")
    print("4. .env.production dosyasini production sunucuna yükleyin")
    print("5. .env.production dosyasini git'e commit etmeyin!\n")
