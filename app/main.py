"""Main FastAPI application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.db.database import init_db
from app.middleware.audit_logging import AuditLoggingMiddleware, AuditContextMiddleware, SecurityEventMiddleware
from app.services.audit_service import AuditService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def create_audit_service() -> AuditService:
    """Factory function to create AuditService for middleware."""
    from app.db.database import async_session_maker

    async with async_session_maker() as session:
        return AuditService(session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Get settings
    settings = get_settings()
    
    # Startup: Initialize database
    await init_db()

    # Set up query performance tracking
    if settings.enable_performance_monitoring:
        try:
            from app.db.database import setup_query_performance_tracking
            setup_query_performance_tracking()
        except Exception as e:
            import logging
            logging.warning(f"Failed to setup query performance tracking: {e}")

    # Initialize performance monitoring if enabled
    if settings.enable_performance_monitoring:
        try:
            await init_performance_monitor()
        except Exception as e:
            # Log but don't fail startup if performance monitoring fails
            import logging
            logging.warning(f"Failed to initialize performance monitoring: {e}")

    yield
    # Shutdown: Cleanup resources
    from app.llm import cleanup_llm_provider
    await cleanup_llm_provider()

    # Close database connections (primary and replicas)
    try:
        from app.db.database import close_all_engines
        await close_all_engines()
    except Exception as e:
        import logging
        logging.warning(f"Failed to close database engines: {e}")

    # Shutdown performance monitoring
    if settings.enable_performance_monitoring:
        try:
            await shutdown_performance_monitor()
        except Exception as e:
            import logging
            logging.warning(f"Failed to shutdown performance monitoring: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-enabled workout coach that creates adaptive strength/fitness programs",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Audit logging middleware - add before security middleware
    # Add context middleware first (lowest level)
    app.add_middleware(AuditContextMiddleware)

    # Security event middleware for detecting suspicious activity
    app.add_middleware(
        SecurityEventMiddleware,
        audit_service_factory=create_audit_service,
        enabled=True,
    )

    # Audit logging middleware for automatic auth event logging
    app.add_middleware(
        AuditLoggingMiddleware,
        audit_service_factory=create_audit_service,
        enabled=True,
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "app": settings.app_name}
    
    # LLM health check
    @app.get("/health/llm")
    async def llm_health_check():
        """Check LLM provider availability."""
        from app.llm import get_llm_provider

        provider = get_llm_provider()
        is_healthy = await provider.health_check()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "provider": settings.llm_provider,
            "model": settings.openai_model,
        }

    # Database replica health check
    @app.get("/health/database/replicas")
    async def replica_health_check():
        """Check read replica health and status."""
        from app.db.database import get_replica_health_status

        status = await get_replica_health_status()

        # Determine overall health
        if not status["enabled"]:
            overall_status = "disabled"
        elif status["healthy_count"] > 0:
            overall_status = "healthy"
        else:
            overall_status = "unhealthy"

        return {
            "overall_status": overall_status,
            **status,
        }
    
    # Import and include routers
    from app.api.routes import (
        programs_router,
        days_router,
        logs_router,
        settings_router,
        circuits_router,
        activities_router,
        scoring_config_router,
        scoring_metrics_router,
        auth_router,
        favorites_router,
        admin_router,
    )
    from app.api.routes.audit import router as audit_router
    from app.api.routes.performance import router as performance_router
    from app.api.routes.errors import router as errors_router
    from app.core.performance import init_performance_monitor, shutdown_performance_monitor

    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    app.include_router(programs_router, prefix="/programs", tags=["Programs"])
    app.include_router(days_router, prefix="/days", tags=["Daily Planning"])
    app.include_router(logs_router, prefix="/logs", tags=["Logging"])
    app.include_router(settings_router, prefix="/settings", tags=["Settings"])
    app.include_router(circuits_router, prefix="/circuits", tags=["Circuits"])
    app.include_router(activities_router, prefix="/activities", tags=["Activities"])
    app.include_router(favorites_router, prefix="/favorites", tags=["Favorites"])
    app.include_router(scoring_config_router, prefix="/scoring", tags=["Scoring Config"])
    app.include_router(scoring_metrics_router, tags=["Scoring Metrics"])
    app.include_router(admin_router, prefix="/admin", tags=["Admin"])
    app.include_router(audit_router, prefix="/api", tags=["Audit"])
    app.include_router(performance_router, tags=["Performance"])
    app.include_router(errors_router, prefix="/api", tags=["Error Dashboard"])
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
