"""phase3_step1_create_program_disciplines_table

Revision ID: create_program_disciplines_table
Revises: 99548d10fc10
Create Date: 2026-01-23 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'create_program_disciplines_table'
down_revision: Union[str, Sequence[str], None] = '99548d10fc10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create program_disciplines junction table."""
    op.create_table(
        'program_disciplines',
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('discipline_type', sa.String(length=50), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], name='fk_program_disciplines_program_id'),
        sa.PrimaryKeyConstraint('program_id', 'discipline_type', name='pk_program_disciplines')
    )
    op.create_index('ix_program_disciplines_program_id', 'program_disciplines', ['program_id'])


def downgrade() -> None:
    """Drop program_disciplines junction table."""
    op.drop_index('ix_program_disciplines_program_id', table_name='program_disciplines')
    op.drop_table('program_disciplines')
