"""add user authentication fields

Revision ID: add_user_auth
Revises: 11d05e914447
Create Date: 2026-01-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = 'add_user_auth'
down_revision: Union[str, Sequence[str], None] = 'phase4_step2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('hashed_password', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('created_at', sa.DateTime(), nullable=False, server_default='now()'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'created_at')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'hashed_password')
