"""API routes module."""
from app.api.routes.programs import router as programs_router
from app.api.routes.days import router as days_router
from app.api.routes.logs import router as logs_router
from app.api.routes.settings import router as settings_router
from app.api.routes.circuits import router as circuits_router
from app.api.routes.activities import router as activities_router
from app.api.routes.scoring_config import router as scoring_config_router
from app.api.routes.scoring_metrics import router as scoring_metrics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.favorites import router as favorites_router
from app.api.routes.admin import router as admin_router

__all__ = [
    "programs_router",
    "days_router",
    "logs_router",
    "settings_router",
    "circuits_router",
    "activities_router",
    "scoring_config_router",
    "scoring_metrics_router",
    "auth_router",
    "favorites_router",
    "admin_router",
]
