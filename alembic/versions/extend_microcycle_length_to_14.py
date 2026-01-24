"""Extend microcycle length to 14 days

Revision ID: extend_microcycle_length_to_14
Revises: add_circuit_metrics
Create Date: 2026-01-21

"""

from typing import Sequence, Union

from alembic import op


revision: str = "extend_microcycle_length_to_14"
down_revision: Union[str, Sequence[str], None] = "add_circuit_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("microcycles") as batch_op:
        batch_op.drop_constraint("valid_length", type_="check")
        batch_op.create_check_constraint(
            "valid_length",
            "length_days >= 7 AND length_days <= 14",
        )


def downgrade() -> None:
    with op.batch_alter_table("microcycles") as batch_op:
        batch_op.drop_constraint("valid_length", type_="check")
        batch_op.create_check_constraint(
            "valid_length",
            "length_days >= 7 AND length_days <= 10",
        )
