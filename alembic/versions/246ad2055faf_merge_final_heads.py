"""merge final heads

Revision ID: 246ad2055faf
Revises: add_2fa_support, add_micro_phase_rpe
Create Date: 2026-02-11 02:49:46.856970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '246ad2055faf'
down_revision: Union[str, Sequence[str], None] = ('add_2fa_support', 'add_micro_phase_rpe')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
