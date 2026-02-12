from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXInstrumentor
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.propagate import inject, extract
from contextvars import ContextVar
from typing import Optional, Dict, Any
import os


_current_span_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar("current_span_context", default=None)


def setup_tracing(service_name: str = "alloy-api", environment: str = "production"):
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.getenv("APP_VERSION", "1.0.0"),
            "deployment.environment": environment,
            "telemetry.sdk.language": "python",
        }
    )
    
    provider = TracerProvider(resource=resource)
    
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    
    trace.set_tracer_provider(provider)
    
    return trace.get_tracer(__name__)


def instrument_fastapi(app):
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace.get_tracer_provider(),
        excluded_urls=["/metrics", "/health", "/health/*"],
    )


def instrument_sqlalchemy(engine):
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        tracer_provider=trace.get_tracer_provider(),
    )


def instrument_redis(redis_client):
    RedisInstrumentor().instrument(
        tracer_provider=trace.get_tracer_provider(),
    )


def instrument_httpx():
    HTTPXInstrumentor().instrument(
        tracer_provider=trace.get_tracer_provider(),
    )


def get_tracer():
    return trace.get_tracer(__name__)


def get_current_span():
    return trace.get_current_span()


def get_current_span_context() -> Dict[str, Any]:
    context = _current_span_context.get()
    if context is None:
        span_context = trace.get_current_span().get_span_context()
        context = {
            "trace_id": format(span_context.trace_id, "032x"),
            "span_id": format(span_context.span_id, "016x"),
        }
        _current_span_context.set(context)
    return context


def set_span_context(context: Dict[str, Any]):
    _current_span_context.set(context)


def add_span_attribute(key: str, value: Any):
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(key, value)


def add_span_event(name: str, attributes: Dict[str, Any] = None):
    span = trace.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes or {})


def record_exception(exception: Exception, attributes: Dict[str, Any] = None):
    span = trace.get_current_span()
    if span.is_recording():
        span.record_exception(exception, attributes or {})


def set_span_status(status: str, description: str = ""):
    span = trace.get_current_span()
    if span.is_recording():
        from opentelemetry.trace import Status, StatusCode
        if status == "ok":
            span.set_status(Status(StatusCode.OK))
        elif status == "error":
            span.set_status(Status(StatusCode.ERROR, description))


def inject_trace_headers(headers: Dict[str, str]):
    inject(headers)
    return headers


def extract_trace_headers(headers: Dict[str, str]):
    return extract(headers)


def set_user(user_id: str, email: str = None, role: str = None):
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("user.id", user_id)
        if email:
            span.set_attribute("user.email", email)
        if role:
            span.set_attribute("user.role", role)


def set_http_request_attributes(method: str, url: str, headers: Dict[str, str] = None):
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(SpanAttributes.HTTP_METHOD, method)
        span.set_attribute(SpanAttributes.HTTP_URL, url)
        if headers:
            span.set_attribute("http.request.headers", str(headers))


def set_http_response_attributes(status_code: int):
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(SpanAttributes.HTTP_STATUS_CODE, status_code)


def set_db_attributes(db_system: str, db_name: str, db_operation: str, db_statement: str = None):
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(SpanAttributes.DB_SYSTEM, db_system)
        span.set_attribute(SpanAttributes.DB_NAME, db_name)
        span.set_attribute(SpanAttributes.DB_OPERATION, db_operation)
        if db_statement:
            span.set_attribute(SpanAttributes.DB_STATEMENT, db_statement)


def set_cache_attributes(cache_system: str, cache_operation: str, cache_key: str = None):
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("cache.system", cache_system)
        span.set_attribute("cache.operation", cache_operation)
        if cache_key:
            span.set_attribute("cache.key", cache_key)
