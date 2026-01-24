"""add max_session_duration to programs

Revision ID: 11d05e914447
Revises: bd7af9fae4b9
Create Date: 2026-01-20 16:28:39.299481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11d05e914447'
down_revision: Union[str, Sequence[str], None] = 'bd7af9fae4b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('programs', sa.Column('max_session_duration', sa.Integer(), nullable=False, server_default='60'))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('programs', 'max_session_duration')
