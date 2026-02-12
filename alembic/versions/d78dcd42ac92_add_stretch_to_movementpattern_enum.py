"""add_stretch_to_movementpattern_enum

Revision ID: d78dcd42ac92
Revises: add_equipment_available
Create Date: 2026-02-09 21:00:09.017050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd78dcd42ac92'
down_revision: Union[str, Sequence[str], None] = 'add_equipment_available'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Add 'stretch' to MovementPattern enum.
    This allows proper classification of stretching exercises separate from mobility.
    """
    
    # Check if 'stretch' already exists in enum (from previous migration)
    # If not, add it. If it exists, skip the enum addition.
    # This handles the case where the enum was already updated via manual intervention
    # or the old migration file (662e6fe73056) was already applied.
    from sqlalchemy import text
    
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT 1 
        FROM pg_enum 
        JOIN pg_type ON pg_enum.enumtypid = pg_type.oid 
        WHERE pg_type.typname = 'movementpattern' 
        AND pg_enum.enumlabel = 'stretch'
    """))
    
    if result.scalar() is None:
        # 'stretch' doesn't exist, add it
        op.execute("""
            ALTER TYPE movementpattern 
            ADD VALUE 'stretch' AFTER 'mobility'
        """)
    
    # Migrate movements that should be 'stretch' instead of 'mobility'
    # Identify movements with "stretch" in their name
    op.execute("""
        UPDATE movements 
        SET pattern = 'stretch'
        WHERE pattern = 'mobility'
        AND (
            name ILIKE '%stretch%'
            OR name ILIKE '%Stretch%'
        )
    """)


def downgrade() -> None:
    """Downgrade schema.
    
    Rollback the stretch enum addition.
    Note: PostgreSQL doesn't support removing enum values directly,
    so we can only revert the data migration.
    """
    
    # Revert stretch movements back to mobility
    op.execute("""
        UPDATE movements 
        SET pattern = 'mobility'
        WHERE pattern = 'stretch'
    """)
    
    # Note: We cannot remove 'stretch' from the enum type in PostgreSQL
    # without recreating the entire type, which is a complex operation
    # that requires dropping and recreating all dependent columns/tables
