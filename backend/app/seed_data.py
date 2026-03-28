"""
Sumatic Modern IoT - Seed Data Script
Populates database with initial test data for development.
"""
import asyncio
import random
from datetime import datetime, timedelta
from pytz import timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.device import Device
from app.models.reading import DeviceReading
from app.models.register_definition import RegisterDefinition
from app.models.user import User
from app.core.security import get_password_hash

# Istanbul timezone
IST = timezone("Europe/Istanbul")


async def seed_register_definitions():
    """Seed register definitions table."""
    async with async_session_maker() as session:
        # Check if already seeded
        result = await session.execute(select(RegisterDefinition))
        if result.scalars().first():
            print("Register definitions already exist, skipping...")
            return

        registers = [
            # FC3 - Holding Registers
            (3, 1000, "Program 1 Cikis Zamani", "uint16", "saniye", "Program 1 çıkış süresi"),
            (3, 1001, "Program 2 Cikis Zamani", "uint16", "saniye", "Program 2 çıkış süresi"),
            (3, 1002, "Program 1 Para Adedi", "uint16", "adet", "Program 1 toplam para adedi"),
            (3, 1003, "Program 2 Para Adedi", "uint16", "adet", "Program 2 toplam para adedi"),
            (3, 1004, "Cikis-3 : Giris 1 Ortak Zaman", "uint16", "saniye", "Çıkış 3 giriş 1 ortak zaman"),
            (3, 1005, "Cikis-3 : Giris 2 Ortak Zaman", "uint16", "saniye", "Çıkış 3 giriş 2 ortak zaman"),
            (3, 1006, "Cihaz Sifresi", "uint16", "", "Cihaz şifresi"),
            (3, 1007, "Modbus Adresi", "uint16", "", "Modbus RTU adresi"),
            (3, 1453, "Acilis Mesaji", "uint16", "", "Açılış mesajı (0=KBO, 1=Sumatic)"),
            # FC4 - Input Registers
            (4, 2000, "Sayac 1", "uint16", "TL", "19 litre sayacı"),
            (4, 2001, "Sayac 2", "uint16", "TL", "5 litre sayacı"),
            (4, 2002, "Cikis-1 Durum", "uint16", "", "Çıkış 1 durumu"),
            (4, 2003, "Cikis-2 Durum", "uint16", "", "Çıkış 2 durumu"),
            (4, 2004, "Acil Ariza Durumu", "uint16", "", "Acil arıza durumu (0=OK, 1=Arıza)"),
            (4, 2005, "Sayac Toplam Low", "uint16", "", "Toplam sayaç düşük 16-bit"),
            (4, 2006, "Sayac Toplam High", "uint16", "", "Toplam sayaç yüksek 16-bit"),
        ]

        for fc, reg, name, data_type, unit, description in registers:
            record = RegisterDefinition(
                fc=fc,
                reg=reg,
                name=name,
                data_type=data_type,
                unit=unit,
                description=description,
            )
            session.add(record)

        await session.commit()
        print(f"Seeded {len(registers)} register definitions")


async def seed_devices():
    """Seed test devices."""
    async with async_session_maker() as session:
        # Check if already seeded
        result = await session.execute(select(Device))
        if result.scalars().first():
            print("Devices already exist, skipping...")
            return

        devices = [
            {
                "device_code": "M1",
                "modem_id": "00001166",
                "device_addr": 1,
                "name": "Makine 1 - Ana Üretim",
                "location": "Üretim Hattı A",
                "method_no": 1,
                "reg_offset_json": {},
                "alias_json": {},
                "skip_raw_json": [],
                "is_enabled": True,
                "is_pending": False,
            },
            {
                "device_code": "M2",
                "modem_id": "00001276",
                "device_addr": 1,
                "name": "Makine 2 - Yan Üretim",
                "location": "Üretim Hattı B",
                "method_no": 1,
                "reg_offset_json": {},
                "alias_json": {},
                "skip_raw_json": [],
                "is_enabled": True,
                "is_pending": False,
            },
            {
                "device_code": "M3",
                "modem_id": "00001186",
                "device_addr": 1,
                "name": "Makine 3 - Test",
                "location": "Test Laboratuvarı",
                "method_no": 1,
                "reg_offset_json": {},
                "alias_json": {},
                "skip_raw_json": [],
                "is_enabled": True,
                "is_pending": False,
            },
            {
                "device_code": "M4",
                "modem_id": "00001186",
                "device_addr": 2,
                "name": "Makine 4 - Test",
                "location": "Test Laboratuvarı",
                "method_no": 1,
                "reg_offset_json": {},
                "alias_json": {},
                "skip_raw_json": [],
                "is_enabled": True,
                "is_pending": False,
            },
        ]

        for device_data in devices:
            device = Device(**device_data)
            session.add(device)

        await session.commit()
        print(f"Seeded {len(devices)} test devices")


