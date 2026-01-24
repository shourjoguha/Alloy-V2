"""Update remaining foreign key constraints after table swap.

This migration fixes the foreign key constraints that were missed
during the table swap in Step 4. The following tables still have
constraints pointing to old_movements instead of movements:

- movement_muscle_map
- movement_relationships (source_movement_id, target_movement_id)
- movement_tags
- top_set_logs
- user_movement_rules

After fixing the constraints, we can safely drop the old_ and stg_ tables.

Revision ID: phase1_step5_fix_fk
Revises: cbde17c598ba
Create Date: 2026-01-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'phase1_step5_fix_fk'
down_revision = 'cbde17c598ba'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Update foreign key constraints to point to production tables."""
    
    # Update movement_muscle_map
    op.execute("ALTER TABLE movement_muscle_map DROP CONSTRAINT movement_muscle_map_movement_id_fkey")
    op.execute("ALTER TABLE movement_muscle_map ADD CONSTRAINT movement_muscle_map_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    
    # Update movement_relationships (source_movement_id)
    op.execute("ALTER TABLE movement_relationships DROP CONSTRAINT movement_relationships_source_movement_id_fkey")
    op.execute("ALTER TABLE movement_relationships ADD CONSTRAINT movement_relationships_source_movement_id_fkey FOREIGN KEY (source_movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    
    # Update movement_relationships (target_movement_id)
    op.execute("ALTER TABLE movement_relationships DROP CONSTRAINT movement_relationships_target_movement_id_fkey")
    op.execute("ALTER TABLE movement_relationships ADD CONSTRAINT movement_relationships_target_movement_id_fkey FOREIGN KEY (target_movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    
    # Update movement_tags
    op.execute("ALTER TABLE movement_tags DROP CONSTRAINT movement_tags_movement_id_fkey")
    op.execute("ALTER TABLE movement_tags ADD CONSTRAINT movement_tags_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    
    # Update top_set_logs
    op.execute("ALTER TABLE top_set_logs DROP CONSTRAINT top_set_logs_movement_id_fkey")
    op.execute("ALTER TABLE top_set_logs ADD CONSTRAINT top_set_logs_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")
    
    # Update user_movement_rules
    op.execute("ALTER TABLE user_movement_rules DROP CONSTRAINT user_movement_rules_movement_id_fkey")
    op.execute("ALTER TABLE user_movement_rules ADD CONSTRAINT user_movement_rules_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES movements(id) ON DELETE CASCADE")


def downgrade() -> None:
    """Revert foreign key constraints to point to old_ tables."""
    
    # Revert movement_muscle_map
    op.execute("ALTER TABLE movement_muscle_map DROP CONSTRAINT movement_muscle_map_movement_id_fkey")
    op.execute("ALTER TABLE movement_muscle_map ADD CONSTRAINT movement_muscle_map_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES old_movements(id) ON DELETE CASCADE")
    
    # Revert movement_relationships (source_movement_id)
    op.execute("ALTER TABLE movement_relationships DROP CONSTRAINT movement_relationships_source_movement_id_fkey")
    op.execute("ALTER TABLE movement_relationships ADD CONSTRAINT movement_relationships_source_movement_id_fkey FOREIGN KEY (source_movement_id) REFERENCES old_movements(id) ON DELETE CASCADE")
    
    # Revert movement_relationships (target_movement_id)
    op.execute("ALTER TABLE movement_relationships DROP CONSTRAINT movement_relationships_target_movement_id_fkey")
    op.execute("ALTER TABLE movement_relationships ADD CONSTRAINT movement_relationships_target_movement_id_fkey FOREIGN KEY (target_movement_id) REFERENCES old_movements(id) ON DELETE CASCADE")
    
    # Revert movement_tags
    op.execute("ALTER TABLE movement_tags DROP CONSTRAINT movement_tags_movement_id_fkey")
    op.execute("ALTER TABLE movement_tags ADD CONSTRAINT movement_tags_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES old_movements(id) ON DELETE CASCADE")
    
    # Revert top_set_logs
    op.execute("ALTER TABLE top_set_logs DROP CONSTRAINT top_set_logs_movement_id_fkey")
    op.execute("ALTER TABLE top_set_logs ADD CONSTRAINT top_set_logs_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES old_movements(id) ON DELETE CASCADE")
    
    # Revert user_movement_rules
    op.execute("ALTER TABLE user_movement_rules DROP CONSTRAINT user_movement_rules_movement_id_fkey")
    op.execute("ALTER TABLE user_movement_rules ADD CONSTRAINT user_movement_rules_movement_id_fkey FOREIGN KEY (movement_id) REFERENCES old_movements(id) ON DELETE CASCADE")
