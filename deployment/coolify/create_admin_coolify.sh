#!/bin/bash
# ==============================================================================
# Sumatic Modern IoT - Coolify Admin User Creation Script
# ==============================================================================
# Bu script Coolify deployment sonrası admin kullanıcısı oluşturur.
# ==============================================================================

set -e

# Renkli çıktı
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}  Sumatic Modern IoT - Admin Kullanıcı Oluşturma${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""

# Environment variables kontrolü
if [ -z "$ADMIN_USERNAME" ]; then
    echo -e "${YELLOW}ADMIN_USERNAME tanımlı değil, varsayılan 'admin' kullanılıyor${NC}"
    ADMIN_USERNAME="admin"
fi

if [ -z "$ADMIN_EMAIL" ]; then
    echo -e "${YELLOW}ADMIN_EMAIL tanımlı değil, varsayılan 'admin@sumatic.io' kullanılıyor${NC}"
    ADMIN_EMAIL="admin@sumatic.io"
fi

if [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${RED}HATA: ADMIN_PASSWORD environment variable tanımlı değil!${NC}"
    echo -e "${YELLOW}Kullanım: export ADMIN_PASSWORD='GüvenliŞifre123!'${NC}"
    exit 1
fi

echo -e "${GREEN}Admin Kullanıcı Bilgileri:${NC}"
echo "  Username: ${ADMIN_USERNAME}"
echo "  Email: ${ADMIN_EMAIL}"
echo "  Password: ******** (gizli)"
echo ""

# Backend container'ına bağlan ve admin oluştur
echo -e "${GREEN}Backend container'ına bağlanılıyor...${NC}"

# Docker container kontrolü
BACKEND_CONTAINER=$(docker ps --filter "name=sumatic-backend" --format "{{.Names}}" | head -n 1)

if [ -z "$BACKEND_CONTAINER" ]; then
    echo -e "${RED}HATA: Backend container bulunamadı!${NC}"
    echo -e "${YELLOW}Container'ları listelemek için: docker ps${NC}"
    exit 1
fi

echo -e "${GREEN}Bulunan container: ${BACKEND_CONTAINER}${NC}"
echo ""

# Python script'i oluştur ve çalıştır
docker exec -i ${BACKEND_CONTAINER} python3 << EOF
import asyncio
from app.database import async_session_maker, init_db
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_admin():
    """Create admin user if not exists."""
    try:
        # Initialize tables
        await init_db()
        
        async with async_session_maker() as session:
            # Check if admin already exists
            result = await session.execute(
                select(User).where(User.username == "${ADMIN_USERNAME}")
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"✓ Admin kullanıcı zaten mevcut (id={existing.id})")
                print(f"  Username: {existing.username}")
                print(f"  Email: {existing.email}")
                return
            
            # Create admin user
            admin = User(
                username="${ADMIN_USERNAME}",
                email="${ADMIN_EMAIL}",
                password_hash=get_password_hash("${ADMIN_PASSWORD}"),
                full_name="Admin User",
                role="admin",
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            
            print(f"✓ Admin kullanıcı başarıyla oluşturuldu!")
            print(f"  ID: {admin.id}")
            print(f"  Username: {admin.username}")
            print(f"  Email: {admin.email}")
            print(f"  Role: {admin.role}")
            print(f"  Active: {admin.is_active}")
            
    except Exception as e:
        print(f"✗ Hata: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(create_admin())
EOF

echo ""
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}  İşlem Tamamlandı!${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""
echo -e "${YELLOW}Giriş Bilgileri:${NC}"
echo "  URL: https://your-domain.com/login"
echo "  Username: ${ADMIN_USERNAME}"
echo "  Password: (Belirlediğiniz şifre)"
echo ""
echo -e "${RED}ÖNEMLİ: İlk girişten sonra şifrenizi değiştirin!${NC}"
echo ""
