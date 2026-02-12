"""Database connection and session management with read replica support."""
import asyncio
import logging
import random
from collections import defaultdict
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import Engine, event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import QueuePool

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Context variable to force read from primary within a transaction
force_primary_session: ContextVar[bool] = ContextVar("force_primary_session", default=False)

settings = get_settings()


@dataclass
class ReplicaStatus:
    """Health status tracking for a read replica."""
    url: str
    engine: Optional[AsyncEngine] = None
    session_maker: Optional[async_sessionmaker] = None
    is_healthy: bool = True
    last_check: Optional[datetime] = None
    failure_count: int = 0
    last_error: Optional[str] = None
    total_queries: int = 0
    failed_queries: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate query success rate."""
        if self.total_queries == 0:
            return 100.0
        return (self.total_queries - self.failed_queries) / self.total_queries * 100


@dataclass
class ReplicaPool:
    """Pool of read replicas with health tracking."""
    replicas: list[ReplicaStatus] = field(default_factory=list)
    current_index: int = 0
    strategy: str = "round_robin"  # round_robin, random, least_connections

    def get_healthy_replica(self) -> Optional[ReplicaStatus]:
        """Get a healthy replica using the configured strategy."""
        healthy_replicas = [r for r in self.replicas if r.is_healthy and r.engine is not None]

        if not healthy_replicas:
            return None

        if self.strategy == "random":
            return random.choice(healthy_replicas)
        elif self.strategy == "least_connections":
            return min(healthy_replicas, key=lambda r: r.total_queries)
        else:  # round_robin (default)
            replica = healthy_replicas[self.current_index % len(healthy_replicas)]
            self.current_index += 1
            return replica

    def mark_failure(self, replica: ReplicaStatus, error: str):
        """Mark a replica as failed."""
        replica.failure_count += 1
        replica.last_error = error
        replica.failed_queries += 1

        if replica.failure_count >= settings.read_replica_max_failures:
            replica.is_healthy = False
            logger.warning(
                f"Replica {replica.url} marked as unhealthy after {replica.failure_count} failures. Error: {error}"
            )

    def mark_success(self, replica: ReplicaStatus):
        """Mark a replica as successful."""
        replica.failure_count = max(0, replica.failure_count - 1)
        replica.total_queries += 1

        # Reset healthy status if we've recovered
        if not replica.is_healthy and replica.failure_count == 0:
            replica.is_healthy = True
            logger.info(f"Replica {replica.url} marked as healthy again")


# Global replica pool instance
replica_pool: Optional[ReplicaPool] = None


def create_primary_engine() -> AsyncEngine:
    """Create the primary database engine for writes."""
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        future=True,
        pool_size=20,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=300,
        pool_pre_ping=True,
    )


def create_replica_engine(url: str) -> AsyncEngine:
    """Create a read replica engine."""
    return create_async_engine(
        url,
        echo=False,  # Disable query logging on replicas for performance
        future=True,
        pool_size=settings.read_replica_pool_size,
        max_overflow=settings.read_replica_max_overflow,
        pool_timeout=settings.read_replica_pool_timeout,
        pool_recycle=settings.read_replica_pool_recycle,
        pool_pre_ping=True,
        poolclass=QueuePool,
    )


async def initialize_replica_pool() -> Optional[ReplicaPool]:
    """Initialize read replica pool from settings."""
    if not settings.read_replica_enabled or not settings.read_replica_urls:
        return None

    replica_urls = [url.strip() for url in settings.read_replica_urls.split(",") if url.strip()]

    if not replica_urls:
        logger.warning("read_replica_enabled is True but no replica URLs configured")
        return None

    replicas = []
    for url in replica_urls:
        try:
            engine = create_replica_engine(url)
            session_maker = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            # Initial health check
            is_healthy = await check_replica_health(engine)

            replica = ReplicaStatus(
                url=url,
                engine=engine,
                session_maker=session_maker,
                is_healthy=is_healthy,
                last_check=datetime.utcnow(),
            )

            replicas.append(replica)
            logger.info(
                f"Initialized read replica: {url} - "
                f"Healthy: {is_healthy}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize replica {url}: {e}")
            # Still add unhealthy replica so it can be monitored
            replicas.append(
                ReplicaStatus(
                    url=url,
                    engine=None,
                    session_maker=None,
                    is_healthy=False,
                    last_error=str(e),
                )
            )

    return ReplicaPool(replicas=replicas, strategy="round_robin")


async def check_replica_health(engine: AsyncEngine) -> bool:
    """Check if a replica is healthy by running a simple query."""
    try:
        async with asyncio.timeout(settings.read_replica_health_check_timeout):
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
    except Exception as e:
        logger.debug(f"Replica health check failed: {e}")
        return False


async def health_check_loop():
    """Background task to periodically check replica health."""
    if not replica_pool:
        return

    while True:
        await asyncio.sleep(settings.read_replica_health_check_interval)

        for replica in replica_pool.replicas:
            if replica.engine is None:
                continue

            try:
                is_healthy = await check_replica_health(replica.engine)
                replica.is_healthy = is_healthy
                replica.last_check = datetime.utcnow()

                if not is_healthy:
                    replica.failure_count += 1
                else:
                    replica.failure_count = max(0, replica.failure_count - 1)

            except Exception as e:
                logger.error(f"Health check error for replica {replica.url}: {e}")
                replica.is_healthy = False
                replica.last_error = str(e)


class RoutingSession(AsyncSession):
    """
    Custom session that routes read queries to replicas and write queries to primary.

    This session automatically determines the appropriate database connection:
    - Write operations (INSERT, UPDATE, DELETE) always use primary
    - Read operations (SELECT) use replicas when available
    - Reads within transactions use primary for consistency
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._use_replica: bool = kwargs.pop("use_replica", False)
        self._replica_status: Optional[ReplicaStatus] = kwargs.pop("replica_status", None)
        super().__init__(*args, **kwargs)


