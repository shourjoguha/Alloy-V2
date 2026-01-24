"""Add external integration tables

Revision ID: bc7890ab12cd
Revises: ae12bc34de56
Create Date: 2026-01-18

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bc7890ab12cd"
down_revision: Union[str, Sequence[str], None] = "ae12bc34de56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    dialect_name = conn.dialect.name

    # Define enums
    external_provider_enum = sa.Enum(
        "STRAVA",
        "GARMIN",
        "APPLE_HEALTH",
        "WHOOP",
        "OURA",
        "OTHER",
        name="externalprovider",
    )
    ingestion_status_enum = sa.Enum("RUNNING", "SUCCEEDED", "FAILED", name="ingestionrunstatus")

    if not inspector.has_table("external_provider_accounts"):
        op.create_table(
            "external_provider_accounts",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("provider", external_provider_enum, nullable=False),
            sa.Column("external_user_id", sa.String(length=255), nullable=True),
            sa.Column("scopes", sa.JSON(), nullable=True),
            sa.Column("access_token_encrypted", sa.Text(), nullable=True),
            sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
            sa.Column("token_expires_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_external_provider_accounts_provider"), "external_provider_accounts", ["provider"], unique=False)
        op.create_index(op.f("ix_external_provider_accounts_status"), "external_provider_accounts", ["status"], unique=False)
        op.create_index(op.f("ix_external_provider_accounts_user_id"), "external_provider_accounts", ["user_id"], unique=False)

    if not inspector.has_table("external_ingestion_runs"):
        op.create_table(
            "external_ingestion_runs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("provider", external_provider_enum, nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("status", ingestion_status_enum, nullable=False),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("cursor_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_external_ingestion_runs_provider"), "external_ingestion_runs", ["provider"], unique=False)
        op.create_index(op.f("ix_external_ingestion_runs_status"), "external_ingestion_runs", ["status"], unique=False)
        op.create_index(op.f("ix_external_ingestion_runs_user_id"), "external_ingestion_runs", ["user_id"], unique=False)

    if not inspector.has_table("external_activity_records"):
        op.create_table(
            "external_activity_records",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("provider", external_provider_enum, nullable=False),
            sa.Column("external_id", sa.String(length=255), nullable=False),
            sa.Column("activity_type_raw", sa.String(length=255), nullable=True),
            sa.Column("start_time", sa.DateTime(), nullable=True),
            sa.Column("end_time", sa.DateTime(), nullable=True),
            sa.Column("timezone", sa.String(length=64), nullable=True),
            sa.Column("raw_payload_json", sa.JSON(), nullable=True),
            sa.Column("ingestion_run_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["ingestion_run_id"], ["external_ingestion_runs.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "provider", "external_id", name="uq_external_activity_record"),
        )
        op.create_index(op.f("ix_external_activity_records_external_id"), "external_activity_records", ["external_id"], unique=False)
        op.create_index(op.f("ix_external_activity_records_ingestion_run_id"), "external_activity_records", ["ingestion_run_id"], unique=False)
        op.create_index(op.f("ix_external_activity_records_provider"), "external_activity_records", ["provider"], unique=False)
        op.create_index(op.f("ix_external_activity_records_start_time"), "external_activity_records", ["start_time"], unique=False)
        op.create_index(op.f("ix_external_activity_records_user_id"), "external_activity_records", ["user_id"], unique=False)

    if not inspector.has_table("external_metric_streams"):
        op.create_table(
            "external_metric_streams",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("external_activity_record_id", sa.Integer(), nullable=False),
            sa.Column("stream_type", sa.String(length=100), nullable=False),
            sa.Column("raw_stream_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["external_activity_record_id"], ["external_activity_records.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_external_metric_streams_external_activity_record_id"), "external_metric_streams", ["external_activity_record_id"], unique=False)
        op.create_index(op.f("ix_external_metric_streams_stream_type"), "external_metric_streams", ["stream_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_external_metric_streams_stream_type"), table_name="external_metric_streams")
    op.drop_index(op.f("ix_external_metric_streams_external_activity_record_id"), table_name="external_metric_streams")
    op.drop_table("external_metric_streams")

    op.drop_index(op.f("ix_external_activity_records_user_id"), table_name="external_activity_records")
    op.drop_index(op.f("ix_external_activity_records_start_time"), table_name="external_activity_records")
    op.drop_index(op.f("ix_external_activity_records_provider"), table_name="external_activity_records")
    op.drop_index(op.f("ix_external_activity_records_ingestion_run_id"), table_name="external_activity_records")
    op.drop_index(op.f("ix_external_activity_records_external_id"), table_name="external_activity_records")
    op.drop_table("external_activity_records")

    op.drop_index(op.f("ix_external_ingestion_runs_user_id"), table_name="external_ingestion_runs")
    op.drop_index(op.f("ix_external_ingestion_runs_status"), table_name="external_ingestion_runs")
    op.drop_index(op.f("ix_external_ingestion_runs_provider"), table_name="external_ingestion_runs")
    op.drop_table("external_ingestion_runs")

    op.drop_index(op.f("ix_external_provider_accounts_user_id"), table_name="external_provider_accounts")
    op.drop_index(op.f("ix_external_provider_accounts_status"), table_name="external_provider_accounts")
    op.drop_index(op.f("ix_external_provider_accounts_provider"), table_name="external_provider_accounts")
    op.drop_table("external_provider_accounts")
