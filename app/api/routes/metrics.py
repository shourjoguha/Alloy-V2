from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from starlette.requests import Request
from app.core.metrics import get_metrics
from app.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics(request: Request):
    try:
        metrics_data = get_metrics()
        return Response(
            content=metrics_data,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
    except Exception as e:
        logger.error("Failed to generate metrics", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to generate metrics")


@router.get("/health", include_in_schema=False)
async def health_check(request: Request):
    return {"status": "healthy"}


@router.get("/health/db", include_in_schema=False)
async def database_health_check(request: Request):
    try:
        from app.database import get_engine
        
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("Database health check failed", exc_info=e)
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@router.get("/health/redis", include_in_schema=False)
async def redis_health_check(request: Request):
    try:
        from app.core.cache import redis_client
        
        if redis_client:
            await redis_client.ping()
            return {"status": "healthy", "redis": "connected"}
        else:
            return {"status": "degraded", "redis": "not_configured"}
    except Exception as e:
        logger.error("Redis health check failed", exc_info=e)
        return {"status": "unhealthy", "redis": "disconnected", "error": str(e)}