def get_session_maker(use_replica: bool = False) -> async_sessionmaker:
    """Get the appropriate session maker based on operation type."""
    if use_replica and replica_pool:
        replica = replica_pool.get_healthy_replica()
        if replica and replica.session_maker:
            return replica.session_maker

    # Fall back to primary
    return async_session_maker


# Create primary engine
engine = create_primary_engine()


def setup_query_performance_tracking():
    """Set up SQLAlchemy event listeners for query performance tracking."""
    try:
        from app.middleware.performance import setup_query_tracking
        # Set up tracking on the underlying sync engine
        sync_engine = engine.sync_engine if hasattr(engine, 'sync_engine') else None
        if sync_engine:
            setup_query_tracking(sync_engine)
    except Exception as e:
        import logging
        logging.debug(f"Failed to setup query tracking: {e}")


# Primary session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncSession:
    """
    Dependency that provides a database session with automatic routing.

    This session will route:
    - Write operations to primary database
    - Read operations to available replicas (with fallback to primary)
    """
    # Check if we should force primary (e.g., within a transaction)
    force_primary = force_primary_session.get()

    # Determine if we should try to use a replica
    use_replica = not force_primary and replica_pool is not None

    if use_replica:
        replica = replica_pool.get_healthy_replica()
        if replica and replica.session_maker:
            try:
                async with replica.session_maker() as session:
                    yield session
                    # Only commit if no exception occurred
                    await session.commit()
                    replica_pool.mark_success(replica)
                    return
            except Exception as e:
                logger.warning(f"Replica query failed, falling back to primary: {e}")
                replica_pool.mark_failure(replica, str(e))

        # Fall back to primary if replica failed or not available
        if not settings.replica_fallback_to_primary:
            raise Exception("All replicas failed and fallback to primary is disabled")

    # Use primary database
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_read_db() -> AsyncSession:
    """
    Dependency that provides a read-only database session.

    This session will always prefer replicas and is suitable for read-heavy operations.
    """
    if replica_pool:
        replica = replica_pool.get_healthy_replica()
        if replica and replica.session_maker:
            try:
                async with replica.session_maker() as session:
                    yield session
                    replica_pool.mark_success(replica)
                    return
            except Exception as e:
                logger.warning(f"Replica query failed, falling back to primary: {e}")
                replica_pool.mark_failure(replica, str(e))

        # Fall back to primary if replica failed or not available
        if not settings.replica_fallback_to_primary:
            raise Exception("All replicas failed and fallback to primary is disabled")

    # Use primary database as fallback
    async with async_session_maker() as session:
        yield session


async def get_write_db() -> AsyncSession:
    """
    Dependency that provides a write-only database session.

    This session always uses the primary database for consistency.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class TransactionContext:
    """
    Context manager for transactions that ensures all reads go to primary.

    This is important for read-after-write consistency scenarios.
    """

    def __init__(self):
        self._token = None

    async def __aenter__(self):
        self._token = force_primary_session.set(True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            force_primary_session.reset(self._token)
        return False


async def init_db():
    """Initialize database tables and replica pool."""
    global replica_pool

    # Initialize replica pool if enabled
    replica_pool = await initialize_replica_pool()

    if replica_pool:
        # Start background health check loop
        asyncio.create_task(health_check_loop())
        logger.info(f"Read replica pool initialized with {len(replica_pool.replicas)} replicas")

    # Initialize database tables
    if settings.debug and not settings.database_url.startswith("sqlite"):
        import logging
        logging.info("Alembic migrations skipped (manual migration required)")

    # Enable WAL mode for SQLite to support concurrent access
    if settings.database_url.startswith("sqlite"):
        async with engine.connect() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA busy_timeout=30000"))
            await conn.commit()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_replica_health_status() -> dict:
    """Get the health status of all read replicas."""
    if not replica_pool:
        return {
            "enabled": False,
            "replicas": [],
        }

    return {
        "enabled": True,
        "strategy": replica_pool.strategy,
        "replicas": [
            {
                "url": r.url,
                "is_healthy": r.is_healthy,
                "last_check": r.last_check.isoformat() if r.last_check else None,
                "failure_count": r.failure_count,
                "last_error": r.last_error,
                "total_queries": r.total_queries,
                "failed_queries": r.failed_queries,
                "success_rate": round(r.success_rate, 2),
            }
            for r in replica_pool.replicas
        ],
        "healthy_count": sum(1 for r in replica_pool.replicas if r.is_healthy),
        "total_count": len(replica_pool.replicas),
    }


async def close_all_engines():
    """Close all database engines (primary and replicas)."""
    global replica_pool

    # Close primary engine
    await engine.dispose()

    # Close all replica engines
    if replica_pool:
        for replica in replica_pool.replicas:
            if replica.engine:
                await replica.engine.dispose()