async def seed_readings():
    """Seed historical readings for the last 30 days."""
    async with async_session_maker() as session:
        # Check if already seeded
        result = await session.execute(select(DeviceReading))
        if result.scalars().first():
            print("Readings already exist, skipping...")
            return

        # Get devices
        result = await session.execute(select(Device))
        devices = result.scalars().all()

        if not devices:
            print("No devices found, skipping readings seed...")
            return

        now = datetime.now(IST)
        readings_per_device = 720  # ~30 days, hourly readings

        total_readings = 0
        for device in devices:
            # Generate hourly readings for the last 30 days
            for i in range(readings_per_device):
                timestamp = now - timedelta(hours=readings_per_device - i)
                
                # Simulate realistic data with some randomness
                base_counter_19l = 50000 + (i * 50) + random.randint(-10, 20)
                base_counter_5l = 30000 + (i * 30) + random.randint(-5, 15)
                
                # Simulate occasional resets (monthly)
                if timestamp.day <= 3 and i % 24 == 0:
                    base_counter_19l = random.randint(100, 500)
                    base_counter_5l = random.randint(50, 300)

                reading = DeviceReading(
                    device_id=device.id,
                    timestamp=timestamp,
                    counter_19l=base_counter_19l,
                    counter_5l=base_counter_5l,
                    output_1_status=random.choice([0, 1]),
                    output_2_status=random.choice([0, 1]),
                    fault_status=0,  # Mostly online
                    program_1_time=random.randint(0, 300),
                    program_2_time=random.randint(0, 300),
                    program_1_coin_count=random.randint(0, 100),
                    program_2_coin_count=random.randint(0, 100),
                    output3_input1_time=random.randint(0, 600),
                    output3_input2_time=random.randint(0, 600),
                    counter_total_low=base_counter_19l + base_counter_5l,
                    counter_total_high=0,
                    modbus_address=device.device_addr,
                    device_password=1234,
                    raw_data={"source": "seed_data"},
                    is_spike=False,
                )
                session.add(reading)
                total_readings += 1

        await session.commit()
        print(f"Seeded {total_readings} historical readings")


async def seed_admin_user():
    """Seed admin user for testing."""
    async with async_session_maker() as session:
        # Check if already seeded
        result = await session.execute(select(User))
        if result.scalars().first():
            print("Users already exist, skipping...")
            return

        admin = User(
            username="admin",
            email="admin@sumatic.local",
            password_hash=get_password_hash("admin123"),
            full_name="System Administrator",
            role="admin",
            is_active=True,
        )
        session.add(admin)

        await session.commit()
        print("Seeded admin user (username: admin, password: admin123)")


async def main():
    """Main seed function."""
    print("Starting database seeding...")
    print()

    try:
        await seed_register_definitions()
        await seed_devices()
        await seed_readings()
        await seed_admin_user()

        print()
        print("Database seeding completed successfully!")
        print()
        print("Summary:")
        print("  - Register definitions: FC3 (1000-1007, 1453), FC4 (2000-2006)")
        print("  - Test devices: M1, M2, M3")
        print("  - Historical readings: ~30 days per device")
        print("  - Admin user: admin / admin123")
        print()

    except Exception as e:
        print(f"Seeding error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
