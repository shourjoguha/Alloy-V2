"""phase4_step2_add_pgvector_support

Revision ID: phase4_step2
Revises: phase4_step1
Create Date: 2026-01-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = 'phase4_step2'
down_revision: Union[str, Sequence[str], None] = 'phase4_step1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pgvector extension and convert embedding_vector to use pgvector."""
    
    # Step 1: Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Step 2: Convert embedding_vector from ARRAY(Float) to vector(1536)
    # First, check the dimension of existing vectors
    result = op.get_bind().execute(text("""
        SELECT array_length(embedding_vector, 1) as dim
        FROM movements
        WHERE embedding_vector IS NOT NULL
        LIMIT 1
    """)).fetchone()
    
    dimension = 1536  # Default dimension for many embedding models
    if result and result.dim:
        dimension = result.dim
    
    # Step 3: Create a temporary vector column
    op.execute(f"ALTER TABLE movements ADD COLUMN IF NOT EXISTS embedding_vector_tmp vector({dimension})")
    
    # Step 4: Copy data from array to vector
    op.execute("""
        UPDATE movements
        SET embedding_vector_tmp = embedding_vector::vector
        WHERE embedding_vector IS NOT NULL
    """)
    
    # Step 5: Drop old array column
    op.drop_column('movements', 'embedding_vector')
    
    # Step 6: Rename temporary column to embedding_vector
    op.alter_column('movements', 'embedding_vector_tmp', new_column_name='embedding_vector')
    
    # Step 7: Create ivfflat index for efficient similarity search
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_movements_embedding_vector_ivfflat
        ON movements USING ivfflat (embedding_vector vector_cosine_ops)
        WITH (lists = 100)
    """)
    
    # Step 8: Create HNSW index as alternative (faster for high-dimensional vectors)
    op.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_movements_embedding_vector_hnsw
        ON movements USING hnsw (embedding_vector vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Remove pgvector extension and revert to array type."""
    
    # Drop indexes
    op.drop_index('idx_movements_embedding_vector_hnsw', table_name='movements')
    op.drop_index('idx_movements_embedding_vector_ivfflat', table_name='movements')
    
    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")
