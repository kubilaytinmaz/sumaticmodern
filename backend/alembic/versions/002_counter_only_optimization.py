"""Counter-only optimization - Remove non-counter fields from device_readings.

Revision ID: 002_counter_only
Revises: 001_initial
Create Date: 2026-03-24 09:00:00.000000

Bu migration device_readings tablosundan sadece sayaç verilerini tutarak
gereksiz sütunları kaldırır. SQLite'ta ALTER TABLE DROP COLUMN desteği
sınırlı olduğu için tablo yeniden oluşturulur, eski veriler kopyalanır.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Yeni (sadece sayaç alanları olan) tabloyu oluştur
    op.create_table(
        'device_readings_new',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('counter_19l', sa.Integer(), nullable=True),
        sa.Column('counter_5l', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_readings_new_device_time', 'device_readings_new', ['device_id', 'timestamp'])
    op.create_index('idx_readings_new_timestamp', 'device_readings_new', ['timestamp'])

    # 2. Eski tablodan sadece sayaç verilerini kopyala (veri kaybolmaz)
    op.execute("""
        INSERT INTO device_readings_new (id, device_id, timestamp, counter_19l, counter_5l)
        SELECT id, device_id, timestamp, counter_19l, counter_5l
        FROM device_readings
    """)

    # 3. Eski tabloyu sil
    op.drop_table('device_readings')

    # 4. Yeni tabloyu device_readings olarak yeniden adlandır
    op.rename_table('device_readings_new', 'device_readings')

    # 5. Index'leri doğru isimlerle yeniden oluştur
    op.drop_index('idx_readings_new_device_time', table_name='device_readings')
    op.drop_index('idx_readings_new_timestamp', table_name='device_readings')
    op.create_index('idx_readings_device_time', 'device_readings', ['device_id', 'timestamp'])
    op.create_index('idx_readings_timestamp', 'device_readings', ['timestamp'])

    # 6. register_definitions tablosundan gereksiz register'ları temizle
    #    (FC3: program/output/modbus register'ları, FC4: sayaç dışındakiler)
    op.execute("""
        DELETE FROM register_definitions
        WHERE (fc = 3 AND reg IN (1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1453))
           OR (fc = 4 AND reg IN (2002, 2003, 2004, 2005, 2006))
    """)


def downgrade() -> None:
    # Downgrade desteklenmiyor - eski sütunlar geri getirilemez (veri kaybı olur)
    # Rollback gerekiyorsa: backup dosyasından restore yapın
    # backend/sumatic_modern.db.backup_YYYYMMDD
    raise NotImplementedError(
        "Downgrade not supported. "
        "Restore from backup: backend/sumatic_modern.db.backup_20260324"
    )
