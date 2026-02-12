"""optimize_movement_discipline_queries

Revision ID: optimize_movement_queries
Revises: 246ad2055faf
Create Date: 2026-02-12 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'optimize_movement_queries'
down_revision: str = '246ad2055faf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add indexes to optimize UserMovementRule queries for cardio detection.
    Uses proper join through MovementDiscipline table.
    """
    
    # Step 1: Create composite index for UserMovementRule queries
    # This optimizes the join between UserMovementRule and Movement tables
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_movement_rules_user_rule "
        "ON user_movement_rules (user_id, rule_type)"
    )
    
    # Step 2: Create index on movement_id for fast joins
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_movement_rules_movement_id "
        "ON user_movement_rules (movement_id)"
    )
    
    # Step 3: MovementDiscipline already has index on discipline column
    # (defined in movement.py: discipline = Column(..., index=True))
    # No additional index needed


def downgrade() -> None:
    """Remove indexes."""
    
    op.drop_index('idx_user_movement_rules_movement_id', table_name='user_movement_rules')
    op.drop_index('idx_user_movement_rules_user_rule', table_name='user_movement_rules')
