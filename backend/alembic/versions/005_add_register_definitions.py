"""Add register definitions

Revision ID: 005_add_register_definitions
Revises: 004_remove_unused_tables
Create Date: 2026-03-30 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision: str = '005_add_register_definitions'
down_revision: Union[str, None] = '004_remove_unused_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add register definitions
    register_definitions = table(
        'register_definitions',
        column('fc', sa.Integer),
        column('reg', sa.Integer),
        column('name', sa.String),
        column('data_type', sa.String),
        column('unit', sa.String),
        column('description', sa.String)
    )
    
    # Check if registers already exist to avoid duplicate key errors
    connection = op.get_bind()
    
    # Check if Sayac 1 (fc=4, reg=2000) exists
    result = connection.execute(
        sa.text("SELECT COUNT(*) FROM register_definitions WHERE fc=4 AND reg=2000")
    ).scalar()
    
    if result == 0:
        # Insert register definitions
        op.bulk_insert(register_definitions, [
            {
                'fc': 4,
                'reg': 2000,
                'name': 'Sayac 1',
                'data_type': 'uint16',
                'unit': 'adet',
                'description': '19L sayaç değeri'
            },
            {
                'fc': 4,
                'reg': 2001,
                'name': 'Sayac 2',
                'data_type': 'uint16',
                'unit': 'adet',
                'description': '5L sayaç değeri'
            },
            {
                'fc': 3,
                'reg': 100,
                'name': 'Sıcaklık',
                'data_type': 'int16',
                'unit': '°C',
                'description': 'Sıcaklık değeri'
            },
            {
                'fc': 3,
                'reg': 101,
                'name': 'Basınç',
                'data_type': 'uint16',
                'unit': 'bar',
                'description': 'Basınç değeri'
            },
            {
                'fc': 3,
                'reg': 102,
                'name': 'Nem',
                'data_type': 'uint16',
                'unit': '%',
                'description': 'Nem değeri'
            },
        ])
        print("Register tanımları eklendi")
    else:
        print("Register tanımları zaten mevcut, atlanıyor")


def downgrade() -> None:
    # Remove the added register definitions
    op.execute(
        sa.text("DELETE FROM register_definitions WHERE fc=4 AND reg IN (2000, 2001)")
    )
    op.execute(
        sa.text("DELETE FROM register_definitions WHERE fc=3 AND reg IN (100, 101, 102)")
    )
