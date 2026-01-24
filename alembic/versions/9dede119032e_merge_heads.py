"""merge_heads

Revision ID: 9dede119032e
Revises: 8e2f9f052d17, custom_session_support
Create Date: 2026-01-22 14:45:41.438099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9dede119032e'
down_revision: Union[str, Sequence[str], None] = ('8e2f9f052d17', 'custom_session_support')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
