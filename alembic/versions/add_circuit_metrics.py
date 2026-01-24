"""Add normalized metrics to circuit templates

Revision ID: add_circuit_metrics
Revises: 11d05e914447
Create Date: 2026-01-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_circuit_metrics"
down_revision: Union[str, Sequence[str], None] = "11d05e914447"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("circuit_templates", sa.Column("fatigue_factor", sa.Float(), nullable=False, server_default="1.0"))
    op.add_column("circuit_templates", sa.Column("stimulus_factor", sa.Float(), nullable=False, server_default="1.0"))
    op.add_column("circuit_templates", sa.Column("min_recovery_hours", sa.Integer(), nullable=False, server_default="24"))
    op.add_column("circuit_templates", sa.Column("muscle_volume", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("circuit_templates", sa.Column("muscle_fatigue", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("circuit_templates", sa.Column("total_reps", sa.Integer(), nullable=True))
    op.add_column("circuit_templates", sa.Column("estimated_work_seconds", sa.Integer(), nullable=True))
    op.add_column("circuit_templates", sa.Column("effective_work_volume", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("circuit_templates", "effective_work_volume")
    op.drop_column("circuit_templates", "estimated_work_seconds")
    op.drop_column("circuit_templates", "total_reps")
    op.drop_column("circuit_templates", "muscle_fatigue")
    op.drop_column("circuit_templates", "muscle_volume")
    op.drop_column("circuit_templates", "min_recovery_hours")
    op.drop_column("circuit_templates", "stimulus_factor")
    op.drop_column("circuit_templates", "fatigue_factor")
