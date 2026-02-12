"""add_generation_status_to_microcycles

Revision ID: add_gen_to_micro
Revises: add_gen_status
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = 'add_gen_to_micro'
down_revision: Union[str, Sequence[str], None] = 'add_gen_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Add generation_status column to microcycles table with 'PENDING' as default value.
    The column is an ENUM with possible values: PENDING, IN_PROGRESS, COMPLETED, FAILED.
    """
    # The generationstatus enum should already exist from add_generation_status migration
    # Just need to add the column to microcycles table

    # Check if the column already exists in the microcycles table
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('microcycles')]

    if 'generation_status' not in columns:
        # Add the column with server_default='PENDING'
        op.add_column(
            'microcycles',
            sa.Column(
                'generation_status',
                ENUM('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='generationstatus', create_type=False),
                nullable=False,
                server_default='PENDING'
            )
        )


def downgrade() -> None:
    """Downgrade schema.

    Remove generation_status column from microcycles table.
    """
    # Drop the column if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('microcycles')]

    if 'generation_status' in columns:
        op.drop_column('microcycles', 'generation_status')
