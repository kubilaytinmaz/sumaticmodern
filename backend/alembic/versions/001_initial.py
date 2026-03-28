"""Initial migration - Create all tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_email', 'users', ['email'])

    # Create devices table
    op.create_table(
        'devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_code', sa.String(length=50), nullable=False),
        sa.Column('modem_id', sa.String(length=8), nullable=False),
        sa.Column('device_addr', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('method_no', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reg_offset_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('alias_json', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('skip_raw_json', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_pending', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_code'),
        sa.UniqueConstraint('modem_id', 'device_addr')
    )
    op.create_index('idx_devices_modem', 'devices', ['modem_id'])
    op.create_index('idx_devices_code', 'devices', ['device_code'])
    op.create_index('idx_devices_enabled', 'devices', ['is_enabled'])
    op.create_index('idx_devices_last_seen', 'devices', ['last_seen_at'])

    # Create device_readings table
    op.create_table(
        'device_readings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('counter_19l', sa.Integer(), nullable=True),
        sa.Column('counter_5l', sa.Integer(), nullable=True),
        sa.Column('output_1_status', sa.Integer(), nullable=True),
        sa.Column('output_2_status', sa.Integer(), nullable=True),
        sa.Column('fault_status', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('program_1_time', sa.Integer(), nullable=True),
        sa.Column('program_2_time', sa.Integer(), nullable=True),
        sa.Column('program_1_coin_count', sa.Integer(), nullable=True),
        sa.Column('program_2_coin_count', sa.Integer(), nullable=True),
        sa.Column('output3_input1_time', sa.Integer(), nullable=True),
        sa.Column('output3_input2_time', sa.Integer(), nullable=True),
        sa.Column('counter_total_low', sa.Integer(), nullable=True),
        sa.Column('counter_total_high', sa.Integer(), nullable=True),
        sa.Column('modbus_address', sa.Integer(), nullable=True),
        sa.Column('device_password', sa.Integer(), nullable=True),
        sa.Column('raw_data', sa.JSON(), nullable=True),
        sa.Column('is_spike', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id', 'timestamp'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE')
    )
    op.create_index('idx_readings_device_time', 'device_readings', ['device_id', 'timestamp'])
    op.create_index('idx_readings_timestamp', 'device_readings', ['timestamp'])

    # Create device_status table
    op.create_table(
        'device_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE')
    )
    op.create_index('idx_status_device', 'device_status', ['device_id', 'started_at'])

    # Create register_definitions table
    op.create_table(
        'register_definitions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fc', sa.Integer(), nullable=False),
        sa.Column('reg', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('data_type', sa.String(length=20), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fc', 'reg')
    )
    op.create_index('idx_register_fc_reg', 'register_definitions', ['fc', 'reg'])

    # Insert default register definitions
    op.execute("""
        INSERT INTO register_definitions (fc, reg, name, data_type, unit, description) VALUES
        (3, 1000, 'Program 1 Cikis Zamani', 'uint16', 'saniye', 'Program 1 cikis suresi'),
        (3, 1001, 'Program 2 Cikis Zamani', 'uint16', 'saniye', 'Program 2 cikis suresi'),
        (3, 1002, 'Program 1 Para Adedi', 'uint16', 'adet', 'Program 1 toplam para adedi'),
        (3, 1003, 'Program 2 Para Adedi', 'uint16', 'adet', 'Program 2 toplam para adedi'),
        (3, 1004, 'Cikis-3 : Giris 1 Ortak Zaman', 'uint16', 'saniye', 'Cikis 3 giris 1 ortak zaman'),
        (3, 1005, 'Cikis-3 : Giris 2 Ortak Zaman', 'uint16', 'saniye', 'Cikis 3 giris 2 ortak zaman'),
        (3, 1006, 'Cihaz Sifresi', 'uint16', '', 'Cihaz sifresi'),
        (3, 1007, 'Modbus Adresi', 'uint16', '', 'Modbus RTU adresi'),
        (3, 1453, 'Acilis Mesaji', 'uint16', '', 'Acilis mesaji (0=KBO, 1=Sumatic)'),
        (4, 2000, 'Sayac 1', 'uint16', 'TL', '19 litre sayaci'),
        (4, 2001, 'Sayac 2', 'uint16', 'TL', '5 litre sayaci'),
        (4, 2002, 'Cikis-1 Durum', 'uint16', '', 'Cikis 1 durumu'),
        (4, 2003, 'Cikis-2 Durum', 'uint16', '', 'Cikis 2 durumu'),
        (4, 2004, 'Acil Ariza Durumu', 'uint16', '', 'Acil ariza durumu (0=OK, 1=Ariza)'),
        (4, 2005, 'Sayac Toplam Low', 'uint16', '', 'Toplam sayac dusuk 16-bit'),
        (4, 2006, 'Sayac Toplam High', 'uint16', '', 'Toplam sayac yuksek 16-bit')
    """)


def downgrade() -> None:
    op.drop_table('register_definitions')
    op.drop_table('device_status')
    op.drop_table('device_readings')
    op.drop_table('devices')
    op.drop_table('users')
