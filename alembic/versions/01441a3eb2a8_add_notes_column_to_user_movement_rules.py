"""add_notes_column_to_user_movement_rules

Revision ID: 01441a3eb2a8
Revises: d78dcd42ac92
Create Date: 2026-02-09 21:08:20.100550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01441a3eb2a8'
down_revision: Union[str, Sequence[str], None] = 'd78dcd42ac92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add notes column to user_movement_rules table if it doesn't already exist
    # Check if column exists first
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('user_movement_rules')]
    
    if 'notes' not in columns:
        op.add_column('user_movement_rules', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove notes column from user_movement_rules table if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('user_movement_rules')]
    
    if 'notes' in columns:
        op.drop_column('user_movement_rules', 'notes')
