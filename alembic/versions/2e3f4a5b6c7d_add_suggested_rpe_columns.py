"""add_suggested_rpe_columns

Revision ID: 2e3f4a5b6c7d
Revises: 1d490889b1ef
Create Date: 2026-02-11 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '2e3f4a5b6c7d'
down_revision: Union[str, Sequence[str], None] = '1d490889b1ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('session_exercises', sa.Column('suggested_rpe_min', sa.Float(), nullable=True))
    op.add_column('session_exercises', sa.Column('suggested_rpe_max', sa.Float(), nullable=True))
    op.add_column('session_exercises', sa.Column('rpe_adjustment_reason', sa.String(100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('session_exercises', 'rpe_adjustment_reason')
    op.drop_column('session_exercises', 'suggested_rpe_max')
    op.drop_column('session_exercises', 'suggested_rpe_min')
