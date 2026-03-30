#!/usr/bin/env python3
"""
Debug script for monthly-stats endpoint.
Tests the query that's causing 500 error.
"""
import asyncio
import sys
from datetime import datetime
from sqlalchemy import select, func, extract
from app.database import async_session_maker
from app.models.device import Device
from app.models.reading import DeviceReading


async def debug_monthly_stats():
    """Debug the monthly stats query."""
    year = 2026
    month = 3
    
    print(f"🔍 Debugging monthly-stats for {year}-{month:02d}")
    print("=" * 60)
    
    async with async_session_maker() as session:
        # Test 1: Get devices
        print("\n1️⃣ Testing device query...")
        try:
            devices_result = await session.execute(
                select(Device).where(Device.is_enabled == True)
            )
            devices = devices_result.scalars().all()
            print(f"   ✅ Found {len(devices)} enabled devices")
            for device in devices:
                print(f"      - Device {device.id}: {device.name or device.device_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Test 2: Get readings for the month
        print("\n2️⃣ Testing readings query...")
        try:
            month_start = datetime(year, month, 1)
            if month == 12:
                month_end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                month_end = datetime(year, month + 1, 1) - timedelta(seconds=1)
            
            print(f"   Month range: {month_start} to {month_end}")
            
            readings_result = await session.execute(
                select(DeviceReading)
                .where(
                    (DeviceReading.timestamp >= month_start) &
                    (DeviceReading.timestamp <= month_end)
                )
                .order_by(DeviceReading.timestamp.asc())
            )
            readings = readings_result.scalars().all()
            print(f"   ✅ Found {len(readings)} readings in month")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test 3: Test EXTRACT query (the problematic one)
        print("\n3️⃣ Testing EXTRACT query...")
        try:
            for device in devices:
                offline_readings_result = await session.execute(
                    select(DeviceReading.timestamp, DeviceReading.status)
                    .where(
                        (DeviceReading.device_id == device.id) &
                        (extract('year', DeviceReading.timestamp) == year) &
                        (extract('month', DeviceReading.timestamp) == month)
                    )
                    .order_by(DeviceReading.timestamp.asc())
                )
                offline_readings = offline_readings_result.all()
                print(f"   ✅ Device {device.id}: {len(offline_readings)} readings")
                
                # Count offline readings
                offline_count = sum(1 for _, status in offline_readings if status and status.lower() == 'offline')
                print(f"      └─ Offline: {offline_count}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test 4: Test with func.extract instead
        print("\n4️⃣ Testing func.extract query...")
        try:
            for device in devices:
                offline_readings_result = await session.execute(
                    select(DeviceReading.timestamp, DeviceReading.status)
                    .where(
                        (DeviceReading.device_id == device.id) &
                        (func.extract('year', DeviceReading.timestamp) == year) &
                        (func.extract('month', DeviceReading.timestamp) == month)
                    )
                    .order_by(DeviceReading.timestamp.asc())
                )
                offline_readings = offline_readings_result.all()
                print(f"   ✅ Device {device.id}: {len(offline_readings)} readings")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Test 5: Check timestamp values
        print("\n5️⃣ Checking timestamp values...")
        try:
            sample_result = await session.execute(
                select(DeviceReading.timestamp, DeviceReading.status)
                .where(DeviceReading.device_id == 1)
                .limit(5)
            )
            samples = sample_result.all()
            print(f"   Sample timestamps:")
            for ts, status in samples:
                print(f"      - {ts} (status: {status})")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
    
    print("\n" + "=" * 60)
    print("✅ All tests passed!")


if __name__ == "__main__":
    from datetime import timedelta
    asyncio.run(debug_monthly_stats())
