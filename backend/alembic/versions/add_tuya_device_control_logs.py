"""add tuya_device_control_logs table

Revision ID: add_tuya_control_logs
Revises: ebab64a6e70f
Create Date: 2026-03-31

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_tuya_control_logs'
down_revision = 'ebab64a6e70f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table exists before creating
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Only create if table doesn't exist
    if not inspector.has_table('tuya_device_control_logs'):
        op.create_table(
            'tuya_device_control_logs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('tuya_device_id', sa.Integer(), sa.ForeignKey('tuya_devices.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('action', sa.String(20), nullable=False),
            sa.Column('previous_state', sa.Boolean(), nullable=False),
            sa.Column('new_state', sa.Boolean(), nullable=True),
            sa.Column('success', sa.Boolean(), nullable=False),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('performed_by', sa.String(100), nullable=True),
            sa.Column('performed_at', sa.DateTime(timezone=True), nullable=False, index=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index('idx_tuya_control_device_id', 'tuya_device_control_logs', ['tuya_device_id'])
        op.create_index('idx_tuya_control_performed_at', 'tuya_device_control_logs', ['performed_at'])


def downgrade() -> None:
    op.drop_index('idx_tuya_control_performed_at', table_name='tuya_device_control_logs')
    op.drop_index('idx_tuya_control_device_id', table_name='tuya_device_control_logs')
    op.drop_table('tuya_device_control_logs')
