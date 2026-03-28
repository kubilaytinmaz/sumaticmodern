"""Fix device_readings id autoincrement

Revision ID: 003_fix_autoincrement
Revises: 002_counter_only_optimization
Create Date: 2026-03-24 10:07:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_fix_autoincrement'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite doesn't support ALTER COLUMN to change PRIMARY KEY constraint
    # We need to recreate the table
    
    # Step 1: Create new table with correct schema
    op.execute("""
        CREATE TABLE device_readings_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            counter_19l INTEGER,
            counter_5l INTEGER,
            FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE CASCADE
        )
    """)
    
    # Step 2: Copy data from old table to new table
    op.execute("""
        INSERT INTO device_readings_new (id, device_id, timestamp, counter_19l, counter_5l)
        SELECT id, device_id, timestamp, counter_19l, counter_5l
        FROM device_readings
    """)
    
    # Step 3: Drop old table
    op.execute("DROP TABLE device_readings")
    
    # Step 4: Rename new table to original name
    op.execute("ALTER TABLE device_readings_new RENAME TO device_readings")
    
    # Step 5: Recreate indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_device_readings_device_id ON device_readings (device_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_device_readings_timestamp ON device_readings (timestamp)")


def downgrade() -> None:
    # Revert back to BIGINT NOT NULL PRIMARY KEY (without AUTOINCREMENT)
    op.execute("""
        CREATE TABLE device_readings_new (
            id BIGINT NOT NULL,
            device_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            counter_19l INTEGER,
            counter_5l INTEGER,
            PRIMARY KEY (id),
            FOREIGN KEY(device_id) REFERENCES devices (id) ON DELETE CASCADE
        )
    """)
    
    op.execute("""
        INSERT INTO device_readings_new (id, device_id, timestamp, counter_19l, counter_5l)
        SELECT id, device_id, timestamp, counter_19l, counter_5l
        FROM device_readings
    """)
    
    op.execute("DROP TABLE device_readings")
    op.execute("ALTER TABLE device_readings_new RENAME TO device_readings")
    
    op.execute("CREATE INDEX IF NOT EXISTS ix_device_readings_device_id ON device_readings (device_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_device_readings_timestamp ON device_readings (timestamp)")
