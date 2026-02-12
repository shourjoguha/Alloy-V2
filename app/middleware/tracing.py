from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.core.tracing import (
    get_tracer,
    get_current_span_context,
    set_span_context,
    add_span_attribute,
    add_span_event,
    set_http_request_attributes,
    set_http_response_attributes,
    set_span_status,
    set_user,
    record_exception,
)
from app.core.logging import get_logger
from urllib.parse import urlparse


logger = get_logger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        tracer = get_tracer()
        
        path = request.url.path
        method = request.method
        endpoint_name = self._get_endpoint_name(request)
        
        with tracer.start_as_current_span(
            name=f"{method} {endpoint_name}",
            kind="server",
        ) as span:
            try:
                self._extract_trace_context(request)
                
                set_http_request_attributes(
                    method=method,
                    url=str(request.url),
                    headers=dict(request.headers),
                )
                
                add_span_attribute("http.route", endpoint_name)
                add_span_attribute("http.scheme", request.url.scheme)
                add_span_attribute("http.host", request.url.hostname)
                add_span_attribute("http.path", path)
                
                request_id = getattr(request.state, "request_id", None)
                if request_id:
                    add_span_attribute("http.request_id", request_id)
                
                user = getattr(request.state, "user", None)
                if user:
                    set_user(
                        user_id=str(user.id),
                        email=user.email,
                        role=user.role.value if hasattr(user, "role") else None,
                    )
                
                add_span_event("request_started", {"path": path, "method": method})
                
                response = await call_next(request)
                
                set_http_response_attributes(status_code=response.status_code)
                
                add_span_event(
                    "request_completed",
                    {"status_code": response.status_code, "path": path},
                )
                
                if response.status_code >= 400:
                    set_span_status(
                        "error",
                        f"HTTP {response.status_code}",
                    )
                else:
                    set_span_status("ok")
                
                return response
            except Exception as e:
                add_span_event(
                    "request_failed",
                    {"error": str(e), "type": type(e).__name__},
                )
                record_exception(e)
                set_span_status("error", str(e))
                raise
    
    def _get_endpoint_name(self, request: Request) -> str:
        route = request.scope.get("route")
        if route and hasattr(route, "path"):
            return route.path
        return request.url.path
    
    def _extract_trace_context(self, request: Request):
        trace_parent = request.headers.get("traceparent")
        trace_state = request.headers.get("tracestate")
        
        if trace_parent:
            try:
                import re
                match = re.match(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})", trace_parent)
                if match:
                    trace_id = match.group(1)
                    span_id = match.group(2)
                    set_span_context({
                        "trace_id": trace_id,
                        "span_id": span_id,
                        "traceparent": trace_parent,
                        "tracestate": trace_state,
                    })
            except Exception as e:
                logger.warning("Failed to extract trace context", exc_info=e)


class DatabaseTracingMiddleware:
    def __init__(self, engine):
        self.engine = engine
        self._setup_listeners()
    
    def _setup_listeners(self):
        from sqlalchemy import event
        
        @event.listens_for(self.engine.sync_engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            from app.core.tracing import get_tracer, set_db_attributes, add_span_attribute
            from app.core.tracing import get_current_span
            
            span = get_current_span()
            if span.is_recording():
                tracer = get_tracer()
                
                with tracer.start_as_current_span(
                    name="database_query",
                    kind="client",
                ) as db_span:
                    db_span.set_attribute("db.system", "postgresql")
                    db_span.set_attribute("db.name", conn.info.dbname if hasattr(conn.info, "dbname") else "alloy")
                    db_span.set_attribute("db.operation", self._extract_operation(statement))
                    db_span.set_attribute("db.statement", statement)
                    
                    context._db_span = db_span
        
        @event.listens_for(self.engine.sync_engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, "_db_span"):
                db_span = context._db_span
                db_span.set_attribute("db.rows_affected", cursor.rowcount if hasattr(cursor, "rowcount") else 0)
        
        @event.listens_for(self.engine.sync_engine, "handle_error")
        def receive_handle_error(exception_context):
            if hasattr(exception_context.execution_context, "_db_span"):
                db_span = exception_context.execution_context._db_span
                db_span.record_exception(exception_context.exception)
                db_span.set_status("error", str(exception_context.exception))
    
    def _extract_operation(self, statement: str) -> str:
        statement = statement.strip().upper()
        if statement.startswith(("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER")):
            return statement.split()[0]
        return "QUERY"


class CacheTracingMiddleware:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self._wrap_redis_client()
    
    def _wrap_redis_client(self):
        from app.core.tracing import get_tracer, set_cache_attributes, add_span_event, set_span_status
        import redis.asyncio as aioredis
        
        original_execute_command = aioredis.Redis.execute_command
        
        async def traced_execute_command(self, *args, **kwargs):
            tracer = get_tracer()
            command = args[0] if args else "UNKNOWN"
            key = args[1] if len(args) > 1 else None
            
            with tracer.start_as_current_span(
                name=f"cache_{command.lower()}",
                kind="client",
            ) as cache_span:
                cache_span.set_attribute("cache.system", "redis")
                cache_span.set_attribute("cache.operation", command.upper())
                if key:
                    cache_span.set_attribute("cache.key", str(key))
                
                add_span_event(
                    "cache_operation_started",
                    {"operation": command, "key": key},
                )
                
                try:
                    result = await original_execute_command(self, *args, **kwargs)
                    
                    add_span_event(
                        "cache_operation_completed",
                        {"operation": command, "key": key},
                    )
                    
                    set_span_status("ok")
                    return result
                except Exception as e:
                    add_span_event(
                        "cache_operation_failed",
                        {"operation": command, "key": key, "error": str(e)},
                    )
                    record_exception(e)
                    set_span_status("error", str(e))
                    raise
        
        aioredis.Redis.execute_command = traced_execute_command


class AsyncTracingContext:
    def __init__(self, tracer, name: str, **attributes):
        self.tracer = tracer
        self.name = name
        self.attributes = attributes
        self.span = None
    
    async def __aenter__(self):
        self.span = self.tracer.start_as_current_span(
            name=self.name,
            kind="internal",
        )
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.span.record_exception(exc_val)
            self.span.set_status("error", str(exc_val))
        else:
            self.span.set_status("ok")
        self.span.end()


def trace_async_function(tracer, name: str = None, **attributes):
    def decorator(func):
        import functools
        import asyncio
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(
                name=span_name,
                kind="internal",
            ) as span:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
                
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status("ok")
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status("error", str(e))
                    raise
        
        return wrapper
    return decorator
