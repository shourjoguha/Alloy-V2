"""phase1_step1_enum_sync

Revision ID: ebaa3499c4af
Revises: 970301065e1d
Create Date: 2026-01-23 15:39:46.725956

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ebaa3499c4af'
down_revision: Union[str, Sequence[str], None] = '970301065e1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Phase 1 Step 1: Enum Synchronization
    - Add 'core' to PrimaryRegion enum
    - Add 'skill' to SessionSection enum (for unification with ExerciseRole)
    """
    
    # Update PrimaryRegion enum to include 'core'
    op.execute("""
        ALTER TYPE primaryregion 
        ADD VALUE 'core' AFTER 'upper body'
    """)
    
    # Update SessionSection enum to include 'skill'
    op.execute("""
        ALTER TYPE sessionsection 
        ADD VALUE 'skill' AFTER 'accessory'
    """)


def downgrade() -> None:
    """Downgrade schema.
    
    Rollback Phase 1 Step 1 enum changes.
    """
    
    # Note: PostgreSQL doesn't support removing enum values directly
    # We would need to recreate the type without the new values
    # This is a known limitation; for production, consider creating new types
    
    pass
