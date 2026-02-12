"""merge_movement_optimization_heads

Revision ID: merge_opt_heads
Revises: g3h4i5j6k7l8, optimize_movement_queries
Create Date: 2026-02-12 01:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_opt_heads'
down_revision: Union[str, Sequence[str], None] = ('g3h4i5j6k7l8', 'optimize_movement_queries')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge branches."""
    pass


def downgrade() -> None:
    """Unmerge branches."""
    pass
