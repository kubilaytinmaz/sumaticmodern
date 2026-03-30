#!/usr/bin/env python3
"""
Sumatic Modern IoT - SQLite to PostgreSQL Migration Script
Migrates data from sumatic_modern.db (SQLite) to PostgreSQL database.

Usage:
    1. Upload sumatic_modern.db to backend container
    2. Run: python migrate_sqlite_to_postgresql.py

Requirements:
    - sumatic_modern.db in the backend directory
    - PostgreSQL connection configured via DATABASE_URL
"""
import asyncio
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session_maker, engine
from app.models.device import Device
from app.models.reading import DeviceReading
from app.models.user import User
from app.core.security import get_password_hash


SQLITE_DB_PATH = Path(__file__).parent / "sumatic_modern.db"

# Device mapping from old system
DEVICE_MAPPING = {
    "m1": {"device_code": "M1", "name": "Merkez Cihaz 1", "modem_id": "00001276", "device_addr": 1},
    "m2": {"device_code": "M2", "name": "Merkez Cihaz 2", "modem_id": "00001276", "device_addr": 2},
    "m3": {"device_code": "M3", "name": "Merkez Cihaz 3", "modem_id": "00001276", "device_addr": 3},
    "m4": {"device_code": "M4", "name": "Merkez Cihaz 4", "modem_id": "00001276", "device_addr": 4},
}


async def check_postgresql_connection():
    """Check if PostgreSQL is accessible."""
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        print("✅ PostgreSQL connection successful")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False


def check_sqlite_file():
    """Check if SQLite file exists."""
    if not SQLITE_DB_PATH.exists():
        print(f"❌ SQLite database not found: {SQLITE_DB_PATH}")
        print(f"\nPlease upload sumatic_modern.db to: {SQLITE_DB_PATH.parent}")
        return False
    print(f"✅ SQLite database found: {SQLITE_DB_PATH}")
    return True


def get_sqlite_stats():
    """Get statistics from SQLite database."""
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    cur = conn.cursor()
    
    stats = {}
    
    # Get table names
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cur.fetchall()]
    
    for table in tables:
        try:
            cur.execute(f'SELECT COUNT(*) FROM "{table}"')
            count = cur.fetchone()[0]
            stats[table] = count
        except Exception as e:
            stats[table] = f"Error: {e}"
    
    conn.close()
    return stats


