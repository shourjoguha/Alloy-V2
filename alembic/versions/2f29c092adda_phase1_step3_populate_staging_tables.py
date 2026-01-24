"""phase1_step3_populate_staging_tables

Revision ID: 2f29c092adda
Revises: c1c9ff760036
Create Date: 2026-01-23 15:53:40.994407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f29c092adda'
down_revision: Union[str, Sequence[str], None] = 'c1c9ff760036'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Phase 1 Step 3: Populate Staging Tables
    - Migrate movements data to stg_movements
    - Migrate session_exercises data to stg_session_exercises (unified exercise_role)
    """
    
    # Migrate movements data to staging table
    op.execute("""
        INSERT INTO stg_movements (
            id, name, pattern, primary_muscle, primary_region,
            cns_load, skill_level, compound, is_complex_lift, is_unilateral,
            metric_type, description, substitution_group, user_id,
            fatigue_factor, stimulus_factor, injury_risk_factor,
            min_recovery_hours, block_type, spinal_compression
        )
        SELECT 
            id, name, pattern, primary_muscle, primary_region,
            cns_load, skill_level, compound, is_complex_lift, is_unilateral,
            metric_type, description, substitution_group, user_id,
            fatigue_factor, stimulus_factor, injury_risk_factor,
            min_recovery_hours, block_type, spinal_compression
        FROM movements
    """)
    
    # Migrate session_exercises data to staging table with unified exercise_role
    # Use 'role' as exercise_role since it matches the unified ExerciseRole enum
    op.execute("""
        INSERT INTO stg_session_exercises (
            id, session_id, movement_id, exercise_role,
            order_in_session, superset_group, target_sets,
            target_rep_range_min, target_rep_range_max, target_rpe,
            target_rir, target_duration_seconds, default_rest_seconds,
            is_complex_lift, substitution_allowed, notes, user_id,
            stimulus, fatigue, circuit_id
        )
        SELECT 
            id, session_id, movement_id, role::exerciserole,
            order_in_session, superset_group, target_sets,
            target_rep_range_min, target_rep_range_max, target_rpe,
            target_rir, target_duration_seconds, default_rest_seconds,
            is_complex_lift, substitution_allowed, notes, user_id,
            stimulus, fatigue, circuit_id
        FROM session_exercises
    """)


def downgrade() -> None:
    """Downgrade schema.
    
    Clear staging tables.
    """
    op.execute("DELETE FROM stg_session_exercises")
    op.execute("DELETE FROM stg_movements")
