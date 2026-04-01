"""Add monthly revenue tracking tables

Revision ID: 006_add_monthly_revenue_tracking
Revises: ebab64a6e70f
Create Date: 2026-04-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_add_monthly_revenue_tracking'
down_revision: Union[str, None] = 'add_tuya_control_logs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create device_month_cycles table
    op.create_table(
        'device_month_cycles',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('cycle_start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cycle_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('start_counter_19l', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('start_counter_5l', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('end_counter_19l', sa.Integer(), nullable=True),
        sa.Column('end_counter_5l', sa.Integer(), nullable=True),
        sa.Column('total_revenue', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('is_closed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_month_cycles_device_id'), 'device_month_cycles', ['device_id'], unique=False)
    op.create_index(op.f('ix_device_month_cycles_cycle_start_date'), 'device_month_cycles', ['cycle_start_date'], unique=False)
    op.create_index(op.f('ix_device_month_cycles_is_closed'), 'device_month_cycles', ['is_closed'], unique=False)
    op.create_index(op.f('ix_device_month_cycles_month'), 'device_month_cycles', ['month'], unique=False)
    op.create_index(op.f('ix_device_month_cycles_year'), 'device_month_cycles', ['year'], unique=False)
    
    # Create monthly_revenue_records table
    op.create_table(
        'monthly_revenue_records',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('month_start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('month_end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closing_counter_19l', sa.Integer(), nullable=True),
        sa.Column('closing_counter_5l', sa.Integer(), nullable=True),
        sa.Column('total_revenue', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_closed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_id', 'year', 'month', name='unique_device_year_month')
    )
    op.create_index(op.f('ix_monthly_revenue_records_device_id'), 'monthly_revenue_records', ['device_id'], unique=False)
    op.create_index(op.f('ix_monthly_revenue_records_month'), 'monthly_revenue_records', ['month'], unique=False)
    op.create_index(op.f('ix_monthly_revenue_records_year'), 'monthly_revenue_records', ['year'], unique=False)


def downgrade() -> None:
    # Drop monthly_revenue_records table
    op.drop_index(op.f('ix_monthly_revenue_records_year'), table_name='monthly_revenue_records')
    op.drop_index(op.f('ix_monthly_revenue_records_month'), table_name='monthly_revenue_records')
    op.drop_index(op.f('ix_monthly_revenue_records_device_id'), table_name='monthly_revenue_records')
    op.drop_table('monthly_revenue_records')
    
    # Drop device_month_cycles table
    op.drop_index(op.f('ix_device_month_cycles_year'), table_name='device_month_cycles')
    op.drop_index(op.f('ix_device_month_cycles_month'), table_name='device_month_cycles')
    op.drop_index(op.f('ix_device_month_cycles_is_closed'), table_name='device_month_cycles')
    op.drop_index(op.f('ix_device_month_cycles_cycle_start_date'), table_name='device_month_cycles')
    op.drop_index(op.f('ix_device_month_cycles_device_id'), table_name='device_month_cycles')
    op.drop_table('device_month_cycles')
