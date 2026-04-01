"""add_tuya_devices_table

Revision ID: ebab64a6e70f
Revises: 005_add_register_definitions
Create Date: 2026-03-31 12:58:23.213324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ebab64a6e70f'
down_revision: Union[str, None] = '005_add_register_definitions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tuya_devices table
    op.create_table(
        'tuya_devices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('device_type', sa.String(length=50), nullable=False, server_default='SMART_PLUG'),
        sa.Column('local_key', sa.String(length=128), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_online', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('power_state', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('last_control_at', sa.DateTime(), nullable=True),
        sa.Column('product_id', sa.String(length=64), nullable=True),
        sa.Column('product_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_id')
    )
    op.create_index(op.f('ix_tuya_devices_device_id'), 'tuya_devices', ['device_id'], unique=True)
    op.create_index(op.f('ix_tuya_devices_id'), 'tuya_devices', ['id'], unique=False)


def downgrade() -> None:
    # Drop tuya_devices table
    op.drop_index(op.f('ix_tuya_devices_id'), table_name='tuya_devices')
    op.drop_index(op.f('ix_tuya_devices_device_id'), table_name='tuya_devices')
    op.drop_table('tuya_devices')
