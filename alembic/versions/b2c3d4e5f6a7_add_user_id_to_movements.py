"""Add user_id to movements

Revision ID: b2c3d4e5f6a7
Revises: 6180f4706b14
Create Date: 2026-01-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = '6180f4706b14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("movements") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_index(op.f("ix_movements_user_id"), ["user_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_movements_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("movements") as batch_op:
        batch_op.drop_constraint("fk_movements_user_id_users", type_="foreignkey")
        batch_op.drop_index(op.f("ix_movements_user_id"))
        batch_op.drop_column("user_id")
