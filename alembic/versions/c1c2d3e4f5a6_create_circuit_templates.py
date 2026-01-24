"""Create circuit templates table

Revision ID: c1c2d3e4f5a6
Revises: b2c3d4e5f6a7
Create Date: 2026-01-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    circuit_type_enum = sa.Enum(
        "ROUNDS_FOR_TIME",
        "AMRAP",
        "EMOM",
        "LADDER",
        "TABATA",
        "CHIPPER",
        "STATION",
        name="circuittype",
    )

    op.create_table(
        "circuit_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("circuit_type", circuit_type_enum, nullable=False),
        sa.Column("exercises_json", sa.JSON(), nullable=False),
        sa.Column("default_rounds", sa.Integer(), nullable=True),
        sa.Column("default_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("bucket_stress", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("difficulty_tier", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_circuit_templates_name"), "circuit_templates", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_circuit_templates_name"), table_name="circuit_templates")
    op.drop_table("circuit_templates")

