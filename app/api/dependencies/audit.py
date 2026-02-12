"""Audit service dependencies for API routes."""
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.audit_service import AuditService


async def get_audit_service(
    db: AsyncSession = Depends(get_db),
) -> AuditService:
    """Dependency that provides an AuditService instance.

    This dependency creates a new AuditService instance for each request,
    providing a clean interface for logging audit events from API routes.

    Args:
        db: Database session from get_db dependency

    Returns:
        AuditService instance

    Example:
        ```python
        @router.post("/login")
        async def login(
            credentials: LoginRequest,
            audit_service: AuditService = Depends(get_audit_service),
            db: AsyncSession = Depends(get_db),
        ):
            # ... authentication logic ...
            await audit_service.log_login(user_id=user.id, request=request)
        ```
    """
    return AuditService(db)


def get_audit_service_factory(db: AsyncSession) -> callable:
    """Create a factory function for getting AuditService instances.

    This is useful for middleware that needs to create AuditService instances
    asynchronously.

    Args:
        db: Database session

    Returns:
        Async factory function that returns AuditService

    Example:
        ```python
        async def audit_service_factory() -> AuditService:
            async with get_db() as db:
                return AuditService(db)

        middleware = AuditLoggingMiddleware(
            app=app,
            audit_service_factory=audit_service_factory,
        )
        ```
    """
    async def factory() -> AuditService:
        return AuditService(db)
    return factory
