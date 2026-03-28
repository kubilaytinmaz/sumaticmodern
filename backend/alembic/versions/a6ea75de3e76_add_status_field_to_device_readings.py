"""add status field to device_readings

Revision ID: a6ea75de3e76
Revises: 3eb55fc04714
Create Date: 2026-03-27 13:00:43.201495

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6ea75de3e76'
down_revision: Union[str, None] = '3eb55fc04714'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add status column to device_readings table
    op.add_column('device_readings', sa.Column('status', sa.String(length=10), nullable=True))


def downgrade() -> None:
    # Remove status column from device_readings table
    op.drop_column('device_readings', 'status')
