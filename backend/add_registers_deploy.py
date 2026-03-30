#!/usr/bin/env python
"""
Deploy ortamında register tanımlarını eklemek için script.
Coolify içinde çalıştırılmalıdır.
"""
import asyncio
import sys
from app.database import async_session_maker
from app.models.register_definition import RegisterDefinition
from sqlalchemy import select


async def add_registers():
    """Register tanımlarını veritabanına ekle."""
    try:
        async with async_session_maker() as session:
            # Mevcut kaydı kontrol et
            result = await session.execute(select(RegisterDefinition))
            existing_regs = result.scalars().all()
            print(f"[INFO] Mevcut register sayısı: {len(existing_regs)}")
            
            if len(existing_regs) > 0:
                print("[INFO] Register tanımları zaten mevcut:")
                for r in existing_regs:
                    print(f"  - fc={r.fc}, reg={r.reg}, name={r.name}")
                return True
            
            # Register tanımlarını ekle
            registers = [
                # Input registers (fc=3) - Read-only
                (3, 100, "Sıcaklık"),
                (3, 101, "Nem"),
                (3, 102, "Basınç"),
                (3, 1000, "Sıcaklık 1"),
                (3, 1001, "Sıcaklık 2"),
                (3, 1002, "Sıcaklık 3"),
                (3, 1003, "Sıcaklık 4"),
                (3, 1004, "Sıcaklık 5"),
                (3, 1005, "Sıcaklık 6"),
                (3, 1006, "Sıcaklık 7"),
                (3, 1007, "Sıcaklık 8"),
                (3, 1453, "Diğer 1"),
                # Holding registers (fc=4) - Read-write
                (4, 2000, "Sayac 1"),
                (4, 2001, "Sayac 2"),
                (4, 2002, "Çıkış-1 Durum"),
                (4, 2003, "Çıkış-2 Durum"),
                (4, 2004, "Acil Arıza Durumu"),
                (4, 2005, "Sayac Toplam Low16"),
                (4, 2006, "Sayac Toplam High16"),
            ]
            
            print(f"[INFO] {len(registers)} register tanımı ekleniyor...")
            for fc, reg, name in registers:
                reg_def = RegisterDefinition(fc=fc, reg=reg, name=name)
                session.add(reg_def)
                print(f"  - fc={fc}, reg={reg}, name={name}")
            
            await session.commit()
            print(f"[SUCCESS] Başarıyla {len(registers)} register tanımı eklendi")
            return True
            
    except Exception as e:
        print(f"[ERROR] Hata oluştu: {str(e)}", file=sys.stderr)
        return False


if __name__ == "__main__":
    result = asyncio.run(add_registers())
    sys.exit(0 if result else 1)
