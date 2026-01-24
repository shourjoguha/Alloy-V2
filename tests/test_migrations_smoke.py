import os
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest


def test_alembic_upgrade_downgrade_smoke(tmp_path: Path) -> None:
    """
    Smoke-test the migration graph on a disposable SQLite database.

    This does NOT mean production uses SQLite (prod is PostgreSQL). This test is a
    fast CI guardrail that catches common migration issues:
    - broken revision graph / dependency ordering
    - missing referenced tables/columns
    - SQLite-incompatible "ALTER TABLE add FK" operations (fixed via batch mode)

    For PostgreSQL-specific validation, set MIGRATIONS_SMOKE_DATABASE_URL to a
    disposable database URL (e.g. a CI provisioned Postgres instance).
    """
    repo_root = Path(__file__).resolve().parents[1]
    alembic_ini_path = repo_root / "alembic.ini"
    db_path = tmp_path / "alembic_smoke.db"

    cfg = Config(str(alembic_ini_path))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")


def test_alembic_upgrade_downgrade_smoke_postgres() -> None:
    """
    Optional smoke-test for PostgreSQL.

    Set MIGRATIONS_SMOKE_DATABASE_URL to a *disposable* database; this test will
    upgrade to head and downgrade to base.
    """
    database_url = os.getenv("MIGRATIONS_SMOKE_DATABASE_URL")
    if not database_url:
        pytest.skip("MIGRATIONS_SMOKE_DATABASE_URL not set")

    repo_root = Path(__file__).resolve().parents[1]
    alembic_ini_path = repo_root / "alembic.ini"

    cfg = Config(str(alembic_ini_path))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
