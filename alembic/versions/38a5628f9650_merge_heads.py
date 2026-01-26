"""merge_heads

Revision ID: 38a5628f9650
Revises: add_user_auth, fix_persona_enum_types
Create Date: 2026-01-26 02:01:25.618701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38a5628f9650'
down_revision: Union[str, Sequence[str], None] = ('add_user_auth', 'fix_persona_enum_types')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
