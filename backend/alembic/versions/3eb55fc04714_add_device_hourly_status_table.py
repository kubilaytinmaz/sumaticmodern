"""add_device_hourly_status_table

Revision ID: 3eb55fc04714
Revises: 003_fix_autoincrement
Create Date: 2026-03-27 11:34:36.057242

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3eb55fc04714'
down_revision: Union[str, None] = '003_fix_autoincrement'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
