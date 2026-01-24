"""Add recovery raw payload and movement relationships

Revision ID: 9c1a2b3c4d5e
Revises: 87ec9db39e1e
Create Date: 2026-01-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c1a2b3c4d5e"
down_revision: Union[str, Sequence[str], None] = "87ec9db39e1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("recovery_signals")]
    if "raw_payload_json" not in columns:
        op.add_column("recovery_signals", sa.Column("raw_payload_json", sa.JSON(), nullable=True))

    if not inspector.has_table("movement_relationships"):
        op.create_table(
            "movement_relationships",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("source_movement_id", sa.Integer(), nullable=False),
            sa.Column("target_movement_id", sa.Integer(), nullable=False),
            sa.Column("relationship_type", sa.String(length=50), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["source_movement_id"], ["movements.id"]),
            sa.ForeignKeyConstraint(["target_movement_id"], ["movements.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_movement_relationships_relationship_type"),
            "movement_relationships",
            ["relationship_type"],
            unique=False,
        )
        op.create_index(
            op.f("ix_movement_relationships_source_movement_id"),
            "movement_relationships",
            ["source_movement_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_movement_relationships_target_movement_id"),
            "movement_relationships",
            ["target_movement_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_movement_relationships_target_movement_id"), table_name="movement_relationships")
    op.drop_index(op.f("ix_movement_relationships_source_movement_id"), table_name="movement_relationships")
    op.drop_index(op.f("ix_movement_relationships_relationship_type"), table_name="movement_relationships")
    op.drop_table("movement_relationships")

    op.drop_column("recovery_signals", "raw_payload_json")

