"""
Middleware package for the application.
"""

from app.middleware.audit_logging import (
    AuditContextMiddleware,
    AuditLoggingMiddleware,
    SecurityEventMiddleware,
)
from app.middleware.metrics import DatabaseMetricsMiddleware, MetricsMiddleware
from app.middleware.performance import (
    QueryTrackingMiddleware,
    setup_query_tracking,
    track_db_query,
)
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.security import SecurityHeadersMiddleware

__all__ = [
    "AuditContextMiddleware",
    "AuditLoggingMiddleware",
    "SecurityEventMiddleware",
    "DatabaseMetricsMiddleware",
    "MetricsMiddleware",
    "QueryTrackingMiddleware",
    "setup_query_tracking",
    "track_db_query",
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
]
