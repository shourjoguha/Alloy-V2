"""Add activity definitions and activity instances

Revision ID: cd3456ef7890
Revises: bc7890ab12cd
Create Date: 2026-01-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cd3456ef7890"
down_revision: Union[str, Sequence[str], None] = "bc7890ab12cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Define enums
    discipline_category_enum = sa.Enum("TRAINING", "SPORT", "RECOVERY", "OTHER", name="disciplinecategory")
    activity_category_enum = sa.Enum("STRENGTH", "CARDIO", "MOBILITY", "SPORT", "RECOVERY", "OTHER", name="activitycategory")
    activity_source_enum = sa.Enum("PLANNED", "MANUAL", "PROVIDER", name="activitysource")
    metric_type_enum = sa.Enum("REPS", "TIME", "TIME_UNDER_TENSION", "DISTANCE", name="metrictype")
    visibility_enum = postgresql.ENUM("PRIVATE", "FRIENDS", "PUBLIC", name="visibility", create_type=False)

    if not inspector.has_table("disciplines"):
        op.create_table(
            "disciplines",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("slug", sa.String(length=100), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("category", discipline_category_enum, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
        op.create_index(op.f("ix_disciplines_slug"), "disciplines", ["slug"], unique=True)

    if not inspector.has_table("activity_definitions"):
        op.create_table(
            "activity_definitions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("category", activity_category_enum, nullable=False),
            sa.Column("discipline_id", sa.Integer(), nullable=True),
            sa.Column("default_metric_type", metric_type_enum, nullable=True),
            sa.Column("default_equipment_tags", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["discipline_id"], ["disciplines.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_activity_definitions_category"), "activity_definitions", ["category"], unique=False)
        op.create_index(op.f("ix_activity_definitions_discipline_id"), "activity_definitions", ["discipline_id"], unique=False)
        op.create_index(op.f("ix_activity_definitions_name"), "activity_definitions", ["name"], unique=False)

    if not inspector.has_table("activity_instances"):
        op.create_table(
            "activity_instances",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("planned_session_id", sa.Integer(), nullable=True),
            sa.Column("source", activity_source_enum, nullable=False),
            sa.Column("activity_definition_id", sa.Integer(), nullable=True),
            sa.Column("performed_start", sa.DateTime(), nullable=True),
            sa.Column("performed_end", sa.DateTime(), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("perceived_difficulty", sa.Integer(), nullable=True),
            sa.Column("enjoyment_rating", sa.Integer(), nullable=True),
            sa.Column("visibility", visibility_enum, nullable=False, server_default="PRIVATE"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["activity_definition_id"], ["activity_definitions.id"]),
            sa.ForeignKeyConstraint(["planned_session_id"], ["sessions.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_activity_instances_activity_definition_id"), "activity_instances", ["activity_definition_id"], unique=False)
        op.create_index(op.f("ix_activity_instances_performed_start"), "activity_instances", ["performed_start"], unique=False)
        op.create_index(op.f("ix_activity_instances_planned_session_id"), "activity_instances", ["planned_session_id"], unique=False)
        op.create_index(op.f("ix_activity_instances_source"), "activity_instances", ["source"], unique=False)
        op.create_index(op.f("ix_activity_instances_user_id"), "activity_instances", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_instances_user_id"), table_name="activity_instances")
    op.drop_index(op.f("ix_activity_instances_source"), table_name="activity_instances")
    op.drop_index(op.f("ix_activity_instances_planned_session_id"), table_name="activity_instances")
    op.drop_index(op.f("ix_activity_instances_performed_start"), table_name="activity_instances")
    op.drop_index(op.f("ix_activity_instances_activity_definition_id"), table_name="activity_instances")
    op.drop_table("activity_instances")

    op.drop_index(op.f("ix_activity_definitions_name"), table_name="activity_definitions")
    op.drop_index(op.f("ix_activity_definitions_discipline_id"), table_name="activity_definitions")
    op.drop_index(op.f("ix_activity_definitions_category"), table_name="activity_definitions")
    op.drop_table("activity_definitions")

    op.drop_index(op.f("ix_disciplines_slug"), table_name="disciplines")
    op.drop_table("disciplines")
