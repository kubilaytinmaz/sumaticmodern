#!/usr/bin/env python3
"""
Sumatic Modern IoT - Admin Password Change Script

Bu script ile admin kullanıcısının şifresini değiştirebilirsiniz.
Kullanım: python change_admin_password.py <yeni_sifre>
"""
import asyncio
import sys
from pathlib import Path

# Proje dizinini Python path'ine ekle
sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session_maker
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy import select


async def change_admin_password(new_password: str) -> bool:
    """
    Admin kullanıcısının şifresini değiştir.

    Args:
        new_password: Yeni şifre

    Returns:
        bool: İşlem başarılı ise True
    """
    async with async_session_maker() as session:
        # Admin kullanıcısını bul
        result = await session.execute(
            select(User).where(User.username == 'admin')
        )
        admin = result.scalar_one_or_none()

        if not admin:
            print("❌ Hata: Admin kullanıcısı bulunamadı!")
            print("   İlk kez kurulum yapıyorsanız, backend'i başlatın.")
            print("   Backend otomatik olarak admin kullanıcısı oluşturacaktır.")
            return False

        # Şifreyi güncelle
        admin.password_hash = get_password_hash(new_password)
        await session.commit()

        print(f"✅ Admin şifresi başarıyla güncellendi!")
        print(f"   Kullanıcı adı: {admin.username}")
        print(f"   E-posta: {admin.email}")
        print(f"   Rol: {admin.role}")
        return True


async def main():
    if len(sys.argv) < 2:
        print("Kullanım: python change_admin_password.py <yeni_sifre>")
        print("\nÖrnek:")
        print("  python change_admin_password.py GucluSifre123!")
        print("\nAlternatif: Environment variable ile")
        print("  ADMIN_PASSWORD='GucluSifre123!' python change_admin_password.py")
        sys.exit(1)

    new_password = sys.argv[1]

    # Şifre güvenlik kontrolü
    if len(new_password) < 8:
        print("⚠️  Uyarı: Şifre en az 8 karakter olmalıdır!")
        confirm = input("Yine de devam etmek istiyor musunuz? (e/h): ")
        if confirm.lower() != 'e':
            print("İptal edildi.")
            sys.exit(0)

    print(f"\n{'='*50}")
    print("Sumatic Modern IoT - Admin Şifre Değiştirme")
    print(f"{'='*50}\n")

    success = await change_admin_password(new_password)

    if success:
        print(f"\n{'='*50}")
        print("Artık yeni şifreniz ile giriş yapabilirsiniz:")
        print(f"  URL: http://46.225.231.44:3001/login")
        print(f"  Kullanıcı adı: admin")
        print(f"  Şifre: {new_password}")
        print(f"{'='*50}\n")
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
