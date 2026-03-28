"""
Sumatic Modern IoT - doludb.db Migration Script
Simple direct SQLite migration.
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DOLUDB_PATH = BASE_DIR / "doludb.db"
MODERN_DB_PATH = BASE_DIR / "sumatic_modern.db"

# Device mapping
DEVICE_MAPPING = {
    "m1": 1,
    "m2": 2,
    "m3": 3,
    "m4": 4,
}

# Column mapping
COLUMN_MAPPING = {
    "Sayac 1": "counter_19l",
    "Sayac 2": "counter_5l",
    "Sayac Toplam (Low16)": "counter_total_low",
    "Sayac Toplam (High16)": "counter_total_high",
    "Acil Ariza Durumu": "fault_status",
    "Cikis-1 Durum": "output_1_status",
    "Cikis-2 Durum": "output_2_status",
    "Program 1 Cikis Zamani": "program_1_time",
    "Program 2 Cikis Zamani": "program_2_time",
    "Program 1 Para Adedi": "program_1_coin_count",
    "Program 2 Para Adedi": "program_2_coin_count",
    "Cikis-3 : Giris 1 Ortak Zaman": "output3_input1_time",
    "Cikis-3 : Giris 2 Ortak Zaman": "output3_input2_time",
    "Modbus Adresi": "modbus_address",
    "Cihaz Sifresi": "device_password",
}

ISTANBUL_OFFSET = timedelta(hours=3)


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def convert_ts(ts_str: str) -> str:
    """Convert Istanbul naive to UTC string."""
    try:
        ts_clean = ts_str.replace("Z", "").replace("+00:00", "").strip()
        dt = datetime.fromisoformat(ts_clean)
        dt_utc = dt - ISTANBUL_OFFSET
        return dt_utc.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return None


def match_device(table_name: str) -> int:
    """Match table to device ID."""
    for prefix, device_id in DEVICE_MAPPING.items():
        if table_name.lower().startswith(prefix.lower()):
            return device_id
    return None


def ensure_tables(modern_conn):
    """Create tables - drop and recreate device_readings to fix BIGINT issue."""
    cur = modern_conn.cursor()
    
    # Drop device_readings if exists (might have wrong BIGINT type from SQLAlchemy)
    cur.execute("DROP TABLE IF EXISTS device_readings")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            modem_id TEXT,
            device_addr INTEGER,
            location TEXT,
            is_enabled INTEGER DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS device_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
            timestamp TEXT NOT NULL,
            counter_19l INTEGER,
            counter_5l INTEGER,
            output_1_status INTEGER,
            output_2_status INTEGER,
            fault_status INTEGER NOT NULL DEFAULT 0,
            program_1_time INTEGER,
            program_2_time INTEGER,
            program_1_coin_count INTEGER,
            program_2_coin_count INTEGER,
            output3_input1_time INTEGER,
            output3_input2_time INTEGER,
            counter_total_low INTEGER,
            counter_total_high INTEGER,
            modbus_address INTEGER,
            device_password INTEGER,
            is_spike INTEGER NOT NULL DEFAULT 0
        );
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_readings_device_ts 
        ON device_readings(device_id, timestamp DESC);
    """)
    
    modern_conn.commit()


