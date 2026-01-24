"""add block_type to movements

Revision ID: 8e2f9f052d17
Revises: extend_microcycle_length_to_14
Create Date: 2026-01-22 12:54:55.111914

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e2f9f052d17'
down_revision: Union[str, Sequence[str], None] = 'extend_microcycle_length_to_14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add block_type column
    op.add_column('movements', sa.Column('block_type', sa.String(length=50), server_default='All', nullable=False))
    op.create_index(op.f('ix_movements_block_type'), 'movements', ['block_type'], unique=False)

    # Backfill data
    movements = sa.table('movements',
        sa.column('pattern', sa.String),
        sa.column('block_type', sa.String)
    )

    # if pattern in ['mobility' , 'olympic'] then Block_Type = pattern
    op.execute(
        movements.update().where(
            movements.c.pattern.in_(['mobility', 'olympic'])
        ).values(block_type=movements.c.pattern)
    )

    # if pattern in ['plyometric'] then Block_Type = 'Explosiveness'
    op.execute(
        movements.update().where(
            movements.c.pattern == 'plyometric'
        ).values(block_type='Explosiveness')
    )

    # if pattern in ['cardio'] then Block_Type = 'Endurance'
    op.execute(
        movements.update().where(
            movements.c.pattern == 'cardio'
        ).values(block_type='Endurance')
    )

    # if pattern in ['conditioning','carry'] then Block_Type = 'Fat Loss'
    op.execute(
        movements.update().where(
            movements.c.pattern.in_(['conditioning', 'carry'])
        ).values(block_type='Fat Loss')
    )
    # Else Block_Type = 'All' (handled by default value)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_movements_block_type'), table_name='movements')
    op.drop_column('movements', 'block_type')
