"""phase4_step1_add_gin_indexes_btree_and_embeddings

Revision ID: phase4_step1
Revises: 82c02a09d89a
Create Date: 2026-01-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY


# revision identifiers, used by Alembic.
revision: str = 'phase4_step1'
down_revision: Union[str, Sequence[str], None] = '82c02a09d89a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add GIN indexes for JSONB, B-Tree composite indexes, and embedding support."""
    
    # Step 1: Add embedding_description column to movements table
    op.add_column('movements', sa.Column(
        'embedding_description',
        sa.Text(),
        nullable=True
    ))
    
    # Step 2: Add embedding_vector column using ARRAY (pgvector optional for future)
    op.add_column('movements', sa.Column(
        'embedding_vector',
        ARRAY(sa.Float()),
        nullable=True
    ))
    
    # Step 3: Create GIN index for biomechanics_profile JSONB column
    # This enables efficient queries like: biomechanics_profile @> '{"stability": "high"}'
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movements_biomechanics_profile_gin "
        "ON movements USING GIN (biomechanics_profile)"
    )
    
    # Step 4: Create composite B-Tree indexes for common filter patterns
    
    # Index for user-specific movement queries (filter by user and pattern)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movements_user_pattern "
        "ON movements (user_id, pattern)"
    )
    
    # Index for pattern and muscle filtering (common search pattern)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movements_pattern_muscle "
        "ON movements (pattern, primary_muscle)"
    )
    
    # Index for skill level and compound filtering (workout planning)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movements_skill_compound "
        "ON movements (skill_level, compound)"
    )
    
    # Index for tier and metabolic demand filtering (movement selection)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movements_tier_metabolic "
        "ON movements (tier, metabolic_demand)"
    )
    
    # Index for substitution group lookups (movement replacement logic)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movements_substitution_group "
        "ON movements (substitution_group) WHERE substitution_group IS NOT NULL"
    )
    
    # Index for movement_relationships composite queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movement_relationships_source_type "
        "ON movement_relationships (source_movement_id, relationship_type)"
    )
    
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movement_relationships_target_type "
        "ON movement_relationships (target_movement_id, relationship_type)"
    )
    
    # Index for movement_muscle_map composite queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movement_muscle_map_movement_role "
        "ON movement_muscle_map (movement_id, role)"
    )
    
    # Index for movement_disciplines composite queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movement_disciplines_movement_discipline "
        "ON movement_disciplines (movement_id, discipline)"
    )
    
    # Index for pattern_exposures time-series queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pattern_exposures_user_pattern_date "
        "ON pattern_exposures (user_id, pattern, date DESC)"
    )
    
    # Index for top_set_logs PR tracking queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_top_set_logs_movement_user_date "
        "ON top_set_logs (movement_id, created_at DESC)"
    )


def downgrade() -> None:
    """Remove indexes and embedding support."""
    
    # Drop indexes in reverse order
    op.drop_index('idx_top_set_logs_movement_user_date', table_name='top_set_logs')
    op.drop_index('idx_pattern_exposures_user_pattern_date', table_name='pattern_exposures')
    op.drop_index('idx_movement_disciplines_movement_discipline', table_name='movement_disciplines')
    op.drop_index('idx_movement_muscle_map_movement_role', table_name='movement_muscle_map')
    op.drop_index('idx_movement_relationships_target_type', table_name='movement_relationships')
    op.drop_index('idx_movement_relationships_source_type', table_name='movement_relationships')
    op.drop_index('idx_movements_substitution_group', table_name='movements')
    op.drop_index('idx_movements_tier_metabolic', table_name='movements')
    op.drop_index('idx_movements_skill_compound', table_name='movements')
    op.drop_index('idx_movements_pattern_muscle', table_name='movements')
    op.drop_index('idx_movements_user_pattern', table_name='movements')
    op.drop_index('idx_movements_biomechanics_profile_gin', table_name='movements')
    
    # Drop embedding columns
    op.drop_column('movements', 'embedding_vector')
    op.drop_column('movements', 'embedding_description')
