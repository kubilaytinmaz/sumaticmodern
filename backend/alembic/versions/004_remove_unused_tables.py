"""Remove unused table: device_status

Revision ID: 004_remove_unused_tables
Revises: 3eb55fc04714
Create Date: 2026-03-28 12:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_remove_unused_tables'
down_revision: Union[str, None] = 'a6ea75de3e76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove unused device_status table."""
    # Drop device_status table (unused, 0 rows, record_status_change never called)
    op.drop_table('device_status')


def downgrade() -> None:
    """Recreate the dropped table for rollback."""
    # Recreate device_status table
    op.create_table(
        'device_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('status_meta', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_device_status_device_id'), 'device_status', ['device_id'], unique=False)
    op.create_index(op.f('ix_device_status_started_at'), 'device_status', ['started_at'], unique=False)
