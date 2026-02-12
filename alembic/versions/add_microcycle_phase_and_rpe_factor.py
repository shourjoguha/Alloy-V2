"""add_microcycle_phase_and_rpe_factor

Revision ID: add_micro_phase_rpe
Revises: add_gen_to_micro
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_micro_phase_rpe'
down_revision: Union[str, Sequence[str], None] = 'add_gen_to_micro'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Add microcycle_phase and rpe_intensity_factor columns to microcycles table.
    """
    op.add_column(
        'microcycles',
        sa.Column('microcycle_phase', sa.String(50), nullable=True)
    )
    op.add_column(
        'microcycles',
        sa.Column('rpe_intensity_factor', sa.Float(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema.

    Remove microcycle_phase and rpe_intensity_factor columns from microcycles table.
    """
    op.drop_column('microcycles', 'rpe_intensity_factor')
    op.drop_column('microcycles', 'microcycle_phase')
