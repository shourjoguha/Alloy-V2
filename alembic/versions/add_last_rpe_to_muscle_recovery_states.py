"""Add last_rpe column to muscle_recovery_states

Revision ID: g3h4i5j6k7l8
Revises: f1a2b3c4d5e6
Create Date: 2026-02-11 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'g3h4i5j6k7l8'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'muscle_recovery_states',
        sa.Column('last_rpe', sa.Float(), nullable=False, server_default='7.0')
    )


def downgrade() -> None:
    op.drop_column('muscle_recovery_states', 'last_rpe')
