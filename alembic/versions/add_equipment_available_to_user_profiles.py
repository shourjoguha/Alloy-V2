"""Add equipment_available to user_profiles

Revision ID: add_equipment_available
Revises: e0787659d7a0
Create Date: 2026-02-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = 'add_equipment_available'
down_revision: Union[str, Sequence[str], None] = 'e0787659d7a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_profiles', sa.Column('equipment_available', JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_profiles', 'equipment_available')
