"""phase2_step1_drop_muscles_name_column

Revision ID: d85b37d662b7
Revises: phase1_step6_cleanup
Create Date: 2026-01-23 18:20:35.272577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd85b37d662b7'
down_revision: Union[str, Sequence[str], None] = 'phase1_step6_cleanup'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('muscles', 'name')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('muscles', sa.Column('name', sa.String(200), nullable=False))
    op.execute("""
        UPDATE muscles 
        SET name = REPLACE(REPLACE(slug, '_', ' '), 'lower body', 'Lower Body')
    """)
