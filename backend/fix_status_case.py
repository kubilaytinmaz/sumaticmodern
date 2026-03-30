#!/usr/bin/env python3
"""Fix status case: ONLINE/OFFLINE/PARTIAL -> online/offline/partial"""
import asyncio
import sys
sys.path.insert(0, '/app')

from app.database import async_session_maker
from sqlalchemy import text


async def fix():
    async with async_session_maker() as session:
        # Check current status values
        r = await session.execute(text("SELECT status, COUNT(*) FROM device_readings GROUP BY status"))
        print("Before:")
        for row in r.fetchall():
            print(f"  status='{row[0]}', count={row[1]}")
        
        # Fix case: uppercase to lowercase
        result = await session.execute(text(
            "UPDATE device_readings SET status = LOWER(status) WHERE status IN ('ONLINE','OFFLINE','PARTIAL')"
        ))
        await session.commit()
        print(f"\nUpdated {result.rowcount} rows")
        
        # Verify
        r2 = await session.execute(text("SELECT status, COUNT(*) FROM device_readings GROUP BY status"))
        print("\nAfter:")
        for row in r2.fetchall():
            print(f"  status='{row[0]}', count={row[1]}")
        
        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(fix())
