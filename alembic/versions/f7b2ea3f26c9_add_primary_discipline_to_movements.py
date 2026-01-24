"""add primary_discipline to movements

Revision ID: f7b2ea3f26c9
Revises: b2c3d4e5f6a7
Create Date: 2026-01-16 21:36:37.158295

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b2ea3f26c9'
down_revision: Union[str, Sequence[str], None] = 'c1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("movements") as batch_op:
        batch_op.add_column(
            sa.Column("primary_discipline", sa.String(length=50), server_default="All", nullable=False)
        )

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(sa.Column("main_circuit_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("finisher_circuit_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_sessions_finisher_circuit_id_circuit_templates",
            "circuit_templates",
            ["finisher_circuit_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_sessions_main_circuit_id_circuit_templates",
            "circuit_templates",
            ["main_circuit_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_constraint("fk_sessions_main_circuit_id_circuit_templates", type_="foreignkey")
        batch_op.drop_constraint("fk_sessions_finisher_circuit_id_circuit_templates", type_="foreignkey")
        batch_op.drop_column("finisher_circuit_id")
        batch_op.drop_column("main_circuit_id")

    with op.batch_alter_table("movements") as batch_op:
        batch_op.drop_column("primary_discipline")
