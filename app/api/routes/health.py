"""Health check endpoints for monitoring system status."""
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.dependencies import get_current_user
from app.config.settings import get_settings
from app.core.exceptions import AuthorizationError
from app.db.database import engine, get_replica_health_status, replica_pool
from app.models.user import User, UserRole

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


class DatabaseHealthStatus(BaseModel):
    """Health status for database connections."""

    status: str = Field(..., description="Overall status: healthy, degraded, or unhealthy")
    primary: dict = Field(..., description="Primary database status")
    replicas: dict | None = Field(None, description="Read replicas status")
    response_time_ms: float = Field(..., description="Database query response time in milliseconds")


class HealthCheckResponse(BaseModel):
    """Complete health check response."""

    status: str = Field(..., description="Overall system status")
    timestamp: str = Field(..., description="ISO 8601 timestamp of check")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    database: DatabaseHealthStatus = Field(..., description="Database health status")
    cache: dict | None = Field(None, description="Cache status if available")
    version: str = Field(..., description="API version")


async def check_primary_health() -> tuple[bool, float]:
    """Check primary database health."""
    try:
        start_time = time.time()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            await result.fetchone()
        response_time = (time.time() - start_time) * 1000
        return True, response_time
    except Exception as e:
        return False, 0


async def check_cache_health() -> dict:
    """Check Redis cache health."""
    try:
        from app.core.cache import get_redis

        redis_client = await get_redis()
        start_time = time.time()
        await redis_client.ping()
        response_time = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "connected": True,
        }
    except Exception:
        return {
            "status": "unhealthy",
            "connected": False,
        }


@router.get("", response_model=HealthCheckResponse)
async def health_check():
    """
    Public health check endpoint.

    Returns basic system health status without requiring authentication.
    This endpoint should be used by load balancers and monitoring systems.
    """
    start_time = time.time()

    primary_healthy, primary_response_time = await check_primary_health()
    replica_status = await get_replica_health_status()
    cache_status = await check_cache_health()

    overall_status = "healthy"
    if not primary_healthy:
        overall_status = "unhealthy"
    elif replica_status.get("healthy_count", 0) < replica_status.get("total_count", 1):
        overall_status = "degraded"

    db_status = "healthy" if primary_healthy else "unhealthy"
    database = DatabaseHealthStatus(
        status=db_status,
        primary={
            "status": db_status,
            "response_time_ms": round(primary_response_time, 2),
            "healthy": primary_healthy,
        },
        replicas=replica_status if replica_status.get("enabled") else None,
        response_time_ms=round(primary_response_time, 2),
    )

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=time.time() - start_time,
        database=database,
        cache=cache_status if cache_status.get("connected") else None,
        version=settings.api_version or "1.0.0",
    )


@router.get("/detailed", response_model=HealthCheckResponse)
async def detailed_health_check(current_user: User = Depends(get_current_user)):
    """
    Detailed health check endpoint (requires authentication).

    Returns comprehensive health status including all components.
    Requires user to be authenticated.
    """
    return await health_check()


@router.get("/database")
async def database_health():
    """Database-specific health check endpoint."""
    primary_healthy, primary_response_time = await check_primary_health()
    replica_status = await get_replica_health_status()

    overall_status = "healthy"
    if not primary_healthy:
        overall_status = "unhealthy"
    elif replica_status.get("healthy_count", 0) < replica_status.get("total_count", 1):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "primary": {
            "status": "healthy" if primary_healthy else "unhealthy",
            "response_time_ms": round(primary_response_time, 2),
        },
        "replicas": replica_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/admin")
async def admin_health_check(current_user: User = Depends(get_current_user)):
    """
    Admin-only health check with additional system metrics.

    Requires admin role to access.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise AuthorizationError("Admin access required", code="AUTH_ADMIN_REQUIRED", details={"user_id": current_user.id, "user_role": current_user.role})

    primary_healthy, primary_response_time = await check_primary_health()
    replica_status = await get_replica_health_status()

    return {
        "status": "healthy" if primary_healthy else "unhealthy",
        "database": {
            "primary": {
                "healthy": primary_healthy,
                "response_time_ms": round(primary_response_time, 2),
            },
            "replicas": replica_status,
        },
        "replica_pool_enabled": replica_pool is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/readiness")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.

    Returns 200 if the service is ready to accept traffic.
    Returns 503 if the service is not ready.
    """
    primary_healthy, _ = await check_primary_health()

    if not primary_healthy:
        raise HTTPException(status_code=503, detail="Database not ready")

    return {"status": "ready"}


@router.get("/liveness")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the service is alive.
    This is a simple check that should always succeed if the process is running.
    """
    return {"status": "alive"}
