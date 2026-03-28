# Sumatic Modern - IoT Su Otomatı Ciro Takip Sistemi

Modern, ölçeklenebilir ve gerçek zamanlı IoT su otomatı ciro takip ve analiz platformu.

## 🚀 Teknolojiler

### Backend
- **FastAPI** - Modern, hızlı Python web framework
- **PostgreSQL + TimescaleDB** - Zaman serisi verileri için optimize edilmiş veritabanı
- **Redis** - Cache ve session yönetimi
- **MQTT** - IoT cihaz iletişimi
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations

### Frontend
- **Next.js 14** - React framework (App Router)
- **TypeScript** - Type-safe development
- **TailwindCSS** - Utility-first CSS framework
- **Shadcn/ui** - Modern UI components
- **Recharts** - Grafikler
- **Zustand** - State management
- **Lucide React** - Icons

## 📋 Özellikler

- ✅ Gerçek zamanlı cihaz izleme (WebSocket)
- ✅ Saatlik/Günlük/Haftalık/Aylık analiz raporları
- ✅ Cihaz durum takibi (Online/Offline)
- ✅ Spike filtreleme ve veri validasyonu
- ✅ Çoklu kullanıcı desteği (Admin/User/Viewer rolleri)
- ✅ Modern dark theme UI
- ✅ Responsive design (mobil uyumlu)
- ✅ JWT authentication
- ✅ MQTT protocol desteği

## 🛠️ Kurulum

### Backend Kurulumu

```bash
cd backend

# Virtual environment oluştur
python -m venv venv
source venv/bin/activate  # Linux/Mac
# veya
venv\Scripts\activate  # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# .env dosyasını düzenle

# Database migration
alembic upgrade head

# Uygulamayı başlat
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Kurulumu

```bash
cd frontend

# Bağımlılıkları yükle
npm install

# Environment variables
cp .env.local.example .env.local
# .env.local dosyasını düzenle

# Development server başlat
npm run dev
```

## 🔧 Konfigürasyon

### Backend Environment Variables

```env
DATABASE_URL=postgresql://user:password@localhost/sumatic_db
REDIS_URL=redis://localhost:6379
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=consumer
MQTT_PASSWORD=password
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Frontend Environment Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Giriş yap
- `POST /api/v1/auth/logout` - Çıkış yap
- `GET /api/v1/auth/me` - Mevcut kullanıcı bilgisi

### Devices
- `GET /api/v1/devices` - Tüm cihazları listele
- `POST /api/v1/devices` - Yeni cihaz ekle
- `GET /api/v1/devices/{id}` - Cihaz detayı
- `PUT /api/v1/devices/{id}` - Cihaz güncelle
- `DELETE /api/v1/devices/{id}` - Cihaz sil

### Analytics
- `GET /api/v1/analytics/revenue` - Gelir analizi
- `GET /api/v1/dashboard/overview` - Dashboard özet

### WebSocket
- `WS /api/v1/ws` - Gerçek zamanlı güncellemeler

## 📦 Deployment

### Docker ile Deployment

```bash
# Backend
cd backend
docker build -t sumatic-backend .
docker run -p 8000:8000 sumatic-backend

# Frontend
cd frontend
docker build -t sumatic-frontend .
docker run -p 3000:3000 sumatic-frontend
```

### Coolify Deployment

1. Coolify dashboard'a giriş yap
2. Yeni proje oluştur
3. Git repository'yi bağla
4. Environment variables'ı ayarla
5. Deploy et

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📚 Dokümantasyon

- **API Docs:** http://localhost:8000/docs (Swagger UI)
- **ReDoc:** http://localhost:8000/redoc
- **Architecture:** `plans/MODERN_ARCHITECTURE_PLAN.md`

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'feat: Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 👥 İletişim

Sorularınız için: [email@example.com]

## 🙏 Teşekkürler

- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/)
- [Shadcn/ui](https://ui.shadcn.com/)
- [TimescaleDB](https://www.timescale.com/)
