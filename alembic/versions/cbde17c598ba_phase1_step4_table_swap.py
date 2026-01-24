"""phase1_step4_table_swap

Revision ID: cbde17c598ba
Revises: 2f29c092adda
Create Date: 2026-01-23 15:56:52.007839

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cbde17c598ba'
down_revision: Union[str, Sequence[str], None] = '2f29c092adda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.
    
    Phase 1 Step 4: Table Swap
    - Drop foreign key constraints on dependent tables
    - Rename production tables to old_ (movements -> old_movements, session_exercises -> old_session_exercises)
    - Rename staging tables to production (stg_movements -> movements, stg_session_exercises -> session_exercises)
    - Re-create foreign key constraints on dependent tables
    """
    
    # Step 1: Drop foreign key constraints from dependent tables
    op.execute("ALTER TABLE session_exercises DROP CONSTRAINT session_exercises_movement_id_fkey")
    op.execute("ALTER TABLE session_exercises DROP CONSTRAINT session_exercises_session_id_fkey")
    op.execute("ALTER TABLE session_exercises DROP CONSTRAINT session_exercises_circuit_id_fkey")
    op.execute("ALTER TABLE movement_disciplines DROP CONSTRAINT movement_disciplines_movement_id_fkey")
    op.execute("ALTER TABLE movement_equipment DROP CONSTRAINT movement_equipment_movement_id_fkey")
    op.execute("ALTER TABLE movement_coaching_cues DROP CONSTRAINT movement_coaching_cues_movement_id_fkey")
    
    # Step 2: Rename production tables to old_
    op.execute("ALTER TABLE movements RENAME TO old_movements")
    op.execute("ALTER TABLE session_exercises RENAME TO old_session_exercises")
    
    # Step 3: Rename staging tables to production
    op.execute("ALTER TABLE stg_movements RENAME TO movements")
    op.execute("ALTER TABLE stg_session_exercises RENAME TO session_exercises")
    
    # Step 4: Re-create foreign key constraints with correct table references
    op.execute("ALTER TABLE session_exercises ADD CONSTRAINT session_exercises_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE session_exercises ADD CONSTRAINT session_exercises_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE session_exercises ADD CONSTRAINT session_exercises_circuit_id_fkey FOREIGN KEY (circuit_id) REFERENCES circuit_templates(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE movement_disciplines ADD CONSTRAINT movement_disciplines_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE movement_equipment ADD CONSTRAINT movement_equipment_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE movement_coaching_cues ADD CONSTRAINT movement_coaching_cues_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")


def downgrade() -> None:
    """Downgrade schema.
    
    Reverse table swap:
    - Drop foreign key constraints
    - Rename staging tables back to stg_
    - Rename old_ tables back to production
    - Re-create foreign key constraints
    """
    
    # Step 1: Drop foreign key constraints
    op.execute("ALTER TABLE session_exercises DROP CONSTRAINT session_exercises_movement_id_fkey")
    op.execute("ALTER TABLE session_exercises DROP CONSTRAINT session_exercises_session_id_fkey")
    op.execute("ALTER TABLE session_exercises DROP CONSTRAINT session_exercises_circuit_id_fkey")
    op.execute("ALTER TABLE movement_disciplines DROP CONSTRAINT movement_disciplines_movement_id_fkey")
    op.execute("ALTER TABLE movement_equipment DROP CONSTRAINT movement_equipment_movement_id_fkey")
    op.execute("ALTER TABLE movement_coaching_cues DROP CONSTRAINT movement_coaching_cues_movement_id_fkey")
    
    # Step 2: Rename production tables (which were staging) back to stg_
    op.execute("ALTER TABLE movements RENAME TO stg_movements")
    op.execute("ALTER TABLE session_exercises RENAME TO stg_session_exercises")
    
    # Step 3: Rename old_ tables back to production
    op.execute("ALTER TABLE old_movements RENAME TO movements")
    op.execute("ALTER TABLE old_session_exercises RENAME TO session_exercises")
    
    # Step 4: Re-create foreign key constraints
    op.execute("ALTER TABLE session_exercises ADD CONSTRAINT session_exercises_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE session_exercises ADD CONSTRAINT session_exercises_session_id_fkey FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE session_exercises ADD CONSTRAINT session_exercises_circuit_id_fkey FOREIGN KEY (circuit_id) REFERENCES circuit_templates(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE movement_disciplines ADD CONSTRAINT movement_disciplines_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE movement_equipment ADD CONSTRAINT movement_equipment_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE movement_coaching_cues ADD CONSTRAINT movement_coaching_cues_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")
