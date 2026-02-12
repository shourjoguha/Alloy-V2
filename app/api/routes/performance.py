"""
Performance monitoring API endpoints.

Provides endpoints for:
- Performance metrics overview
- Slow queries analysis
- Performance reports
- Active alerts
- Baseline management
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.core.performance import (
    PerformanceMonitor,
    get_performance_monitor,
    track_request_latency,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/performance", tags=["Performance"])


# ========================================
# Pydantic Models
# ========================================


class LatencyMetrics(BaseModel):
    """Latency metrics for an endpoint."""

    endpoint: str
    count: int
    p50: float = Field(..., description="50th percentile (median) latency in seconds")
    p95: float = Field(..., description="95th percentile latency in seconds")
    p99: float = Field(..., description="99th percentile latency in seconds")
    min: float = Field(..., description="Minimum latency in seconds")
    max: float = Field(..., description="Maximum latency in seconds")
    avg: float = Field(..., description="Average latency in seconds")


class QueryMetrics(BaseModel):
    """Query metrics for an operation/table."""

    query: str
    count: int
    avg: float = Field(..., description="Average query duration in seconds")
    min: float = Field(..., description="Minimum query duration in seconds")
    max: float = Field(..., description="Maximum query duration in seconds")
    total: float = Field(..., description="Total time spent on queries in seconds")


class SlowQuery(BaseModel):
    """Slow query details."""

    operation: str
    table: str
    duration: float = Field(..., description="Query duration in seconds")
    timestamp: float = Field(..., description="Unix timestamp")
    query_hash: str
    request_id: Optional[str] = None


class MemoryMetrics(BaseModel):
    """Memory usage metrics."""

    rss_mb: float = Field(..., description="Resident Set Size in MB")
    vms_mb: float = Field(..., description="Virtual Memory Size in MB")
    heap_mb: float = Field(..., description="Heap memory in MB")
    thread_count: int = Field(..., description="Number of threads")
    open_files: int = Field(..., description="Number of open files")
    timestamp: float = Field(..., description="Unix timestamp")


class PerformanceAlert(BaseModel):
    """Performance alert details."""

    alert_type: str
    severity: str = Field(..., description="Alert severity: warning or critical")
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    timestamp: float = Field(..., description="Unix timestamp")
    context: Dict[str, Any] = Field(default_factory=dict)


class LatencyReport(BaseModel):
    """Complete latency performance report."""

    endpoints: Dict[str, LatencyMetrics]
    summary: Dict[str, Any]


class QueryReport(BaseModel):
    """Complete query performance report."""

    queries: Dict[str, QueryMetrics]
    slow_queries: List[SlowQuery]
    summary: Dict[str, Any]


class MemoryReport(BaseModel):
    """Complete memory usage report."""

    current: MemoryMetrics
    history: List[Dict[str, Any]]
    growth_rate_mb_per_min: Optional[float] = None


class PerformanceReport(BaseModel):
    """Comprehensive performance report."""

    timestamp: float
    latency: LatencyReport
    queries: QueryReport
    memory: MemoryReport
    alerts: List[PerformanceAlert]


class BaselineRequest(BaseModel):
    """Request to set a performance baseline."""

    method: Optional[str] = None
    endpoint: Optional[str] = None
    operation: Optional[str] = None
    table: Optional[str] = None
    value: float = Field(..., gt=0, description="Baseline value in seconds")


class ThresholdUpdate(BaseModel):
    """Request to update performance thresholds."""

    p50_latency_warning: Optional[float] = None
    p50_latency_critical: Optional[float] = None
    p95_latency_warning: Optional[float] = None
    p95_latency_critical: Optional[float] = None
    p99_latency_warning: Optional[float] = None
    p99_latency_critical: Optional[float] = None
    query_duration_warning: Optional[float] = None
    query_duration_critical: Optional[float] = None
    memory_usage_warning: Optional[int] = None
    memory_usage_critical: Optional[int] = None
    memory_growth_rate_warning: Optional[float] = None
    error_rate_warning: Optional[float] = None
    error_rate_critical: Optional[float] = None
    regression_detection_threshold: Optional[float] = None
    slow_query_threshold: Optional[float] = None


# ========================================
# Helper Functions
# ========================================


def format_timestamp(timestamp: float) -> str:
    """Format Unix timestamp to ISO string."""
    return datetime.fromtimestamp(timestamp).isoformat()


def hash_query(query: str) -> str:
    """Generate a hash for a query string."""
    return hashlib.md5(query.encode()).hexdigest()[:16]


# ========================================
# Performance Metrics Endpoints
# ========================================


@router.get(
    "/metrics",
    response_model=PerformanceReport,
    summary="Get comprehensive performance metrics",
    description="Returns a complete performance report including latency, queries, memory, and active alerts.",
)
async def get_performance_metrics(
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> PerformanceReport:
    """
    Get comprehensive performance metrics.

    Returns:
        PerformanceReport: Complete performance report including latency,
        query performance, memory usage, and active alerts.
    """
    try:
        report = monitor.get_full_report()

        # Format timestamps
        report["timestamp_formatted"] = format_timestamp(report["timestamp"])

        # Format alert timestamps
        for alert in report["alerts"]:
            alert["timestamp_formatted"] = format_timestamp(alert["timestamp"])

        return PerformanceReport(**report)
    except Exception as e:
        logger.error("Failed to get performance metrics", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics",
        )


@router.get(
    "/latency",
    response_model=LatencyReport,
    summary="Get latency metrics",
    description="Returns detailed latency metrics for all endpoints including P50, P95, and P99 percentiles.",
)
async def get_latency_metrics(
    endpoint_filter: Optional[str] = Query(
        None, description="Filter by endpoint path (partial match)"
    ),
    method_filter: Optional[str] = Query(
        None, description="Filter by HTTP method (GET, POST, etc.)"
    ),
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> LatencyReport:
    """
    Get latency metrics.

    Args:
        endpoint_filter: Optional filter for endpoint path
        method_filter: Optional filter for HTTP method

    Returns:
        LatencyReport: Latency metrics report
    """
    try:
        report = monitor.get_latency_report()

        # Apply filters if provided
        if endpoint_filter or method_filter:
            filtered_endpoints = {}
            for key, metrics in report["endpoints"].items():
                method, endpoint = key.split(" ", 1)

                if endpoint_filter and endpoint_filter not in endpoint:
                    continue
                if method_filter and method_filter.upper() != method.upper():
                    continue

                filtered_endpoints[key] = metrics

            report["endpoints"] = filtered_endpoints

        return LatencyReport(**report)
    except Exception as e:
        logger.error("Failed to get latency metrics", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latency metrics",
        )


@router.get(
    "/latency/percentiles",
    summary="Get latency percentiles",
    description="Returns P50, P95, and P99 latency values for all endpoints.",
)
async def get_latency_percentiles(
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> Dict[str, Dict[str, float]]:
    """
    Get latency percentiles summary.

    Returns:
        Dict with P50, P95, P99 values for each endpoint
    """
    try:
        report = monitor.get_latency_report()

        result = {}
        for key, metrics in report.get("endpoints", {}).items():
            result[key] = {
                "p50": metrics["p50"],
                "p95": metrics["p95"],
                "p99": metrics["p99"],
            }

        return result
    except Exception as e:
        logger.error("Failed to get latency percentiles", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latency percentiles",
        )


@router.get(
    "/queries",
    response_model=QueryReport,
    summary="Get query performance metrics",
    description="Returns detailed query performance metrics including slow queries.",
)
async def get_query_metrics(
    operation_filter: Optional[str] = Query(
        None, description="Filter by query operation (SELECT, INSERT, UPDATE, DELETE)"
    ),
    table_filter: Optional[str] = Query(
        None, description="Filter by table name (partial match)"
    ),
    min_duration: Optional[float] = Query(
        None, ge=0, description="Minimum query duration in seconds"
    ),
    limit_slow_queries: int = Query(
        50, ge=1, le=500, description="Maximum number of slow queries to return"
    ),
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> QueryReport:
    """
    Get query performance metrics.

    Args:
        operation_filter: Optional filter for query operation
        table_filter: Optional filter for table name
        min_duration: Optional minimum duration filter
        limit_slow_queries: Maximum slow queries to return

    Returns:
        QueryReport: Query performance report
    """
    try:
        report = monitor.get_query_report()

        # Apply filters to queries
        if operation_filter or table_filter:
            filtered_queries = {}
            for key, metrics in report["queries"].items():
                operation, table = key.split(" ", 1)

                if operation_filter and operation_filter.upper() != operation.upper():
                    continue
                if table_filter and table_filter.lower() not in table.lower():
                    continue

                filtered_queries[key] = metrics

            report["queries"] = filtered_queries

        # Filter slow queries
        if min_duration or limit_slow_queries:
            filtered_slow_queries = report.get("slow_queries", [])

            if min_duration:
                filtered_slow_queries = [
                    q for q in filtered_slow_queries if q["duration"] >= min_duration
                ]

            if limit_slow_queries:
                filtered_slow_queries = filtered_slow_queries[:limit_slow_queries]

            report["slow_queries"] = filtered_slow_queries

        return QueryReport(**report)
    except Exception as e:
        logger.error("Failed to get query metrics", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve query metrics",
        )


@router.get(
    "/queries/slow",
    response_model=List[SlowQuery],
    summary="Get slow queries",
    description="Returns a list of slow queries that exceeded the threshold.",
)
async def get_slow_queries(
    min_duration: Optional[float] = Query(
        None, ge=0, description="Minimum duration in seconds"
    ),
    operation: Optional[str] = Query(
        None, description="Filter by operation type"
    ),
    table: Optional[str] = Query(
        None, description="Filter by table name"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> List[SlowQuery]:
    """
    Get slow queries.

    Args:
        min_duration: Optional minimum duration filter
        operation: Optional operation filter
        table: Optional table filter
        limit: Maximum number of results

    Returns:
        List of slow queries
    """
    try:
        report = monitor.get_query_report()
        slow_queries = report.get("slow_queries", [])

        # Apply filters
        if min_duration:
            slow_queries = [q for q in slow_queries if q["duration"] >= min_duration]

        if operation:
            slow_queries = [
                q for q in slow_queries if q["operation"].upper() == operation.upper()
            ]

        if table:
            slow_queries = [
                q for q in slow_queries if table.lower() in q["table"].lower()
            ]

        # Sort by duration (slowest first) and limit
        slow_queries = sorted(slow_queries, key=lambda x: x["duration"], reverse=True)
        slow_queries = slow_queries[:limit]

        return [SlowQuery(**q) for q in slow_queries]
    except Exception as e:
        logger.error("Failed to get slow queries", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve slow queries",
        )


@router.get(
    "/memory",
    response_model=MemoryReport,
    summary="Get memory usage metrics",
    description="Returns detailed memory usage metrics including historical data.",
)
async def get_memory_metrics(
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> MemoryReport:
    """
    Get memory usage metrics.

    Returns:
        MemoryReport: Memory usage report
    """
    try:
        report = monitor.get_memory_report()

        if "error" in report:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=report["error"],
            )

        return MemoryReport(**report)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get memory metrics", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory metrics",
        )


@router.get(
    "/alerts",
    response_model=List[PerformanceAlert],
    summary="Get active performance alerts",
    description="Returns all active performance alerts.",
)
async def get_active_alerts(
    severity: Optional[str] = Query(
        None, description="Filter by severity (warning or critical)"
    ),
    alert_type: Optional[str] = Query(
        None, description="Filter by alert type"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> List[PerformanceAlert]:
    """
    Get active performance alerts.

    Args:
        severity: Optional severity filter
        alert_type: Optional alert type filter
        limit: Maximum number of results

    Returns:
        List of active alerts
    """
    try:
        alerts = monitor.get_active_alerts()

        # Apply filters
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]

        if alert_type:
            alerts = [a for a in alerts if a["alert_type"] == alert_type]

        # Sort by timestamp (newest first) and limit
        alerts = sorted(alerts, key=lambda x: x["timestamp"], reverse=True)
        alerts = alerts[:limit]

        return [PerformanceAlert(**a) for a in alerts]
    except Exception as e:
        logger.error("Failed to get active alerts", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active alerts",
        )


@router.get(
    "/alerts/count",
    summary="Get alert counts",
    description="Returns count of active alerts by severity.",
)
async def get_alert_counts(
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> Dict[str, int]:
    """
    Get alert counts by severity.

    Returns:
        Dict with warning and critical alert counts
    """
    try:
        alerts = monitor.get_active_alerts()

        return {
            "warning": sum(1 for a in alerts if a["severity"] == "warning"),
            "critical": sum(1 for a in alerts if a["severity"] == "critical"),
            "total": len(alerts),
        }
    except Exception as e:
        logger.error("Failed to get alert counts", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert counts",
        )


# ========================================
# Performance Reports Endpoints
# ========================================


@router.get(
    "/report",
    response_model=PerformanceReport,
    summary="Get performance report",
    description="Returns a comprehensive performance report with all metrics.",
)
async def get_performance_report(
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> PerformanceReport:
    """
    Get comprehensive performance report.

    Returns:
        PerformanceReport: Complete performance report
    """
    try:
        report = monitor.get_full_report()
        return PerformanceReport(**report)
    except Exception as e:
        logger.error("Failed to get performance report", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance report",
        )


@router.get(
    "/report/summary",
    summary="Get performance summary",
    description="Returns a concise summary of key performance metrics.",
)
async def get_performance_summary(
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> Dict[str, Any]:
    """
    Get performance summary.

    Returns:
        Dict with key performance metrics summary
    """
    try:
        latency_report = monitor.get_latency_report()
        query_report = monitor.get_query_report()
        memory_report = monitor.get_memory_report()
        alerts = monitor.get_active_alerts()

        return {
            "latency_summary": latency_report.get("summary", {}),
            "query_summary": query_report.get("summary", {}),
            "memory_current": memory_report.get("current", {}),
            "alert_counts": {
                "warning": sum(1 for a in alerts if a["severity"] == "warning"),
                "critical": sum(1 for a in alerts if a["severity"] == "critical"),
                "total": len(alerts),
            },
        }
    except Exception as e:
        logger.error("Failed to get performance summary", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance summary",
        )


# ========================================
# Baseline Management Endpoints
# ========================================


@router.post(
    "/baseline/latency",
    status_code=status.HTTP_201_CREATED,
    summary="Set latency baseline",
    description="Set a baseline value for latency monitoring and regression detection.",
)
async def set_latency_baseline(
    request: BaselineRequest,
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> Dict[str, Any]:
    """
    Set latency baseline.

    Args:
        request: Baseline request with method, endpoint, and value

    Returns:
        Confirmation message
    """
    if not request.method or not request.endpoint:
        raise ValidationError(
            "method, endpoint",
            "Both method and endpoint are required for latency baseline",
            details={"method": request.method, "endpoint": request.endpoint}
        )

    try:
        monitor.set_latency_baseline(
            method=request.method.upper(),
            endpoint=request.endpoint,
            value=request.value,
        )

        logger.info(
            "Latency baseline set",
            method=request.method,
            endpoint=request.endpoint,
            value=request.value,
        )

        return {
            "status": "success",
            "message": f"Latency baseline set to {request.value}s for {request.method} {request.endpoint}",
            "baseline": {
                "method": request.method,
                "endpoint": request.endpoint,
                "value": request.value,
            },
        }
    except Exception as e:
        logger.error("Failed to set latency baseline", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set latency baseline",
        )


@router.post(
    "/baseline/query",
    status_code=status.HTTP_201_CREATED,
    summary="Set query baseline",
    description="Set a baseline value for query performance monitoring and regression detection.",
)
async def set_query_baseline(
    request: BaselineRequest,
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> Dict[str, Any]:
    """
    Set query baseline.

    Args:
        request: Baseline request with operation, table, and value

    Returns:
        Confirmation message
    """
    if not request.operation or not request.table:
        raise ValidationError(
            "operation, table",
            "Both operation and table are required for query baseline",
            details={"operation": request.operation, "table": request.table}
        )

    try:
        monitor.set_query_baseline(
            operation=request.operation.upper(),
            table=request.table,
            value=request.value,
        )

        logger.info(
            "Query baseline set",
            operation=request.operation,
            table=request.table,
            value=request.value,
        )

        return {
            "status": "success",
            "message": f"Query baseline set to {request.value}s for {request.operation} {request.table}",
            "baseline": {
                "operation": request.operation,
                "table": request.table,
                "value": request.value,
            },
        }
    except Exception as e:
        logger.error("Failed to set query baseline", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set query baseline",
        )


@router.get(
    "/baseline",
    summary="Get performance baselines",
    description="Returns all configured performance baselines.",
)
async def get_baselines(
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> Dict[str, Any]:
    """
    Get all performance baselines.

    Returns:
        Dict with all configured baselines
    """
    try:
        return {
            "latency_baselines": {
                f"{method} {endpoint}": value
                for (method, endpoint), value in monitor._baseline_latencies.items()
            },
            "query_baselines": {
                f"{operation} {table}": value
                for (operation, table), value in monitor._baseline_queries.items()
            },
        }
    except Exception as e:
        logger.error("Failed to get baselines", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve baselines",
        )


@router.delete(
    "/baseline/latency/{method}/{endpoint:path}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete latency baseline",
    description="Remove a latency baseline for regression detection.",
)
async def delete_latency_baseline(
    method: str,
    endpoint: str,
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> None:
    """
    Delete latency baseline.

    Args:
        method: HTTP method
        endpoint: Endpoint path
    """
    try:
        key = (method.upper(), endpoint)
        if key in monitor._baseline_latencies:
            del monitor._baseline_latencies[key]
            logger.info("Latency baseline deleted", method=method, endpoint=endpoint)
    except Exception as e:
        logger.error("Failed to delete latency baseline", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete latency baseline",
        )


@router.delete(
    "/baseline/query/{operation}/{table}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete query baseline",
    description="Remove a query baseline for regression detection.",
)
async def delete_query_baseline(
    operation: str,
    table: str,
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> None:
    """
    Delete query baseline.

    Args:
        operation: Query operation
        table: Table name
    """
    try:
        key = (operation.upper(), table)
        if key in monitor._baseline_queries:
            del monitor._baseline_queries[key]
            logger.info("Query baseline deleted", operation=operation, table=table)
    except Exception as e:
        logger.error("Failed to delete query baseline", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete query baseline",
        )


# ========================================
# Threshold Management Endpoints
# ========================================


@router.get(
    "/thresholds",
    summary="Get performance thresholds",
    description="Returns current performance alerting thresholds.",
)
async def get_thresholds(
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> Dict[str, Any]:
    """
    Get current performance thresholds.

    Returns:
        Dict with all threshold values
    """
    try:
        t = monitor.thresholds
        return {
            "latency": {
                "p50_warning": t.p50_latency_warning,
                "p50_critical": t.p50_latency_critical,
                "p95_warning": t.p95_latency_warning,
                "p95_critical": t.p95_latency_critical,
                "p99_warning": t.p99_latency_warning,
                "p99_critical": t.p99_latency_critical,
            },
            "query": {
                "duration_warning": t.query_duration_warning,
                "duration_critical": t.query_duration_critical,
                "slow_query_threshold": t.slow_query_threshold,
            },
            "memory": {
                "usage_warning": t.memory_usage_warning,
                "usage_critical": t.memory_usage_critical,
                "growth_rate_warning": t.memory_growth_rate_warning,
            },
            "error_rate": {
                "warning": t.error_rate_warning,
                "critical": t.error_rate_critical,
            },
            "regression_detection": {
                "threshold": t.regression_detection_threshold,
                "window": t.regression_detection_window,
            },
        }
    except Exception as e:
        logger.error("Failed to get thresholds", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve thresholds",
        )


@router.put(
    "/thresholds",
    status_code=status.HTTP_200_OK,
    summary="Update performance thresholds",
    description="Update performance alerting thresholds dynamically.",
)
async def update_thresholds(
    request: ThresholdUpdate,
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> Dict[str, Any]:
    """
    Update performance thresholds.

    Args:
        request: Threshold update request

    Returns:
        Updated threshold values
    """
    try:
        t = monitor.thresholds

        # Update latency thresholds
        if request.p50_latency_warning is not None:
            t.p50_latency_warning = request.p50_latency_warning
        if request.p50_latency_critical is not None:
            t.p50_latency_critical = request.p50_latency_critical
        if request.p95_latency_warning is not None:
            t.p95_latency_warning = request.p95_latency_warning
        if request.p95_latency_critical is not None:
            t.p95_latency_critical = request.p95_latency_critical
        if request.p99_latency_warning is not None:
            t.p99_latency_warning = request.p99_latency_warning
        if request.p99_latency_critical is not None:
            t.p99_latency_critical = request.p99_latency_critical

        # Update query thresholds
        if request.query_duration_warning is not None:
            t.query_duration_warning = request.query_duration_warning
        if request.query_duration_critical is not None:
            t.query_duration_critical = request.query_duration_critical
        if request.slow_query_threshold is not None:
            t.slow_query_threshold = request.slow_query_threshold

        # Update memory thresholds
        if request.memory_usage_warning is not None:
            t.memory_usage_warning = request.memory_usage_warning
        if request.memory_usage_critical is not None:
            t.memory_usage_critical = request.memory_usage_critical
        if request.memory_growth_rate_warning is not None:
            t.memory_growth_rate_warning = request.memory_growth_rate_warning

        # Update error rate thresholds
        if request.error_rate_warning is not None:
            t.error_rate_warning = request.error_rate_warning
        if request.error_rate_critical is not None:
            t.error_rate_critical = request.error_rate_critical

        # Update regression detection thresholds
        if request.regression_detection_threshold is not None:
            t.regression_detection_threshold = request.regression_detection_threshold

        logger.info("Performance thresholds updated")

        # Return updated thresholds
        return await get_thresholds(monitor)
    except Exception as e:
        logger.error("Failed to update thresholds", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update thresholds",
        )


# ========================================
# Health and Status Endpoints
# ========================================


@router.get(
    "/status",
    summary="Get performance monitoring status",
    description="Returns the status of the performance monitoring system.",
)
async def get_performance_status(
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> Dict[str, Any]:
    """
    Get performance monitoring system status.

    Returns:
        Dict with system status information
    """
    try:
        latency_report = monitor.get_latency_report()
        query_report = monitor.get_query_report()
        memory_report = monitor.get_memory_report()
        alerts = monitor.get_active_alerts()

        critical_alerts = [a for a in alerts if a["severity"] == "critical"]

        # Determine overall health
        health_status = "healthy"
        if critical_alerts:
            health_status = "critical"
        elif alerts:
            health_status = "degraded"

        return {
            "status": health_status,
            "monitoring_active": monitor._monitoring_active,
            "tracemalloc_enabled": monitor.enable_tracemalloc,
            "latency_samples": sum(
                len(samples) for samples in monitor._latency_samples.values()
            ),
            "query_samples": sum(
                len(samples) for samples in monitor._query_samples.values()
            ),
            "memory_snapshots": len(monitor._memory_snapshots),
            "active_alerts": len(alerts),
            "critical_alerts": len(critical_alerts),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error("Failed to get performance status", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance status",
        )


@router.post(
    "/snapshot",
    summary="Trigger memory snapshot",
    description="Manually trigger a memory usage snapshot.",
)
async def trigger_memory_snapshot(
    monitor: PerformanceMonitor = Depends(get_performance_monitor),
) -> Dict[str, Any]:
    """
    Trigger a memory snapshot.

    Returns:
        Memory snapshot data
    """
    try:
        snapshot = monitor.capture_memory_snapshot()

        return {
            "timestamp": format_timestamp(snapshot.timestamp),
            "rss_mb": snapshot.rss_mb,
            "vms_mb": snapshot.vms_mb,
            "heap_mb": snapshot.heap_mb,
            "thread_count": snapshot.thread_count,
            "open_files": snapshot.open_files,
        }
    except Exception as e:
        logger.error("Failed to trigger memory snapshot", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to capture memory snapshot",
        )
