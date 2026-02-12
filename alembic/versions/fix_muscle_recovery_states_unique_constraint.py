"""fix_muscle_recovery_states_unique_constraint

Revision ID: f1a2b3c4d5e6
Revises: 2e3f4a5b6c7d
Create Date: 2026-02-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '2e3f4a5b6c7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - fix unique constraint to support multi-user system."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Check if the old unique constraint exists on 'muscle' column
    existing_constraints = [con['name'] for con in inspector.get_unique_constraints('muscle_recovery_states')]
    
    # Drop old unique constraint on 'muscle' column if it exists
    # The constraint might be named 'uq_muscle_recovery_states_muscle' or similar
    for constraint_name in existing_constraints:
        if constraint_name and 'muscle' in constraint_name.lower():
            op.drop_constraint(constraint_name, 'muscle_recovery_states', type_='unique')
            break
    
    # Add composite unique constraint on (user_id, muscle)
    op.create_unique_constraint(
        'uq_user_muscle_recovery_state',
        'muscle_recovery_states',
        ['user_id', 'muscle']
    )


def downgrade() -> None:
    """Downgrade schema - revert to single unique constraint on muscle."""
    # Drop composite unique constraint
    op.drop_constraint('uq_user_muscle_recovery_state', 'muscle_recovery_states', type_='unique')
    
    # Re-add unique constraint on 'muscle' column alone
    op.create_unique_constraint(
        'uq_muscle_recovery_states_muscle',
        'muscle_recovery_states',
        ['muscle']
    )
