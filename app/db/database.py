"""Database connection and session management."""
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_size=20,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency that provides a database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    if settings.debug and not settings.database_url.startswith("sqlite"):
        try:
            from alembic import command
            from alembic.config import Config

            repo_root = Path(__file__).resolve().parents[2]
            cfg = Config(str(repo_root / "alembic.ini"))
            cfg.set_main_option("script_location", str(repo_root / "alembic"))
            cfg.set_main_option("sqlalchemy.url", settings.database_url)
            command.upgrade(cfg, "head")
        except Exception:
            pass

    # Enable WAL mode for SQLite to support concurrent access
    if settings.database_url.startswith("sqlite"):
        async with engine.connect() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA busy_timeout=30000"))
            await conn.commit()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
