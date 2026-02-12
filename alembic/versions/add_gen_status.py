"""add_generation_status_to_sessions

Revision ID: add_gen_status
Revises: a1b2c3d4e5f6
Create Date: 2026-02-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = 'add_gen_status'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Add generation_status column to sessions table with 'PENDING' as default value.
    The column is an ENUM with possible values: PENDING, IN_PROGRESS, COMPLETED, FAILED.
    """
    # Create the generation_status enum type if it doesn't exist
    # Check if enum type already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if enum type exists in PostgreSQL
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'generationstatus'")
    ).fetchone()

    if not result:
        # Create the enum type
        generationstatus_enum = ENUM(
            'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED',
            name='generationstatus',
            create_type=True
        )
        generationstatus_enum.create(conn, checkfirst=True)

    # Check if column already exists in sessions table
    columns = [col['name'] for col in inspector.get_columns('sessions')]

    if 'generation_status' not in columns:
        # Add column with server_default='PENDING'
        op.add_column(
            'sessions',
            sa.Column(
                'generation_status',
                sa.Enum('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', name='generationstatus', create_type=False),
                nullable=False,
                server_default='PENDING'
            )
        )


def downgrade() -> None:
    """Downgrade schema.

    Remove generation_status column from sessions table.
    """
    # Drop the column if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('sessions')]
    
    if 'generation_status' in columns:
        op.drop_column('sessions', 'generation_status')
    
    # Drop the enum type if it exists
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'generationstatus'")
    ).fetchone()
    
    if result:
        op.execute("DROP TYPE generationstatus")
