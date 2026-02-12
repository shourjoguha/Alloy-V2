"""
Performance monitoring middleware for database queries and other operations.

Provides integration between database operations and the performance monitoring system.
"""

import hashlib
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional

from sqlalchemy import event
from sqlalchemy.engine import Engine, Connection

from app.core.logging import get_logger
from app.core.performance import get_performance_monitor
from app.config.settings import get_settings

logger = get_logger(__name__)


@contextmanager
def track_db_query(
    operation: str,
    table: str,
    query: str,
    request_id: Optional[str] = None,
) -> Generator[None, None, None]:
    """
    Context manager to track database query performance.

    Args:
        operation: Query operation type (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        query: SQL query string
        request_id: Optional request ID for correlation

    Usage:
        with track_db_query("SELECT", "programs", "SELECT * FROM programs"):
            # ... execute query ...
    """
    settings = get_settings()
    if not settings.enable_performance_monitoring:
        yield
        return

    try:
        monitor = get_performance_monitor()
    except Exception:
        yield
        return

    query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
    start_time = time.time()

    try:
        yield
    finally:
        duration = time.time() - start_time
        monitor.record_query(
            operation=operation,
            table=table,
            duration=duration,
            query_hash=query_hash,
            request_id=request_id,
        )


def setup_query_tracking(engine: Engine) -> None:
    """
    Set up SQLAlchemy event listeners for query tracking.

    Args:
        engine: SQLAlchemy engine instance
    """
    settings = get_settings()
    if not settings.enable_performance_monitoring:
        return

    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(
        conn: Connection,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Store query start time for timing."""
        context._query_start_time = time.time()

    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(
        conn: Connection,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Record query performance after execution."""
        if not hasattr(context, "_query_start_time"):
            return

        duration = time.time() - context._query_start_time

        try:
            monitor = get_performance_monitor()

            # Parse operation type from statement
            operation = "UNKNOWN"
            statement_upper = statement.strip().upper()
            if statement_upper.startswith("SELECT"):
                operation = "SELECT"
            elif statement_upper.startswith("INSERT"):
                operation = "INSERT"
            elif statement_upper.startswith("UPDATE"):
                operation = "UPDATE"
            elif statement_upper.startswith("DELETE"):
                operation = "DELETE"
            elif statement_upper.startswith("CREATE"):
                operation = "CREATE"
            elif statement_upper.startswith("ALTER"):
                operation = "ALTER"
            elif statement_upper.startswith("DROP"):
                operation = "DROP"

            # Extract table name (simplified extraction)
            table = extract_table_name(statement)

            # Generate query hash
            query_hash = hashlib.md5(statement.encode()).hexdigest()[:16]

            # Get affected rows if available
            affected_rows = 0
            if hasattr(cursor, "rowcount") and cursor.rowcount is not None:
                affected_rows = cursor.rowcount

            # Get request ID from context if available
            request_id = None
            try:
                # Try to get request ID from connection info
                if hasattr(conn, "info") and hasattr(conn.info, "context"):
                    request_id = conn.info.context.get("request_id")
            except Exception:
                pass

            monitor.record_query(
                operation=operation,
                table=table,
                duration=duration,
                query_hash=query_hash,
                affected_rows=affected_rows,
                request_id=request_id,
            )
        except Exception as e:
            # Don't fail query execution if performance tracking fails
            logger.debug("Failed to track query performance", error=str(e))


def extract_table_name(statement: str) -> str:
    """
    Extract table name from SQL statement.

    Args:
        statement: SQL query string

    Returns:
        Table name or 'UNKNOWN' if not found
    """
    statement = statement.strip().upper()

    # Simple pattern matching for common operations
    patterns = [
        ("FROM", ["WHERE", "GROUP", "ORDER", "LIMIT", "JOIN", ";"]),
        ("UPDATE", ["SET", "WHERE", ";"]),
        ("INSERT INTO", ["(", ";"]),
        ("DELETE FROM", ["WHERE", ";"]),
    ]

    for keyword, delimiters in patterns:
        if keyword in statement:
            # Find keyword and get everything after it
            start_idx = statement.find(keyword) + len(keyword)
            rest = statement[start_idx:].strip()

            # Find first delimiter
            for delim in delimiters:
                if delim in rest:
                    table_part = rest[: rest.find(delim)].strip()
                    # Remove any schema prefix
                    if "." in table_part:
                        table_part = table_part.split(".")[-1]
                    return table_part

    return "UNKNOWN"


class QueryTrackingMiddleware:
    """
    Middleware for tracking database queries in the request context.

    This helps correlate queries with requests for better analysis.
    """

    def __init__(self, app, get_request_id_func: Optional[Callable] = None):
        """
        Initialize query tracking middleware.

        Args:
            app: ASGI application
            get_request_id_func: Optional function to extract request ID from scope
        """
        self.app = app
        self.get_request_id_func = get_request_id_func

    async def __call__(self, scope, receive, send):
        """ASGI middleware call."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request ID
        request_id = None
        if self.get_request_id_func:
            try:
                request_id = self.get_request_id_func(scope)
            except Exception:
                pass

        # Store request ID in state for database connections to access
        # This is a simplified approach - in production, you might use
        # a more sophisticated context system
        async def wrapped_receive():
            message = await receive()
            return message

        # Store in a thread-local or context variable
        # For now, we'll use a simple approach with the database connection

        await self.app(scope, wrapped_receive, send)
