"""merge_program_generation_heads

Revision ID: merge_program_gen_heads
Revises: add_program_gen_progress, merge_opt_heads
Create Date: 2026-02-12 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'merge_program_gen_heads'
down_revision: Union[str, Sequence[str], None] = ('add_program_gen_progress', 'merge_opt_heads')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge branches."""
    pass


def downgrade() -> None:
    """Unmerge branches."""
    pass
