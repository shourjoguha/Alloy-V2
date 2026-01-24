"""Add user profile preferences

Revision ID: 1a2b3c4d5e6f
Revises: ef3456789abc
Create Date: 2026-01-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = 'ef3456789abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.add_column(sa.Column("discipline_preferences", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("scheduling_preferences", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_column("scheduling_preferences")
        batch_op.drop_column("discipline_preferences")