async def migrate_devices(session: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Migrate devices from SQLite to PostgreSQL."""
    print("\n📦 Migrating devices...")
    
    cur = sqlite_conn.cursor()
    cur.execute("SELECT * FROM devices ORDER BY id")
    rows = cur.fetchall()
    
    if not rows:
        print("  ⚠️  No devices found in SQLite")
        return 0
    
    # Get column names
    cur.execute("PRAGMA table_info(devices)")
    columns = [r[1] for r in cur.fetchall()]
    
    migrated = 0
    for row in rows:
        data = dict(zip(columns, row))
        
        # Check if device already exists
        result = await session.execute(
            select(Device).where(Device.device_code == data.get('device_code'))
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"  ⏭️  Device {data.get('device_code')} already exists, skipping")
            continue
        
        # Create device
        device = Device(
            device_code=data.get('device_code'),
            modem_id=data.get('modem_id') or '00001276',
            device_addr=data.get('device_addr') or 1,
            name=data.get('name') or f"Device {data.get('device_code')}",
            location=data.get('location'),
            method_no=data.get('method_no') or 0,
            is_enabled=bool(data.get('is_enabled', 1)),
            is_pending=bool(data.get('is_pending', 0)),
            reg_offset_json=data.get('reg_offset_json') or {},
            alias_json=data.get('alias_json') or {},
            skip_raw_json=data.get('skip_raw_json') or [],
            device_meta=data.get('device_meta') or {},
        )
        
        session.add(device)
        migrated += 1
        print(f"  ✅ Migrated device: {device.device_code}")
    
    await session.commit()
    print(f"\n  📊 Total devices migrated: {migrated}")
    return migrated


async def migrate_readings(session: AsyncSession, sqlite_conn: sqlite3.Connection):
    """Migrate device readings from SQLite to PostgreSQL."""
    print("\n📊 Migrating device readings...")
    
    # Get device mapping (SQLite ID -> PostgreSQL ID)
    result = await session.execute(select(Device))
    devices = result.scalars().all()
    device_map = {d.device_code: d.id for d in devices}
    
    cur = sqlite_conn.cursor()
    
    # Check if device_readings table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='device_readings'")
    if not cur.fetchone():
        print("  ⚠️  No device_readings table found in SQLite")
        return 0
    
    # Get column names
    cur.execute("PRAGMA table_info(device_readings)")
    columns = [r[1] for r in cur.fetchall()]
    
    # Get total count
    cur.execute("SELECT COUNT(*) FROM device_readings")
    total = cur.fetchone()[0]
    
    if total == 0:
        print("  ⚠️  No readings found in SQLite")
        return 0
    
    print(f"  📈 Found {total:,} readings to migrate")
    
    # Fetch and migrate in batches
    batch_size = 1000
    migrated = 0
    batch = []
    
    cur.execute("SELECT * FROM device_readings ORDER BY timestamp")
    
    for row in cur:
        data = dict(zip(columns, row))
        
        # Map device_id from SQLite to PostgreSQL
        # If old data uses device_id directly
        old_device_id = data.get('device_id')
        
        # Try to find device by old ID or device_code
        new_device_id = None
        for device_code, pg_id in device_map.items():
            if device_code == f"M{old_device_id}":
                new_device_id = pg_id
                break
        
        if not new_device_id:
            # Fallback: use device_id directly if it exists in mapping
            new_device_id = old_device_id
        
        # Parse timestamp
        timestamp_str = data.get('timestamp')
        try:
            # Handle various timestamp formats
            if isinstance(timestamp_str, str):
                # Remove timezone info if present
                timestamp_str = timestamp_str.replace('Z', '').replace('+00:00', '').strip()
                timestamp = datetime.fromisoformat(timestamp_str)
            else:
                timestamp = datetime.utcnow()
        except Exception as e:
            print(f"  ⚠️  Invalid timestamp: {timestamp_str}, using current time")
            timestamp = datetime.utcnow()
        
        # Determine status based on counter values
        counter_19l = data.get('counter_19l')
        counter_5l = data.get('counter_5l')
        
        if counter_19l is not None and counter_5l is not None:
            status = 'ONLINE'
        elif counter_19l is None and counter_5l is None:
            status = 'OFFLINE'
        else:
            status = 'PARTIAL'
        
        reading = DeviceReading(
            device_id=new_device_id,
            timestamp=timestamp,
            counter_19l=counter_19l,
            counter_5l=counter_5l,
            status=status,
        )
        
        batch.append(reading)
        
        if len(batch) >= batch_size:
            session.add_all(batch)
            await session.flush()
            migrated += len(batch)
            print(f"  ⏳ Migrated {migrated:,}/{total:,} readings ({(migrated/total)*100:.1f}%)", end='\r')
            batch = []
    
    # Insert remaining
    if batch:
        session.add_all(batch)
        migrated += len(batch)
    
    await session.commit()
    print(f"\n  📊 Total readings migrated: {migrated:,}")
    return migrated


async def main():
    """Main migration function."""
    print("\n" + "="*60)
    print("  Sumatic Modern IoT - SQLite to PostgreSQL Migration")
    print("="*60)
    
    # Check prerequisites
    if not check_sqlite_file():
        return
    
    if not await check_postgresql_connection():
        return
    
    # Show SQLite stats
    print("\n📊 SQLite Database Statistics:")
    stats = get_sqlite_stats()
    for table, count in stats.items():
        print(f"  {table}: {count}")
    
    # Confirm migration
    print("\n⚠️  This will migrate data from SQLite to PostgreSQL.")
    print("⚠️  Existing records with same device_code will be skipped.")
    response = input("\nProceed with migration? (yes/no): ")
    
    if response.lower() != 'yes':
        print("\n❌ Migration cancelled")
        return
    
    # Open SQLite connection
    sqlite_conn = sqlite3.connect(str(SQLITE_DB_PATH))
    
    try:
        async with async_session_maker() as session:
            # Migrate devices first
            devices_migrated = await migrate_devices(session, sqlite_conn)
            
            # Then migrate readings
            readings_migrated = await migrate_readings(session, sqlite_conn)
            
            print("\n" + "="*60)
            print("  Migration Summary:")
            print("="*60)
            print(f"  Devices migrated:  {devices_migrated}")
            print(f"  Readings migrated: {readings_migrated:,}")
            print("="*60)
            print("\n✅ Migration completed successfully!")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    asyncio.run(main())
