#!/usr/bin/env python3
"""Debug offline hours calculation - run this in backend container"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.database import async_session_maker
from sqlalchemy import text
from datetime import datetime


async def debug():
    async with async_session_maker() as session:
        # 1. Check status distribution
        r = await session.execute(text("SELECT status, COUNT(*) FROM device_readings GROUP BY status"))
        print("=== Status Distribution ===")
        for row in r.fetchall():
            print(f"  status='{row[0]}', count={row[1]}")
        
        # 2. Check offline readings specifically
        r2 = await session.execute(text("""
            SELECT COUNT(*) FROM device_readings 
            WHERE LOWER(status) = 'offline'
        """))
        offline_count = r2.scalar()
        print(f"\n=== Offline readings (case-insensitive): {offline_count} ===")
        
        # 3. Check March 2026 readings
        r3 = await session.execute(text("""
            SELECT device_id, timestamp, status
            FROM device_readings
            WHERE timestamp >= '2026-03-01' AND timestamp <= '2026-03-31 23:59:59'
            ORDER BY timestamp ASC
            LIMIT 20
        """))
        print("\n=== March 2026 readings (first 20) ===")
        for row in r3.fetchall():
            print(f"  device_id={row[0]}, timestamp={row[1]}, status='{row[2]}'")
        
        # 4. Check if there are any offline readings in March 2026
        r4 = await session.execute(text("""
            SELECT COUNT(*) FROM device_readings
            WHERE timestamp >= '2026-03-01' AND timestamp <= '2026-03-31 23:59:59'
            AND LOWER(status) = 'offline'
        """))
        march_offline = r4.scalar()
        print(f"\n=== March 2026 offline readings: {march_offline} ===")
        
        # 5. Sample offline reading with context
        r5 = await session.execute(text("""
            SELECT device_id, timestamp, status, counter_19l, counter_5l
            FROM device_readings
            WHERE LOWER(status) = 'offline'
            ORDER BY timestamp DESC
            LIMIT 5
        """))
        print("\n=== Latest 5 offline readings ===")
        for row in r5.fetchall():
            print(f"  device={row[0]}, time={row[1]}, status='{row[2]}', 19l={row[3]}, 5l={row[4]}")


if __name__ == "__main__":
    asyncio.run(debug())
