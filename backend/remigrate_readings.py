#!/usr/bin/env python3
"""
Reset and remigrate device readings from SQLite to PostgreSQL.
This script:
1. Deletes all existing device_readings from PostgreSQL
2. Re-migrates from SQLite preserving original status values
"""
import asyncio
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session_maker
from sqlalchemy import text

POSSIBLE_PATHS = [
    Path("/app/sumatic_modern.db"),
    Path("/app/backend/sumatic_modern.db"),
]

SQLITE_DB_PATH = None
for path in POSSIBLE_PATHS:
    if path.exists():
        SQLITE_DB_PATH = path
        break


async def remigrate():
    if not SQLITE_DB_PATH:
        print("ERROR: SQLite file found!")
        return

    print(f"Using SQLite: {SQLITE_DB_PATH}")
    
    # Try to make SQLite file writable by copying it
    import shutil
    import os
    
    writable_path = "/tmp/sumatic_modern_copy.db"
    try:
        shutil.copy2(SQLITE_DB_PATH, writable_path)
        print(f"Copied SQLite to writable location: {writable_path}")
        sqlite_conn = sqlite3.connect(writable_path)
    except Exception as e:
        print(f"Could not copy SQLite file: {e}")
        # Try direct connection anyway
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    # Get device code -> id mapping from SQLite
    sqlite_cur.execute("SELECT id, device_code FROM devices")
    sqlite_devices = {row['id']: row['device_code'] for row in sqlite_cur.fetchall()}
    print(f"SQLite devices: {sqlite_devices}")
    
    # Get all readings from SQLite with original status
    sqlite_cur.execute("""
        SELECT device_id, timestamp, counter_19l, counter_5l, status
        FROM device_readings
        ORDER BY timestamp ASC
    """)
    all_readings = sqlite_cur.fetchall()
    print(f"Total SQLite readings: {len(all_readings)}")
    
    # Count by status
    status_counts = {}
    for r in all_readings:
        s = r['status'] or 'None'
        status_counts[s] = status_counts.get(s, 0) + 1
    print(f"SQLite status distribution: {status_counts}")
    
    sqlite_conn.close()
    
    async with async_session_maker() as session:
        # Get PostgreSQL device mapping
        r = await session.execute(text("SELECT id, device_code FROM devices"))
        pg_devices = {row[1]: row[0] for row in r.fetchall()}
        print(f"PostgreSQL devices: {pg_devices}")
        
        # Build device_id mapping: SQLite device_id -> PG device_id
        device_id_map = {}
        for sqlite_id, device_code in sqlite_devices.items():
            if device_code in pg_devices:
                device_id_map[sqlite_id] = pg_devices[device_code]
        print(f"Device ID map: {device_id_map}")
        
        # Check current PG status before
        r = await session.execute(text("SELECT status, COUNT(*) FROM device_readings GROUP BY status"))
        print("\nPostgreSQL BEFORE:")
        for row in r.fetchall():
            print(f"  status='{row[0]}', count={row[1]}")
        
        # Delete all existing readings
        r = await session.execute(text("DELETE FROM device_readings"))
        deleted = r.rowcount
        await session.commit()
        print(f"\nDeleted {deleted} existing readings from PostgreSQL")
        
        # Re-insert with correct status values
        batch_size = 1000
        batch = []
        inserted = 0
        
        for reading in all_readings:
            sqlite_device_id = reading['device_id']
            pg_device_id = device_id_map.get(sqlite_device_id)
            if pg_device_id is None:
                continue
            
            # Parse timestamp
            ts_str = reading['timestamp']
            try:
                if isinstance(ts_str, str):
                    ts_str = ts_str.replace('T', ' ').replace('Z', '').strip()
                    ts = datetime.fromisoformat(ts_str)
                else:
                    ts = datetime.utcnow()
            except:
                ts = datetime.utcnow()
            
            # Use ORIGINAL status from SQLite
            original_status = reading['status']
            if original_status:
                status = original_status.lower()
            elif reading['counter_19l'] is not None and reading['counter_5l'] is not None:
                status = 'online'
            elif reading['counter_19l'] is None and reading['counter_5l'] is None:
                status = 'offline'
            else:
                status = 'partial'
            
            batch.append({
                'device_id': pg_device_id,
                'timestamp': ts,
                'counter_19l': reading['counter_19l'],
                'counter_5l': reading['counter_5l'],
                'status': status,
            })
            
            if len(batch) >= batch_size:
                await session.execute(
                    text("""
                        INSERT INTO device_readings (device_id, timestamp, counter_19l, counter_5l, status)
                        VALUES (:device_id, :timestamp, :counter_19l, :counter_5l, :status)
                    """),
                    batch
                )
                await session.flush()
                inserted += len(batch)
                batch = []
                print(f"  Inserted {inserted}/{len(all_readings)}...", end='\r')
        
        # Insert remaining
        if batch:
            await session.execute(
                text("""
                    INSERT INTO device_readings (device_id, timestamp, counter_19l, counter_5l, status)
                    VALUES (:device_id, :timestamp, :counter_19l, :counter_5l, :status)
                """),
                batch
            )
            inserted += len(batch)
        
        await session.commit()
        print(f"\nInserted {inserted} readings into PostgreSQL")
        
        # Check after
        r = await session.execute(text("SELECT status, COUNT(*) FROM device_readings GROUP BY status"))
        print("\nPostgreSQL AFTER:")
        for row in r.fetchall():
            print(f"  status='{row[0]}', count={row[1]}")
        
        # Verify offline count per device
        r = await session.execute(text("""
            SELECT device_id, COUNT(*) 
            FROM device_readings WHERE status='offline'
            GROUP BY device_id ORDER BY device_id
        """))
        print("\nOffline per device:")
        for row in r.fetchall():
            print(f"  device_id={row[0]}, offline={row[1]}")


if __name__ == "__main__":
    print("=== Re-migrating device readings with correct status values ===")
    asyncio.run(remigrate())
    print("\nDone!")