def ensure_devices(modern_conn):
    """Create device records."""
    cur = modern_conn.cursor()
    for prefix, device_id in DEVICE_MAPPING.items():
        cur.execute("SELECT id FROM devices WHERE id = ?", (device_id,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO devices (id, device_code, name, modem_id, device_addr, location, is_enabled) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (device_id, f"M{device_id}", f"Merkez Cihaz {device_id}", "00001276", device_id, "Ana Bina", 1)
            )
            print(f"  [+] Created M{device_id}")
        else:
            print(f"  [=] M{device_id} exists")
    modern_conn.commit()


def migrate_table(dolu_conn, modern_conn, table_name, device_id, dry_run=False):
    """Migrate one table."""
    print(f"\n  Migrating '{table_name}' -> device_id {device_id}...")
    
    dolu_cur = dolu_conn.cursor()
    modern_cur = modern_conn.cursor()
    
    # Get available columns
    dolu_cur.execute(f'PRAGMA table_info({qident(table_name)});')
    available = [c[1] for c in dolu_cur.fetchall()]
    
    # Build SELECT columns
    sel_cols = ["ts_received"]
    for col in available:
        if col in COLUMN_MAPPING:
            sel_cols.append(col)
    
    sel_sql = ", ".join([qident(c) for c in sel_cols])
    dolu_cur.execute(f'SELECT {sel_sql} FROM {qident(table_name)} ORDER BY ts_received;')
    rows = dolu_cur.fetchall()
    
    total = len(rows)
    stats = {"total": total, "inserted": 0, "skipped": 0}
    
    if total == 0:
        print(f"  [!] Empty table")
        return stats
    
    # Build INSERT columns (always same order)
    ins_cols = [
        "device_id", "timestamp",
        "counter_19l", "counter_5l",
        "output_1_status", "output_2_status",
        "fault_status",
        "program_1_time", "program_2_time",
        "program_1_coin_count", "program_2_coin_count",
        "output3_input1_time", "output3_input2_time",
        "counter_total_low", "counter_total_high",
        "modbus_address", "device_password",
        "is_spike"
    ]
    
    ins_sql = f"INSERT INTO device_readings ({', '.join(ins_cols)}) VALUES ({', '.join(['?']*len(ins_cols))})"
    
    batch = []
    batch_size = 500
    
    for i, row in enumerate(rows):
        ts_utc = convert_ts(row[0])
        if not ts_utc:
            stats["skipped"] += 1
            continue
        
        # Build values dict
        vals = {col: None for col in ins_cols}
        vals["device_id"] = device_id
        vals["timestamp"] = ts_utc
        vals["is_spike"] = 0
        vals["fault_status"] = 0
        
        # Map row values
        for j, col_name in enumerate(sel_cols):
            if col_name == "ts_received":
                continue
            modern_col = COLUMN_MAPPING.get(col_name)
            if modern_col:
                val = row[j]
                if val is not None:
                    try:
                        vals[modern_col] = int(val)
                    except:
                        vals[modern_col] = None
        
        # Convert to list in correct order
        row_values = [vals[col] for col in ins_cols]
        batch.append(tuple(row_values))
        
        if len(batch) >= batch_size:
            if not dry_run:
                for rv in batch:
                    try:
                        modern_cur.execute(ins_sql, rv)
                        stats["inserted"] += 1
                    except Exception as e:
                        stats["skipped"] += 1
                        if stats["skipped"] == 1:  # Print first error
                            print(f"\n    First error: {e}")
                            print(f"    SQL: {ins_sql}")
                            print(f"    Values: {rv}")
            else:
                stats["inserted"] += len(batch)
            batch = []
            pct = ((i+1)/total)*100
            print(f"    Progress: {i+1:,}/{total:,} ({pct:.0f}%)", end="\r")
    
    # Remaining
    if batch:
        if not dry_run:
            for rv in batch:
                try:
                    modern_cur.execute(ins_sql, rv)
                    stats["inserted"] += 1
                except sqlite3.IntegrityError:
                    stats["skipped"] += 1
        else:
            stats["inserted"] += len(batch)
    
    if not dry_run:
        modern_conn.commit()
    
    print(f"    Done: {stats['inserted']:,} inserted, {stats['skipped']:,} skipped              ")
    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("  Sumatic Modern IoT - doludb.db Migration")
    print("=" * 50)
    
    if not DOLUDB_PATH.exists():
        print(f"  [!] doludb.db not found")
        return
    
    dolu_conn = sqlite3.connect(str(DOLUDB_PATH))
    modern_conn = sqlite3.connect(str(MODERN_DB_PATH))
    modern_conn.execute("PRAGMA journal_mode=WAL;")
    
    try:
        print("\n  Setting up tables...")
        ensure_tables(modern_conn)
        
        print("\n  Ensuring devices...")
        ensure_devices(modern_conn)
        
        # Get tables
        cur = dolu_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'm%' ORDER BY name;")
        tables = [r[0] for r in cur.fetchall()]
        
        to_migrate = []
        for t in tables:
            did = match_device(t)
            if did:
                to_migrate.append((t, did))
        
        if not to_migrate:
            print("  [!] No tables found")
            return
        
        print(f"\n  Found {len(to_migrate)} tables:")
        for t, did in to_migrate:
            cur.execute(f'SELECT COUNT(*) FROM {qident(t)};')
            cnt = cur.fetchone()[0]
            print(f"    {t} -> device {did}: {cnt:,} rows")
        
        if args.dry_run:
            print("\n  ** DRY RUN MODE **")
        
        all_stats = {}
        for t, did in to_migrate:
            stats = migrate_table(dolu_conn, modern_conn, t, did, args.dry_run)
            all_stats[t] = stats
        
        # Summary
        print("\n" + "=" * 50)
        print("  Summary:")
        for t, s in all_stats.items():
            print(f"  {t}: {s['inserted']:,} / {s['total']:,}")
        ti = sum(s["inserted"] for s in all_stats.values())
        tt = sum(s["total"] for s in all_stats.values())
        print(f"\n  TOTAL: {ti:,} / {tt:,}")
        print("=" * 50)
        
        # Verify
        cur = modern_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM device_readings;")
        print(f"\n  Total readings in DB: {cur.fetchone()[0]:,}")
        
    finally:
        dolu_conn.close()
        modern_conn.close()
    
    print("\n  Done!")


if __name__ == "__main__":
    main()
