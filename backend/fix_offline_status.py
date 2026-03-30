#!/usr/bin/env python3
"""
Fix PostgreSQL status values by reading actual status from SQLite.

The migration script calculated status based on counter values, but
SQLite already had correct status values that should be preserved.
This script:
1. Reads all offline readings from SQLite
2. Updates corresponding PostgreSQL records to 'offline'
"""
import asyncio
import sqlite3
import sys
import os
sys.path.insert(0, '/app')

from app.database import async_session_maker
from sqlalchemy import text


async def fix_status():
    # Connect to SQLite
    sqlite_path = '/app/sumatic_modern.db'
    if not os.path.exists(sqlite_path):
        print(f"ERROR: SQLite file not found at {sqlite_path}")
        return
    
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_cur = sqlite_conn.cursor()
    
    # Get all device mappings first
    sqlite_cur.execute("SELECT id, device_code FROM devices")
    devices = {row[0]: row[1] for row in sqlite_cur.fetchall()}
    print(f"Found {len(devices)} devices in SQLite: {devices}")
    
    # Get all offline readings from SQLite (including those with counter values)
    sqlite_cur.execute("""
        SELECT device_id, timestamp 
        FROM device_readings 
        WHERE status='offline'
        AND (counter_19l IS NOT NULL OR counter_5l IS NOT NULL)
    """)
    offline_with_counters = sqlite_cur.fetchall()
    print(f"\nFound {len(offline_with_counters)} offline readings WITH counter values in SQLite")
    
    sqlite_conn.close()
    
    if not offline_with_counters:
        print("No offline readings with counters found - nothing to fix!")
        return
    
    # Now update PostgreSQL
    async with async_session_maker() as session:
        # Check current status distribution
        r = await session.execute(text("SELECT status, COUNT(*) FROM device_readings GROUP BY status"))
        print("\nBefore fix:")
        for row in r.fetchall():
            print(f"  status='{row[0]}', count={row[1]}")
        
        # Build device_code to id mapping from PostgreSQL
        r = await session.execute(text("SELECT id, device_code FROM devices"))
        pg_devices = {row[1]: row[0] for row in r.fetchall()}
        print(f"\nPostgreSQL devices: {pg_devices}")
        
        # We need to match by timestamp since device_id might differ
        # SQLite device_id 1 -> device_code 'M1' -> PostgreSQL id
        # Build SQLite device_id to PostgreSQL id mapping
        sqlite_conn2 = sqlite3.connect(sqlite_path)
        sqlite_cur2 = sqlite_conn2.cursor()
        sqlite_cur2.execute("SELECT id, device_code FROM devices")
        sqlite_devices = {row[0]: row[1] for row in sqlite_cur2.fetchall()}
        print(f"\nSQLite device_code mapping: {sqlite_devices}")
        sqlite_conn2.close()
        
        # Map SQLite device_id to PostgreSQL device_id
        device_id_map = {}
        for sqlite_id, device_code in sqlite_devices.items():
            if device_code in pg_devices:
                device_id_map[sqlite_id] = pg_devices[device_code]
        print(f"\nDevice ID mapping (SQLite -> PostgreSQL): {device_id_map}")
        
        # Update status for offline readings with counters
        updated = 0
        for sqlite_device_id, timestamp_str in offline_with_counters:
            pg_device_id = device_id_map.get(sqlite_device_id)
            if pg_device_id is None:
                continue
            
            # Normalize timestamp
            ts = timestamp_str.replace('T', ' ').strip()
            
            result = await session.execute(text("""
                UPDATE device_readings 
                SET status = 'offline'
                WHERE device_id = :device_id 
                AND timestamp::text LIKE :ts_pattern
                AND status != 'offline'
            """), {"device_id": pg_device_id, "ts_pattern": ts[:16] + "%"})
            updated += result.rowcount
        
        await session.commit()
        print(f"\nUpdated {updated} rows to 'offline'")
        
        # Check after fix
        r = await session.execute(text("SELECT status, COUNT(*) FROM device_readings GROUP BY status"))
        print("\nAfter fix:")
        for row in r.fetchall():
            print(f"  status='{row[0]}', count={row[1]}")


if __name__ == "__main__":
    asyncio.run(fix_status())
