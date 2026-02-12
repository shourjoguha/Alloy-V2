"""add_role_column_to_users

Revision ID: 1d490889b1ef
Revises: 246ad2055faf
Create Date: 2026-02-11 03:16:29.489958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

revision: str = '1d490889b1ef'
down_revision: Union[str, Sequence[str], None] = '246ad2055faf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    user_role_enum = ENUM('user', 'admin', name='userrole', create_type=False)
    user_role_enum.create(op.get_bind())
    
    op.add_column('users', sa.Column('role', user_role_enum, nullable=True, server_default='user'))
    op.alter_column('users', 'role', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'role')
    user_role_enum = ENUM('user', 'admin', name='userrole', create_type=False)
    user_role_enum.drop(op.get_bind())
