"""add block type to movements

Placeholder migration to restore broken dependency chain.
Original migration was deleted but is referenced by 20a4abf61a67_fix_exerciserole_enum_case.py.

Revision ID: 8e2f9f052d17
Create Date: 2026-02-12 (placeholder)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '8e2f9f052d17'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Placeholder - actual changes already exist in database."""
    pass


def downgrade() -> None:
    """Placeholder."""
    pass
