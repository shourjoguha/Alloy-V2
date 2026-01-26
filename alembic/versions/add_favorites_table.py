"""add_favorites_table

Revision ID: add_favorites_table
Revises: create_program_disciplines_table
Create Date: 2026-01-25 17:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_favorites_table'
down_revision: Union[str, Sequence[str], None] = 'create_program_disciplines_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create favorites table."""
    op.create_table(
        'favorites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('movement_id', sa.Integer(), nullable=True),
        sa.Column('program_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['movement_id'], ['movements.id'], ondelete='CASCADE', name='fk_favorites_movement_id'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE', name='fk_favorites_program_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_favorites_user_id'),
        sa.PrimaryKeyConstraint('id', name='pk_favorites'),
        sa.UniqueConstraint('user_id', 'movement_id', name='uq_user_movement_favorite'),
        sa.UniqueConstraint('user_id', 'program_id', name='uq_user_program_favorite')
    )
    op.create_index('ix_favorites_user_id', 'favorites', ['user_id'])


def downgrade() -> None:
    """Drop favorites table."""
    op.drop_index('ix_favorites_user_id', table_name='favorites')
    op.drop_table('favorites')
