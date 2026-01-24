"""Add fatigue and anatomy tables

Revision ID: def012345678
Revises: cd3456ef7890
Create Date: 2026-01-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "def012345678"
down_revision: Union[str, Sequence[str], None] = "cd3456ef7890"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Define enums
    muscle_role_enum = sa.Enum("PRIMARY", "SECONDARY", "STABILIZER", name="musclerole")

    if not inspector.has_table("muscles"):
        op.create_table(
            "muscles",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("slug", sa.String(length=100), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("region", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
        op.create_index(op.f("ix_muscles_slug"), "muscles", ["slug"], unique=True)

    if not inspector.has_table("movement_muscle_map"):
        op.create_table(
            "movement_muscle_map",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("movement_id", sa.Integer(), nullable=False),
            sa.Column("muscle_id", sa.Integer(), nullable=False),
            sa.Column("role", muscle_role_enum, nullable=False),
            sa.Column("magnitude", sa.Float(), nullable=False),
            sa.ForeignKeyConstraint(["movement_id"], ["movements.id"]),
            sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("movement_id", "muscle_id", "role", name="uq_movement_muscle_role"),
        )
        op.create_index(op.f("ix_movement_muscle_map_movement_id"), "movement_muscle_map", ["movement_id"], unique=False)
        op.create_index(op.f("ix_movement_muscle_map_muscle_id"), "movement_muscle_map", ["muscle_id"], unique=False)
        op.create_index(op.f("ix_movement_muscle_map_role"), "movement_muscle_map", ["role"], unique=False)

    if not inspector.has_table("activity_muscle_map"):
        op.create_table(
            "activity_muscle_map",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("activity_definition_id", sa.Integer(), nullable=False),
            sa.Column("muscle_id", sa.Integer(), nullable=False),
            sa.Column("magnitude", sa.Float(), nullable=False),
            sa.Column("cns_impact", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["activity_definition_id"], ["activity_definitions.id"]),
            sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("activity_definition_id", "muscle_id", name="uq_activity_muscle"),
        )
        op.create_index(op.f("ix_activity_muscle_map_activity_definition_id"), "activity_muscle_map", ["activity_definition_id"], unique=False)
        op.create_index(op.f("ix_activity_muscle_map_muscle_id"), "activity_muscle_map", ["muscle_id"], unique=False)

    if not inspector.has_table("user_fatigue_state"):
        op.create_table(
            "user_fatigue_state",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("muscle_id", sa.Integer(), nullable=False),
            sa.Column("fatigue_score", sa.Float(), nullable=False),
            sa.Column("computed_from", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["muscle_id"], ["muscles.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "date", "muscle_id", name="uq_user_fatigue_state"),
        )
        op.create_index(op.f("ix_user_fatigue_state_date"), "user_fatigue_state", ["date"], unique=False)
        op.create_index(op.f("ix_user_fatigue_state_muscle_id"), "user_fatigue_state", ["muscle_id"], unique=False)
        op.create_index(op.f("ix_user_fatigue_state_user_id"), "user_fatigue_state", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_fatigue_state_user_id"), table_name="user_fatigue_state")
    op.drop_index(op.f("ix_user_fatigue_state_muscle_id"), table_name="user_fatigue_state")
    op.drop_index(op.f("ix_user_fatigue_state_date"), table_name="user_fatigue_state")
    op.drop_table("user_fatigue_state")

    op.drop_index(op.f("ix_activity_muscle_map_muscle_id"), table_name="activity_muscle_map")
    op.drop_index(op.f("ix_activity_muscle_map_activity_definition_id"), table_name="activity_muscle_map")
    op.drop_table("activity_muscle_map")

    op.drop_index(op.f("ix_movement_muscle_map_role"), table_name="movement_muscle_map")
    op.drop_index(op.f("ix_movement_muscle_map_muscle_id"), table_name="movement_muscle_map")
    op.drop_index(op.f("ix_movement_muscle_map_movement_id"), table_name="movement_muscle_map")
    op.drop_table("movement_muscle_map")

    op.drop_index(op.f("ix_muscles_slug"), table_name="muscles")
    op.drop_table("muscles")
