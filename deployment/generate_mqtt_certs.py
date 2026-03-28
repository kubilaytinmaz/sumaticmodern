#!/usr/bin/env python3
"""
MQTT Broker TLS/SSL Sertifika Oluşturma Script'i
Bu script, MQTT broker için geliştirme/test ortamında kullanılacak
self-signed sertifikalar oluşturur.

PRODUCTION için Let's Encrypt veya commercial CA kullanın.
"""

import os
import subprocess
import sys
from pathlib import Path

# Sertifika dizini
CERT_DIR = Path(__file__).parent.parent / "mqtt-broker" / "certs"
CERT_DIR.mkdir(parents=True, exist_ok=True)

def check_openssl():
    """OpenSSL'in kurulu olup olmadığını kontrol et"""
    try:
        result = subprocess.run(
            ["openssl", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✓ OpenSSL bulundu: {result.stdout.strip()}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print("✗ OpenSSL bulunamadı!")
    print("\nOpenSSL kurulumu için:")
    print("  - Windows: https://slproweb.com/products/Win32OpenSSL.html")
    print("  - Linux: sudo apt-get install openssl (Debian/Ubuntu)")
    print("  - macOS: brew install openssl")
    print("\nAlternatif olarak, production ortamında Let's Encrypt kullanın.")
    return False

def generate_ca_certificate():
    """CA (Certificate Authority) sertifikası oluştur"""
    print("\n[1/4] CA sertifikası oluşturuluyor...")
    
    ca_key = CERT_DIR / "ca.key"
    ca_cert = CERT_DIR / "ca.crt"
    
    # CA private key
    subprocess.run([
        "openssl", "genrsa",
        "-out", str(ca_key),
        "2048"
    ], check=True, capture_output=True)
    
    # CA certificate
    subprocess.run([
        "openssl", "req",
        "-new", "-x509",
        "-days", "365",
        "-key", str(ca_key),
        "-out", str(ca_cert),
        "-subj", "/C=TR/ST=Istanbul/L=Istanbul/O=SumaticModern/CN=SumaticMQTTCA"
    ], check=True, capture_output=True)
    
    print(f"✓ CA sertifikası oluşturuldu: {ca_cert}")
    return True

def generate_server_certificate():
    """MQTT broker için server sertifikası oluştur"""
    print("\n[2/4] Server sertifikası oluşturuluyor...")
    
    ca_key = CERT_DIR / "ca.key"
    ca_cert = CERT_DIR / "ca.crt"
    server_key = CERT_DIR / "mqtt-server.key"
    server_csr = CERT_DIR / "mqtt-server.csr"
    server_cert = CERT_DIR / "mqtt-server.crt"
    
    # Server private key
    subprocess.run([
        "openssl", "genrsa",
        "-out", str(server_key),
        "2048"
    ], check=True, capture_output=True)
    
    # Server CSR (Certificate Signing Request)
    subprocess.run([
        "openssl", "req",
        "-new",
        "-key", str(server_key),
        "-out", str(server_csr),
        "-subj", "/C=TR/ST=Istanbul/L=Istanbul/O=SumaticModern/CN=localhost"
    ], check=True, capture_output=True)
    
    # SAN (Subject Alternative Names) config dosyası oluştur
    san_config = CERT_DIR / "san.cnf"
    san_config.write_text("""[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = TR
ST = Istanbul
L = Istanbul
O = SumaticModern
CN = localhost

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.local
IP.1 = 127.0.0.1
IP.2 = ::1
""")
    
    # Server certificate (CA ile imzalanmış)
    subprocess.run([
        "openssl", "x509",
        "-req",
        "-in", str(server_csr),
        "-CA", str(ca_cert),
        "-CAkey", str(ca_key),
        "-CAcreateserial",
        "-out", str(server_cert),
        "-days", "365",
        "-sha256",
        "-extfile", str(san_config),
        "-extensions", "v3_req"
    ], check=True, capture_output=True)
    
    # CSR dosyasını temizle
    server_csr.unlink()
    san_config.unlink()
    
    print(f"✓ Server sertifikası oluşturuldu: {server_cert}")
    return True

def generate_client_certificate():
    """MQTT client'ları için client sertifikası oluştur"""
    print("\n[3/4] Client sertifikası oluşturuluyor...")
    
    ca_key = CERT_DIR / "ca.key"
    ca_cert = CERT_DIR / "ca.crt"
    client_key = CERT_DIR / "mqtt-client.key"
    client_csr = CERT_DIR / "mqtt-client.csr"
    client_cert = CERT_DIR / "mqtt-client.crt"
    
    # Client private key
    subprocess.run([
        "openssl", "genrsa",
        "-out", str(client_key),
        "2048"
    ], check=True, capture_output=True)
    
    # Client CSR
    subprocess.run([
        "openssl", "req",
        "-new",
        "-key", str(client_key),
        "-out", str(client_csr),
        "-subj", "/C=TR/ST=Istanbul/L=Istanbul/O=SumaticModern/CN=MQTTClient"
    ], check=True, capture_output=True)
    
    # Client certificate (CA ile imzalanmış)
    subprocess.run([
        "openssl", "x509",
        "-req",
        "-in", str(client_csr),
        "-CA", str(ca_cert),
        "-CAkey", str(ca_key),
        "-CAcreateserial",
        "-out", str(client_cert),
        "-days", "365",
        "-sha256"
    ], check=True, capture_output=True)
    
    # CSR dosyasını temizle
    client_csr.unlink()
    
    print(f"✓ Client sertifikası oluşturuldu: {client_cert}")
    return True

def set_permissions():
    """Sertifika dosyalarının izinlerini ayarla"""
    print("\n[4/4] Dosya izinleri ayarlanıyor...")
    
    # Private key'leri sadece sahibi okuyabilmeli
    for key_file in CERT_DIR.glob("*.key"):
        # Windows'ta chmod çalışmayabilir, hata yoksay
        try:
            os.chmod(key_file, 0o600)
        except Exception:
            pass
    
    print("✓ Dosya izinleri ayarlandı")
    return True

def print_summary():
    """Özet bilgileri yazdır"""
    print("\n" + "="*60)
    print("MQTT TLS SERTİKALARI BAŞARIYLA OLUŞTURULDU")
    print("="*60)
    print(f"\nSertifika dizini: {CERT_DIR}")
    print("\nOluşturulan dosyalar:")
    print("  - ca.crt           : CA sertifikası (public)")
    print("  - ca.key           : CA private key (GİZLİ)")
    print("  - mqtt-server.crt  : Server sertifikası (public)")
    print("  - mqtt-server.key  : Server private key (GİZLİ)")
    print("  - mqtt-client.crt  : Client sertifikası (public)")
    print("  - mqtt-client.key  : Client private key (GİZLİ)")
    
    print("\n" + "!"*60)
    print("ÖNEMLİ GÜVENLİK UYARISI")
    print("!"*60)
    print("Bu sertifikalar SADECE geliştirme/test ortamı içindir.")
    print("Production ortamında mutlaka şu yöntemleri kullanın:")
    print("  1. Let's Encrypt (ücretsiz, otomatik yenileme)")
    print("  2. Commercial CA (Symantec, DigiCert, etc.)")
    print("  3. Kurum internal CA'sı")
    print("\nCA private key (ca.key) asla paylaşılmamalıdır!")
    print("="*60)

def main():
    """Ana fonksiyon"""
    print("="*60)
    print("MQTT Broker TLS/SSL Sertifika Oluşturma")
    print("="*60)
    
    # OpenSSL kontrolü
    if not check_openssl():
        sys.exit(1)
    
    try:
        # Sertifikaları oluştur
        generate_ca_certificate()
        generate_server_certificate()
        generate_client_certificate()
        set_permissions()
        print_summary()
        
        return 0
        
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Hata: Sertifika oluşturma başarısız oldu")
        print(f"Komut: {e.cmd}")
        print(f"Return code: {e.returncode}")
        return 1
    except Exception as e:
        print(f"\n✗ Beklenmeyen hata: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
