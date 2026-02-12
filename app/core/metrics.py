from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from prometheus_client.multiprocess import MultiProcessCollector
from functools import wraps
from typing import Callable, ParamSpec, TypeVar
from time import time
import os


P = ParamSpec('P')
T = TypeVar('T')


registry = CollectorRegistry()
if os.getenv('prometheus_multiproc_dir'):
    MultiProcessCollector(registry)


http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
    registry=registry
)

http_errors_total = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['method', 'endpoint', 'status'],
    registry=registry
)

db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['operation', 'table'],
    registry=registry
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation', 'table'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=registry
)

db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections',
    ['pool'],
    registry=registry
)

db_connections_idle = Gauge(
    'db_connections_idle',
    'Idle database connections',
    ['pool'],
    registry=registry
)

db_pool_size = Gauge(
    'db_pool_size',
    'Database connection pool size',
    ['pool'],
    registry=registry
)

db_pool_checkout_duration_seconds = Histogram(
    'db_pool_checkout_duration_seconds',
    'Database connection pool checkout duration in seconds',
    ['pool'],
    buckets=[0.0001, 0.0005, 0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry
)

db_pool_overflow_total = Counter(
    'db_pool_overflow_total',
    'Total database connection pool overflows',
    ['pool'],
    registry=registry
)

active_users = Gauge(
    'active_users',
    'Number of active users',
    registry=registry
)

sessions_generated_total = Counter(
    'sessions_generated_total',
    'Total sessions generated',
    ['status'],
    registry=registry
)

program_creation_total = Counter(
    'program_creation_total',
    'Total programs created',
    ['status'],
    registry=registry
)

cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type'],
    registry=registry
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type'],
    registry=registry
)

auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['result'],
    registry=registry
)

refresh_tokens_issued = Counter(
    'refresh_tokens_issued',
    'Total refresh tokens issued',
    registry=registry
)

refresh_tokens_revoked = Counter(
    'refresh_tokens_revoked',
    'Total refresh tokens revoked',
    ['reason'],
    registry=registry
)

app_info = Info(
    'app_info',
    'Application information',
    registry=registry
)


def track_http_request(method: str, endpoint: str, status: int, duration: float):
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    if status >= 400:
        http_errors_total.labels(method=method, endpoint=endpoint, status=status).inc()


def track_db_query(operation: str, table: str, duration: float):
    db_queries_total.labels(operation=operation, table=table).inc()
    db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)


def track_cache_hit(cache_type: str):
    cache_hits_total.labels(cache_type=cache_type).inc()


def track_cache_miss(cache_type: str):
    cache_misses_total.labels(cache_type=cache_type).inc()


def track_auth_attempt(result: str):
    auth_attempts_total.labels(result=result).inc()


def track_refresh_token_issued():
    refresh_tokens_issued.inc()


def track_refresh_token_revoked(reason: str):
    refresh_tokens_revoked.labels(reason=reason).inc()


def increment_active_users():
    active_users.inc()


def decrement_active_users():
    active_users.dec()


def track_session_generated(status: str):
    sessions_generated_total.labels(status=status).inc()


def track_program_created(status: str):
    program_creation_total.labels(status=status).inc()


def track_db_connections(pool: str, active: int, idle: int):
    db_connections_active.labels(pool=pool).set(active)
    db_connections_idle.labels(pool=pool).set(idle)


def track_db_pool_size(pool: str, size: int):
    db_pool_size.labels(pool=pool).set(size)


def track_db_pool_checkout(pool: str, duration: float):
    db_pool_checkout_duration_seconds.labels(pool=pool).observe(duration)


def track_db_pool_overflow(pool: str):
    db_pool_overflow_total.labels(pool=pool).inc()


def time_it(metric: Callable[[float], None] = lambda _: None):
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start = time()
            try:
                result = await func(*args, **kwargs)
                duration = time() - start
                metric(duration)
                return result
            except Exception as e:
                duration = time() - start
                metric(duration)
                raise
        
        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start = time()
            try:
                result = func(*args, **kwargs)
                duration = time() - start
                metric(duration)
                return result
            except Exception as e:
                duration = time() - start
                metric(duration)
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


def get_metrics() -> bytes:
    return generate_latest(registry)


def set_app_info(version: str, environment: str):
    app_info.info({
        'version': version,
        'environment': environment
    })
