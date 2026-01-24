"""Add activity instance links

Revision ID: ef3456789abc
Revises: def012345678
Create Date: 2026-01-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ef3456789abc"
down_revision: Union[str, Sequence[str], None] = "def012345678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table("activity_instance_links"):
        op.create_table(
            "activity_instance_links",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("activity_instance_id", sa.Integer(), nullable=False),
            sa.Column("external_activity_record_id", sa.Integer(), nullable=True),
            sa.Column("workout_log_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["activity_instance_id"], ["activity_instances.id"]),
            sa.ForeignKeyConstraint(["external_activity_record_id"], ["external_activity_records.id"]),
            sa.ForeignKeyConstraint(["workout_log_id"], ["workout_logs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_activity_instance_links_activity_instance_id"), "activity_instance_links", ["activity_instance_id"], unique=False)
        op.create_index(op.f("ix_activity_instance_links_external_activity_record_id"), "activity_instance_links", ["external_activity_record_id"], unique=False)
        op.create_index(op.f("ix_activity_instance_links_workout_log_id"), "activity_instance_links", ["workout_log_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_instance_links_workout_log_id"), table_name="activity_instance_links")
    op.drop_index(op.f("ix_activity_instance_links_external_activity_record_id"), table_name="activity_instance_links")
    op.drop_index(op.f("ix_activity_instance_links_activity_instance_id"), table_name="activity_instance_links")
    op.drop_table("activity_instance_links")

