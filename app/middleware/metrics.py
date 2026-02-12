from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from time import time
from app.core.metrics import track_http_request, track_db_connections
from app.core.logging import get_logger


logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time()

        method = request.method
        path = self._get_endpoint_path(request)
        request_id = getattr(request.state, "request_id", None)

        try:
            response = await call_next(request)
            duration = time() - start_time
            status = response.status_code

            track_http_request(method=method, endpoint=path, status=status, duration=duration)

            # Also record to performance monitor if enabled
            try:
                from app.core.performance import get_performance_monitor
                from app.config.settings import get_settings

                settings = get_settings()
                if settings.enable_performance_monitoring:
                    monitor = get_performance_monitor()
                    monitor.record_latency(
                        method=method,
                        endpoint=path,
                        duration=duration,
                        status_code=status,
                        request_id=request_id,
                    )
            except Exception:
                # Don't fail if performance monitoring has issues
                pass

            logger.debug(
                "Request completed",
                extra={
                    "method": method,
                    "path": path,
                    "status": status,
                    "duration": duration,
                    "request_id": request_id,
                }
            )

            return response
        except Exception as e:
            duration = time() - start_time
            track_http_request(method=method, endpoint=path, status=500, duration=duration)

            # Record to performance monitor
            try:
                from app.core.performance import get_performance_monitor
                from app.config.settings import get_settings

                settings = get_settings()
                if settings.enable_performance_monitoring:
                    monitor = get_performance_monitor()
                    monitor.record_latency(
                        method=method,
                        endpoint=path,
                        duration=duration,
                        status_code=500,
                        request_id=request_id,
                    )
            except Exception:
                pass

            logger.error(
                "Request failed",
                exc_info=e,
                extra={
                    "method": method,
                    "path": path,
                    "duration": duration,
                    "request_id": request_id,
                }
            )

            raise
    
    def _get_endpoint_path(self, request: Request) -> str:
        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            path = route.path
            if "<" not in path:
                return path
        
        path = request.url.path
        
        if path.startswith("/api"):
            parts = path.split("/")
            if len(parts) > 3:
                return f"{parts[0]}/{parts[1]}/{parts[2]}/{{id}}"
        
        return path


class DatabaseMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            from app.database import get_engine
            
            engine = get_engine()
            pool = engine.pool
            
            if pool:
                active_connections = getattr(pool, "checkedout", 0) or 0
                idle_connections = getattr(pool, "size", 0) - active_connections
                
                track_db_connections("default", active_connections, idle_connections)
            
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error("Failed to track database metrics", exc_info=e)
            return await call_next(request)
