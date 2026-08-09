"""add kid_info more fields (age, favorite_color, favorite_animal)

Revision ID: a1b2c3d4e5f6
Revises: 2043bf995c6a
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '2043bf995c6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('kid_info', sa.Column('age', sa.Integer(), nullable=True))
    op.add_column('kid_info', sa.Column('favorite_color', sa.String(), nullable=True))
    op.add_column('kid_info', sa.Column('favorite_animal', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('kid_info', 'favorite_animal')
    op.drop_column('kid_info', 'favorite_color')
    op.drop_column('kid_info', 'age')
