"""add_program_generation_in_progress

Revision ID: add_program_gen_progress
Revises: add_2fa_support
Create Date: 2026-02-12 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'add_program_gen_progress'
down_revision = 'add_2fa_support'
branch_labels = None
depends_on = None


def upgrade():
    """Add generation_in_progress column to programs table."""
    op.add_column(
        'programs',
        sa.Column('generation_in_progress', sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade():
    """Remove generation_in_progress column from programs table."""
    op.drop_column('programs', 'generation_in_progress')
