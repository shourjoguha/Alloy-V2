"""phase1_step2_staging_and_bridge_tables

Revision ID: c1c9ff760036
Revises: ebaa3499c4af
Create Date: 2026-01-23 15:46:09.735002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1c9ff760036'
down_revision: Union[str, Sequence[str], None] = 'ebaa3499c4af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Phase 1 Step 2: Create Staging Tables
    - Create stg_movements (staging table for movements data migration)
    - Create stg_session_exercises (staging table for session_exercises data migration)
    
    Note: Bridge tables (muscles, movement_muscle_map, tags, movement_tags) already exist.
    """
    
    # Create staging table for movements with refactored schema
    op.execute("""
        CREATE TABLE stg_movements (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            pattern movementpattern NOT NULL,
            primary_muscle primarymuscle NOT NULL,
            primary_region primaryregion NOT NULL,
            cns_load cnsload NOT NULL,
            skill_level skilllevel NOT NULL,
            compound BOOLEAN,
            is_complex_lift BOOLEAN,
            is_unilateral BOOLEAN,
            metric_type metrictype NOT NULL,
            description TEXT,
            substitution_group VARCHAR(100),
            user_id INTEGER REFERENCES users(id),
            fatigue_factor DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            stimulus_factor DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            injury_risk_factor DOUBLE PRECISION NOT NULL DEFAULT 1.0,
            min_recovery_hours INTEGER NOT NULL DEFAULT 24,
            block_type VARCHAR(50) NOT NULL DEFAULT 'All',
            spinal_compression spinalcompression NOT NULL DEFAULT 'none'
        )
    """)
    
    # Create staging table for session_exercises with unified exercise_role
    op.execute("""
        CREATE TABLE stg_session_exercises (
            id INTEGER PRIMARY KEY,
            session_id INTEGER NOT NULL,
            movement_id INTEGER NOT NULL,
            exercise_role exerciserole NOT NULL,
            order_in_session INTEGER NOT NULL,
            superset_group INTEGER,
            target_sets INTEGER NOT NULL,
            target_rep_range_min INTEGER,
            target_rep_range_max INTEGER,
            target_rpe DOUBLE PRECISION,
            target_rir INTEGER,
            target_duration_seconds INTEGER,
            default_rest_seconds INTEGER,
            is_complex_lift BOOLEAN,
            substitution_allowed BOOLEAN,
            notes TEXT,
            user_id INTEGER REFERENCES users(id),
            stimulus DOUBLE PRECISION,
            fatigue DOUBLE PRECISION,
            circuit_id INTEGER REFERENCES circuit_templates(id)
        )
    """)


def downgrade() -> None:
    """Downgrade schema.
    
    Drop staging tables.
    """
    op.execute("DROP TABLE IF EXISTS stg_session_exercises")
    op.execute("DROP TABLE IF EXISTS stg_movements")
