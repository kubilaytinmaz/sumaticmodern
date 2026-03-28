# Sumatic Modern IoT Platform

Modern, scalable, and production-ready IoT device monitoring and analytics platform.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00a393?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14.2+-000000?logo=next.js)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql)](https://www.postgresql.org/)
[![TimescaleDB](https://img.shields.io/badge/TimescaleDB-latest-yellow)](https://www.timescale.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://www.docker.com/)

---

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Teknoloji Stack](#-teknoloji-stack)
- [Mimari](#-mimari)
- [Hızlı Başlangıç](#-hızlı-başlangıç)
- [Development Setup](#-development-setup)
- [Production Deployment](#-production-deployment)
- [API Dokümantasyonu](#-api-dokümantasyonu)
- [Kullanım](#-kullanım)
- [Monitoring ve Logging](#-monitoring-ve-logging)
- [Backup ve Recovery](#-backup-ve-recovery)
- [Sorun Giderme](#-sorun-giderme)
- [Katkıda Bulunma](#-katkıda-bulunma)

---

## 🚀 Özellikler

### Core Features
- **Real-time Device Monitoring** - WebSocket ile canlı cihaz durumu takibi
- **Time-Series Analytics** - TimescaleDB ile yüksek performanslı veri analizi
- **MQTT Integration** - IoT cihazlardan veri toplama
- **Modbus Support** - Endüstriyel cihaz entegrasyonu
- **Multi-Device Management** - Birden fazla cihaz yönetimi
- **Advanced Analytics** - Detaylı raporlama ve görselleştirme

### Technical Features
- **Scalable Architecture** - Mikroservis mimarisine uygun
- **Docker Support** - Kolay deployment ve ölçeklendirme
- **RESTful API** - Standart API endpoints
- **WebSocket** - Real-time bidirectional communication
- **Authentication & Authorization** - JWT tabanlı güvenlik
- **Health Checks** - Otomatik servis durumu kontrolü
- **Automated Backups** - PostgreSQL ve Redis backup desteği

---

## 🛠 Teknoloji Stack

### Backend
- **FastAPI** - Modern, hızlı Python web framework
- **PostgreSQL 15** - İlişkisel veritabanı
- **TimescaleDB** - Time-series data optimization
- **Redis** - Caching ve session yönetimi
- **SQLAlchemy 2.0** - ORM
- **Alembic** - Database migrations
- **Paho MQTT** - MQTT client
- **uvicorn** - ASGI server

### Frontend
- **Next.js 14** - React framework
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Recharts** - Data visualization
- **Zustand** - State management
- **Radix UI** - Accessible components

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **Nginx** - Reverse proxy
- **Mosquitto** - MQTT broker
- **Coolify** - Self-hosted deployment platform

---

## 🏗 Mimari

```
┌─────────────────────────────────────────────────────────────┐
│                         NGINX                                │
│                   (Reverse Proxy)                            │
└────────────┬──────────────────────────────┬─────────────────┘
             │                              │
             │                              │
┌────────────▼──────────┐      ┌───────────▼─────────────────┐
│    Next.js Frontend    │      │    FastAPI Backend          │
│    - Dashboard         │      │    - REST API               │
│    - Analytics         │      │    - WebSocket              │
│    - Device Management │      │    - MQTT Consumer          │
└────────────────────────┘      └──────────┬──────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
         ┌──────────▼──────────┐  ┌───────▼────────┐  ┌─────────▼────────┐
         │   PostgreSQL +      │  │     Redis      │  │    Mosquitto     │
         │   TimescaleDB       │  │   (Cache)      │  │   MQTT Broker    │
         └─────────────────────┘  └────────────────┘  └──────────────────┘
                                                                │
                                                     ┌──────────▼──────────┐
                                                     │   IoT Devices       │
                                                     │   (Modbus/MQTT)     │
                                                     └─────────────────────┘
```

Detaylı mimari bilgisi için: [`plans/MODERN_ARCHITECTURE_PLAN.md`](plans/MODERN_ARCHITECTURE_PLAN.md)

---

## ⚡ Hızlı Başlangıç

### Gereksinimler

- Docker 24.0+
- Docker Compose 2.20+
- Git
- (Opsiyonel) Node.js 20+ ve Python 3.11+ (local development için)

### 1. Repository'yi Clone Edin

```bash
git clone https://github.com/yourusername/sumaticmodern.git
cd sumaticmodern
```

### 2. Environment Variables Ayarlayın

```bash
# .env dosyası oluşturun
cp .env.example .env

# Güvenli JWT secret key oluşturun
openssl rand -hex 32

# .env dosyasını düzenleyin ve JWT_SECRET_KEY'i güncelleyin
```

### 3. Docker ile Başlatın

```bash
# Development mode
docker-compose up -d

# İlk kurulumda migration'ları çalıştırın
docker-compose exec backend alembic upgrade head
```

### 4. Uygulamaya Erişin

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MQTT Broker**: localhost:1883 (TCP), localhost:9001 (WebSocket)

### 5. İlk Kullanıcıyı Oluşturun

```bash
# Backend container'a girin
docker-compose exec backend bash

# Admin kullanıcı oluşturun (Python script ile)
python -c "
from app.core.security import get_password_hash
print('admin:', get_password_hash('admin123'))
"
```

---

## 💻 Development Setup

### Backend Development

```bash
cd backend

# Virtual environment oluşturun
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Dependencies yükleyin
pip install -r requirements.txt

# Environment variables ayarlayın
cp .env.example .env

# Database migration
alembic upgrade head

# Development server başlatın
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend

# Dependencies yükleyin
npm install

# Environment variables ayarlayın
cp .env.local.example .env.local

# Development server başlatın
npm run dev
```

### Database Migration

```bash
# Yeni migration oluşturun
docker-compose exec backend alembic revision --autogenerate -m "description"

# Migration uygulayın
docker-compose exec backend alembic upgrade head

# Migration geri alın
docker-compose exec backend alembic downgrade -1
```

---

## 🚀 Production Deployment

### Docker Compose ile Production

```bash
# Production compose file ile başlatın
docker-compose -f docker-compose.prod.yml up -d

# Logları kontrol edin
docker-compose -f docker-compose.prod.yml logs -f
```

### Coolify ile Deployment

Detaylı Coolify deployment rehberi için: [`deployment/coolify/README.md`](deployment/coolify/README.md)

Temel adımlar:
1. Coolify'ı sunucunuza kurun
2. Git repository'nizi bağlayın
3. `docker-compose.prod.yml` dosyasını seçin
4. Environment variables'ı yapılandırın
5. Deploy edin

---

## 📚 API Dokümantasyonu

### Interactive API Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Temel Endpoints

```
POST   /api/v1/auth/login              - Kullanıcı girişi
POST   /api/v1/auth/register           - Yeni kullanıcı kaydı
GET    /api/v1/devices                 - Cihaz listesi
POST   /api/v1/devices                 - Yeni cihaz ekleme
GET    /api/v1/devices/{id}            - Cihaz detayları
GET    /api/v1/readings                - Okuma verileri
GET    /api/v1/analytics/hourly        - Saatlik analitik
WS     /api/v1/ws                      - WebSocket bağlantısı
```

### Authentication

API JWT token ile korunmaktadır:

```bash
# Token alın
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# API isteği yapın
curl -X GET http://localhost:8000/api/v1/devices \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🎯 Kullanım

### 1. Cihaz Ekleme

Dashboard > Devices > "Add Device" butonuna tıklayın ve cihaz bilgilerini girin.

### 2. MQTT Üzerinden Veri Gönderme

```python
import paho.mqtt.client as mqtt
import json

client = mqtt.Client()
client.connect("localhost", 1883)

data = {
    "device_id": "device_001",
    "timestamp": "2024-01-01T12:00:00Z",
    "values": {
        "voltage": 220.5,
        "current": 10.2,
        "power": 2250.1
    }
}

client.publish("Alldatas", json.dumps(data))
```

### 3. Real-time Monitoring

Dashboard'da WebSocket bağlantısı otomatik olarak kurulur ve canlı veri güncellemeleri alırsınız.

---

## 📊 Monitoring ve Logging

### Health Check

```bash
# Tüm servisleri kontrol edin
./deployment/healthcheck.sh

# Manuel health check
curl http://localhost:8000/health
```

### Logs

```bash
# Tüm servis logları
docker-compose logs -f

# Spesifik servis
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Metrics

- PostgreSQL: Connection pooling ve query performance
- Redis: Cache hit/miss ratio ve memory usage
- Backend: Request/response times ve error rates
- MQTT: Message throughput ve connection status

---

## 💾 Backup ve Recovery

### Otomatik Backup

```bash
# Full backup (database + redis + configs)
./deployment/backup.sh --full

# Sadece database
./deployment/backup.sh --db-only

# Retention policy (7 gün)
./deployment/backup.sh --full --retention 7
```

### Recovery

```bash
# PostgreSQL'den geri yükleme
gunzip < backups/2024-01-01/postgres_20240101_120000.sql.gz | \
  docker exec -i sumatic-postgres psql -U sumatic -d sumatic_db

# Redis'ten geri yükleme
docker cp backups/2024-01-01/redis_20240101_120000.rdb \
  sumatic-redis:/data/dump.rdb
docker-compose restart redis
```

---

## 🔧 Sorun Giderme

### Backend Başlamıyor

```bash
# Database bağlantısını kontrol edin
docker-compose exec postgres pg_isready -U sumatic

# Migration durumunu kontrol edin
docker-compose exec backend alembic current

# Logları kontrol edin
docker-compose logs backend
```

### Frontend Derleme Hatası

```bash
# Node modules'ü temizleyin
cd frontend
rm -rf node_modules .next
npm install
npm run build
```

### MQTT Bağlantı Sorunu

```bash
# Mosquitto durumunu kontrol edin
docker-compose exec mqtt mosquitto_sub -t '$SYS/#' -C 1

# Port'ların açık olduğunu kontrol edin
netstat -tuln | grep 1883
```

---

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

---

## 📝 License

Bu proje MIT lisansı altında lisanslanmıştır.

---

## 📞 İletişim

Sorularınız için GitHub Issues kullanabilirsiniz.

---

## 🙏 Acknowledgments

- FastAPI team
- Next.js team
- TimescaleDB team
- Coolify project
