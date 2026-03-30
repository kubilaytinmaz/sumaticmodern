#!/usr/bin/env python3
"""Update last_seen_at for all devices from their latest reading."""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.database import async_session_maker
from sqlalchemy import text


async def update_last_seen():
    async with async_session_maker() as session:
        # Update each device's last_seen_at from their latest reading
        result = await session.execute(text("""
            UPDATE devices 
            SET last_seen_at = (
                SELECT MAX(timestamp) 
                FROM device_readings 
                WHERE device_readings.device_id = devices.id
            )
            WHERE id IN (SELECT DISTINCT device_id FROM device_readings)
            RETURNING id, device_code, last_seen_at
        """))
        
        updated = result.fetchall()
        await session.commit()
        
        print(f"\n✅ Updated {len(updated)} devices:")
        for row in updated:
            print(f"  {row[1]}: last_seen_at = {row[2]}")
        
        # Verify
        r2 = await session.execute(text('SELECT id, device_code, last_seen_at FROM devices'))
        print(f"\n📊 All devices after update:")
        for row in r2.fetchall():
            print(f"  {row[1]}: last_seen_at = {row[2]}")


if __name__ == "__main__":
    asyncio.run(update_last_seen())
