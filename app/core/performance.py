"""
Performance monitoring and alerting system.

Provides comprehensive performance tracking including:
- Request latency metrics (P50, P95, P99)
- Query performance tracking
- Memory usage monitoring
- Performance regression detection
- Alerting thresholds
"""

import asyncio
import gc
import os
import psutil
import threading
import time
import tracemalloc
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from statistics import median
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Deque,
    Dict,
    Generator,
    List,
    Optional,
    ParamSpec,
    TypeVar,
)

from prometheus_client import Counter, Gauge, Histogram, Info

from app.core.logging import get_logger
from app.core.metrics import registry

logger = get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

# ========================================
# Performance Thresholds Configuration
# ========================================


@dataclass
class PerformanceThresholds:
    """Configuration for performance alerting thresholds."""

    # Latency thresholds (in seconds)
    p50_latency_warning: float = 0.1  # 100ms
    p50_latency_critical: float = 0.25  # 250ms
    p95_latency_warning: float = 0.5  # 500ms
    p95_latency_critical: float = 1.0  # 1s
    p99_latency_warning: float = 1.0  # 1s
    p99_latency_critical: float = 2.5  # 2.5s

    # Query duration thresholds (in seconds)
    query_duration_warning: float = 0.1  # 100ms
    query_duration_critical: float = 0.5  # 500ms

    # Memory thresholds (in MB)
    memory_usage_warning: int = 512  # 512MB
    memory_usage_critical: int = 1024  # 1GB
    memory_growth_rate_warning: float = 10.0  # MB per minute

    # Error rate thresholds (percentage)
    error_rate_warning: float = 1.0  # 1%
    error_rate_critical: float = 5.0  # 5%

    # Queue length thresholds
    queue_length_warning: int = 50
    queue_length_critical: int = 100

    # Regression detection thresholds (percentage change)
    regression_detection_threshold: float = 20.0  # 20% increase
    regression_detection_window: int = 5  # Number of samples to compare

    # Slow query log thresholds
    slow_query_threshold: float = 0.1  # 100ms

    @classmethod
    def from_settings(cls, settings: Any) -> "PerformanceThresholds":
        """Create thresholds from application settings."""
        return cls()


# ========================================
# Performance Metrics Data Classes
# ========================================


@dataclass
class LatencySample:
    """Represents a single latency sample."""

    timestamp: float
    value: float
    endpoint: str
    method: str
    status_code: int
    request_id: Optional[str] = None


@dataclass
class QuerySample:
    """Represents a single query performance sample."""

    timestamp: float
    duration: float
    operation: str
    table: str
    query_hash: str
    affected_rows: int = 0
    request_id: Optional[str] = None


@dataclass
class MemorySnapshot:
    """Represents a memory usage snapshot."""

    timestamp: float
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    heap_mb: float  # Heap memory (if tracemalloc enabled)
    thread_count: int
    open_files: int


@dataclass
class PerformanceAlert:
    """Represents a performance alert."""

    alert_type: str
    severity: str  # "warning", "critical"
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegressionDetectionResult:
    """Result of performance regression detection."""

    detected: bool
    metric_name: str
    baseline_value: float
    current_value: float
    percent_change: float
    severity: str  # "warning", "critical"
    timestamp: float
    details: str


# ========================================
# Performance Metrics (Prometheus)
# ========================================

# Latency histograms with custom buckets for P50, P95, P99
request_latency_histogram = Histogram(
    "performance_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint", "status"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

# Latency percentiles as gauges
request_latency_p50 = Gauge(
    "performance_request_latency_p50_seconds",
    "Request latency P50 (median) in seconds",
    ["method", "endpoint"],
    registry=registry,
)

request_latency_p95 = Gauge(
    "performance_request_latency_p95_seconds",
    "Request latency P95 in seconds",
    ["method", "endpoint"],
    registry=registry,
)

request_latency_p99 = Gauge(
    "performance_request_latency_p99_seconds",
    "Request latency P99 in seconds",
    ["method", "endpoint"],
    registry=registry,
)

# Query performance
query_latency_histogram = Histogram(
    "performance_query_latency_seconds",
    "Database query latency in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=registry,
)

slow_query_counter = Counter(
    "performance_slow_queries_total",
    "Total number of slow queries",
    ["operation", "table"],
    registry=registry,
)

# Memory metrics
memory_usage_gauge = Gauge(
    "performance_memory_usage_mb",
    "Process memory usage in MB",
    ["type"],  # rss, vms, heap
    registry=registry,
)

memory_growth_rate_gauge = Gauge(
    "performance_memory_growth_rate_mb_per_min",
    "Memory growth rate in MB per minute",
    registry=registry,
)

gc_collections = Counter(
    "performance_gc_collections_total",
    "Garbage collection cycles",
    ["generation"],
    registry=registry,
)

# Alert metrics
performance_alerts_total = Counter(
    "performance_alerts_total",
    "Total performance alerts triggered",
    ["alert_type", "severity"],
    registry=registry,
)

active_alerts_gauge = Gauge(
    "performance_active_alerts",
    "Number of active performance alerts",
    ["severity"],
    registry=registry,
)

regression_detected_total = Counter(
    "performance_regressions_detected_total",
    "Total performance regressions detected",
    ["metric_name", "severity"],
    registry=registry,
)

# Performance metadata
performance_info = Info(
    "performance_info",
    "Performance monitoring system information",
    registry=registry,
)


# ========================================
# Performance Monitor Class
# ========================================


class PerformanceMonitor:
    """
    Central performance monitoring system.

    Tracks request latency, query performance, memory usage,
    detects regressions, and generates alerts.
    """

    _instance: Optional["PerformanceMonitor"] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for performance monitor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        thresholds: Optional[PerformanceThresholds] = None,
        latency_window_size: int = 1000,
        query_window_size: int = 500,
        memory_window_size: int = 60,
        enable_tracemalloc: bool = False,
    ):
        """
        Initialize performance monitor.

        Args:
            thresholds: Performance alerting thresholds
            latency_window_size: Number of latency samples to keep
            query_window_size: Number of query samples to keep
            memory_window_size: Number of memory snapshots to keep
            enable_tracemalloc: Enable detailed memory tracking
        """
        if hasattr(self, "_initialized"):
            return

        self.thresholds = thresholds or PerformanceThresholds()
        self.enable_tracemalloc = enable_tracemalloc

        # Latency tracking: key = (method, endpoint), value = deque of samples
        self._latency_samples: Dict[
            tuple, Deque[LatencySample]
        ] = defaultdict(lambda: deque(maxlen=latency_window_size))

        # Query tracking: key = (operation, table), value = deque of samples
        self._query_samples: Dict[
            tuple, Deque[QuerySample]
        ] = defaultdict(lambda: deque(maxlen=query_window_size))

        # Memory tracking
        self._memory_snapshots: Deque[MemorySnapshot] = deque(
            maxlen=memory_window_size
        )

        # Active alerts
        self._active_alerts: List[PerformanceAlert] = []
        self._alert_lock = threading.Lock()

        # Baseline metrics for regression detection
        self._baseline_latencies: Dict[tuple, float] = {}
        self._baseline_queries: Dict[tuple, float] = {}

        # Process info for memory tracking
        self._process = psutil.Process(os.getpid())

        # Metrics tracking
        self._total_requests: int = 0
        self._total_errors: int = 0

        # Initialize
        if self.enable_tracemalloc:
            tracemalloc.start()

        # Start background monitoring
        self._monitoring_active = False
        self._monitor_task: Optional[asyncio.Task] = None

        self._initialized = True
        performance_info.info({"version": "1.0.0", "tracemalloc_enabled": str(enable_tracemalloc)})
        logger.info("Performance monitor initialized", enable_tracemalloc=enable_tracemalloc)

    async def start(self) -> None:
        """Start background performance monitoring."""
        if self._monitoring_active:
            return

        self._monitoring_active = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Performance monitoring started")

    async def stop(self) -> None:
        """Stop background performance monitoring."""
        if not self._monitoring_active:
            return

        self._monitoring_active = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Performance monitoring stopped")

    async def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                # Capture memory snapshot
                self.capture_memory_snapshot()

                # Update latency percentiles
                self._update_latency_percentiles()

                # Check for regressions
                await self._check_regressions()

                # Clean old alerts
                self._cleanup_old_alerts()

                # Wait before next iteration
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in performance monitor loop", exc_info=e)

    # ========================================
    # Request Latency Tracking
    # ========================================

    def record_latency(
        self,
        method: str,
        endpoint: str,
        duration: float,
        status_code: int,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Record a request latency sample.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Request endpoint path
            duration: Request duration in seconds
            status_code: HTTP status code
            request_id: Optional request ID for correlation
        """
        key = (method, endpoint)
        sample = LatencySample(
            timestamp=time.time(),
            value=duration,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            request_id=request_id,
        )

        self._latency_samples[key].append(sample)

        # Track totals for error rate calculation
        self._total_requests += 1
        if status_code >= 400:
            self._total_errors += 1

        # Record to Prometheus
        request_latency_histogram.labels(
            method=method, endpoint=endpoint, status=status_code
        ).observe(duration)

        # Check for latency alerts
        self._check_latency_alerts(key, sample)

    def _update_latency_percentiles(self) -> None:
        """Update Prometheus gauges with current latency percentiles."""
        for key, samples in self._latency_samples.items():
            if len(samples) < 10:  # Need minimum samples
                continue

            method, endpoint = key
            values = [s.value for s in samples]

            # Calculate percentiles
            sorted_values = sorted(values)
            n = len(sorted_values)

            p50 = sorted_values[n // 2]
            p95 = sorted_values[int(n * 0.95)] if n >= 20 else sorted_values[-1]
            p99 = sorted_values[int(n * 0.99)] if n >= 100 else sorted_values[-1]

            # Update gauges
            request_latency_p50.labels(method=method, endpoint=endpoint).set(p50)
            request_latency_p95.labels(method=method, endpoint=endpoint).set(p95)
            request_latency_p99.labels(method=method, endpoint=endpoint).set(p99)

    def _check_latency_alerts(self, key: tuple, sample: LatencySample) -> None:
        """Check latency against thresholds and generate alerts."""
        method, endpoint = key
        samples = self._latency_samples[key]

        if len(samples) < 10:
            return

        values = [s.value for s in samples]
        sorted_values = sorted(values)
        n = len(sorted_values)

        p50 = sorted_values[n // 2]
        p95 = sorted_values[int(n * 0.95)] if n >= 20 else sorted_values[-1]
        p99 = sorted_values[int(n * 0.99)] if n >= 100 else sorted_values[-1]

        # Check P50
        if p50 > self.thresholds.p50_latency_critical:
            self._trigger_alert(
                alert_type="latency_p50",
                severity="critical",
                metric_name=f"{method} {endpoint}",
                current_value=p50,
                threshold_value=self.thresholds.p50_latency_critical,
                message=f"P50 latency critical: {p50:.3f}s > {self.thresholds.p50_latency_critical}s",
                context={"percentile": "P50", "endpoint": endpoint, "method": method},
            )
        elif p50 > self.thresholds.p50_latency_warning:
            self._trigger_alert(
                alert_type="latency_p50",
                severity="warning",
                metric_name=f"{method} {endpoint}",
                current_value=p50,
                threshold_value=self.thresholds.p50_latency_warning,
                message=f"P50 latency warning: {p50:.3f}s > {self.thresholds.p50_latency_warning}s",
                context={"percentile": "P50", "endpoint": endpoint, "method": method},
            )

        # Check P95
        if p95 > self.thresholds.p95_latency_critical:
            self._trigger_alert(
                alert_type="latency_p95",
                severity="critical",
                metric_name=f"{method} {endpoint}",
                current_value=p95,
                threshold_value=self.thresholds.p95_latency_critical,
                message=f"P95 latency critical: {p95:.3f}s > {self.thresholds.p95_latency_critical}s",
                context={"percentile": "P95", "endpoint": endpoint, "method": method},
            )
        elif p95 > self.thresholds.p95_latency_warning:
            self._trigger_alert(
                alert_type="latency_p95",
                severity="warning",
                metric_name=f"{method} {endpoint}",
                current_value=p95,
                threshold_value=self.thresholds.p95_latency_warning,
                message=f"P95 latency warning: {p95:.3f}s > {self.thresholds.p95_latency_warning}s",
                context={"percentile": "P95", "endpoint": endpoint, "method": method},
            )

        # Check P99
        if p99 > self.thresholds.p99_latency_critical:
            self._trigger_alert(
                alert_type="latency_p99",
                severity="critical",
                metric_name=f"{method} {endpoint}",
                current_value=p99,
                threshold_value=self.thresholds.p99_latency_critical,
                message=f"P99 latency critical: {p99:.3f}s > {self.thresholds.p99_latency_critical}s",
                context={"percentile": "P99", "endpoint": endpoint, "method": method},
            )
        elif p99 > self.thresholds.p99_latency_warning:
            self._trigger_alert(
                alert_type="latency_p99",
                severity="warning",
                metric_name=f"{method} {endpoint}",
                current_value=p99,
                threshold_value=self.thresholds.p99_latency_warning,
                message=f"P99 latency warning: {p99:.3f}s > {self.thresholds.p99_latency_warning}s",
                context={"percentile": "P99", "endpoint": endpoint, "method": method},
            )

    # ========================================
    # Query Performance Tracking
    # ========================================

    def record_query(
        self,
        operation: str,
        table: str,
        duration: float,
        query_hash: str,
        affected_rows: int = 0,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Record a database query performance sample.

        Args:
            operation: Query operation (SELECT, INSERT, UPDATE, DELETE)
            table: Database table name
            duration: Query duration in seconds
            query_hash: Hash of the query for aggregation
            affected_rows: Number of rows affected
            request_id: Optional request ID for correlation
        """
        key = (operation, table)
        sample = QuerySample(
            timestamp=time.time(),
            duration=duration,
            operation=operation,
            table=table,
            query_hash=query_hash,
            affected_rows=affected_rows,
            request_id=request_id,
        )

        self._query_samples[key].append(sample)

        # Record to Prometheus
        query_latency_histogram.labels(
            operation=operation, table=table
        ).observe(duration)

        # Check for slow query
        if duration > self.thresholds.slow_query_threshold:
            slow_query_counter.labels(operation=operation, table=table).inc()

        # Check for query alerts
        self._check_query_alerts(key, sample)

    def _check_query_alerts(self, key: tuple, sample: QuerySample) -> None:
        """Check query duration against thresholds and generate alerts."""
        operation, table = key
        samples = self._query_samples[key]

        if len(samples) < 5:
            return

        # Calculate average duration for recent queries
        recent_values = [s.duration for s in list(samples)[-20:]]
        avg_duration = sum(recent_values) / len(recent_values)

        if avg_duration > self.thresholds.query_duration_critical:
            self._trigger_alert(
                alert_type="query_performance",
                severity="critical",
                metric_name=f"{operation} {table}",
                current_value=avg_duration,
                threshold_value=self.thresholds.query_duration_critical,
                message=f"Query performance critical: {avg_duration:.3f}s avg > {self.thresholds.query_duration_critical}s",
                context={"operation": operation, "table": table},
            )
        elif avg_duration > self.thresholds.query_duration_warning:
            self._trigger_alert(
                alert_type="query_performance",
                severity="warning",
                metric_name=f"{operation} {table}",
                current_value=avg_duration,
                threshold_value=self.thresholds.query_duration_warning,
                message=f"Query performance warning: {avg_duration:.3f}s avg > {self.thresholds.query_duration_warning}s",
                context={"operation": operation, "table": table},
            )

    # ========================================
    # Memory Usage Tracking
    # ========================================

    def capture_memory_snapshot(self) -> MemorySnapshot:
        """
        Capture current memory usage snapshot.

        Returns:
            MemorySnapshot: Current memory usage statistics
        """
        try:
            memory_info = self._process.memory_info()
            rss_mb = memory_info.rss / (1024 * 1024)
            vms_mb = memory_info.vms / (1024 * 1024)

            heap_mb = 0.0
            if self.enable_tracemalloc:
                current, peak = tracemalloc.get_traced_memory()
                heap_mb = current / (1024 * 1024)

            thread_count = self._process.num_threads()
            open_files = len(self._process.open_files())

            snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=rss_mb,
                vms_mb=vms_mb,
                heap_mb=heap_mb,
                thread_count=thread_count,
                open_files=open_files,
            )

            self._memory_snapshots.append(snapshot)

            # Update Prometheus gauges
            memory_usage_gauge.labels(type="rss").set(rss_mb)
            memory_usage_gauge.labels(type="vms").set(vms_mb)
            memory_usage_gauge.labels(type="heap").set(heap_mb)

            # Calculate memory growth rate
            if len(self._memory_snapshots) >= 2:
                recent_snapshots = list(self._memory_snapshots)[-10:]
                oldest = recent_snapshots[0]
                newest = recent_snapshots[-1]
                time_diff = newest.timestamp - oldest.timestamp

                if time_diff > 0:
                    growth_rate = (newest.rss_mb - oldest.rss_mb) / (time_diff / 60)  # MB/min
                    memory_growth_rate_gauge.set(growth_rate)

            # Check for memory alerts
            self._check_memory_alerts(snapshot)

            return snapshot
        except Exception as e:
            logger.error("Failed to capture memory snapshot", exc_info=e)
            # Return empty snapshot
            return MemorySnapshot(
                timestamp=time.time(), rss_mb=0, vms_mb=0, heap_mb=0, thread_count=0, open_files=0
            )

    def _check_memory_alerts(self, snapshot: MemorySnapshot) -> None:
        """Check memory usage against thresholds and generate alerts."""
        # Check RSS usage
        if snapshot.rss_mb > self.thresholds.memory_usage_critical:
            self._trigger_alert(
                alert_type="memory_usage",
                severity="critical",
                metric_name="rss_mb",
                current_value=snapshot.rss_mb,
                threshold_value=self.thresholds.memory_usage_critical,
                message=f"Memory usage critical: {snapshot.rss_mb:.1f}MB > {self.thresholds.memory_usage_critical}MB",
                context={
                    "rss_mb": snapshot.rss_mb,
                    "vms_mb": snapshot.vms_mb,
                    "thread_count": snapshot.thread_count,
                },
            )
        elif snapshot.rss_mb > self.thresholds.memory_usage_warning:
            self._trigger_alert(
                alert_type="memory_usage",
                severity="warning",
                metric_name="rss_mb",
                current_value=snapshot.rss_mb,
                threshold_value=self.thresholds.memory_usage_warning,
                message=f"Memory usage warning: {snapshot.rss_mb:.1f}MB > {self.thresholds.memory_usage_warning}MB",
                context={
                    "rss_mb": snapshot.rss_mb,
                    "vms_mb": snapshot.vms_mb,
                    "thread_count": snapshot.thread_count,
                },
            )

        # Check growth rate
        if len(self._memory_snapshots) >= 2:
            recent = list(self._memory_snapshots)[-10:]
            oldest = recent[0]
            newest = recent[-1]
            time_diff = newest.timestamp - oldest.timestamp

            if time_diff > 0:
                growth_rate = (newest.rss_mb - oldest.rss_mb) / (time_diff / 60)
                if growth_rate > self.thresholds.memory_growth_rate_warning:
                    self._trigger_alert(
                        alert_type="memory_growth",
                        severity="warning",
                        metric_name="growth_rate_mb_per_min",
                        current_value=growth_rate,
                        threshold_value=self.thresholds.memory_growth_rate_warning,
                        message=f"Memory growth rate high: {growth_rate:.1f}MB/min > {self.thresholds.memory_growth_rate_warning}MB/min",
                        context={"growth_rate_mb_per_min": growth_rate},
                    )

    # ========================================
    # Performance Regression Detection
    # ========================================

    def set_latency_baseline(self, method: str, endpoint: str, value: float) -> None:
        """Set baseline latency for a specific endpoint."""
        key = (method, endpoint)
        self._baseline_latencies[key] = value
        logger.debug("Set latency baseline", key=key, value=value)

    def set_query_baseline(self, operation: str, table: str, value: float) -> None:
        """Set baseline query duration for a specific operation/table."""
        key = (operation, table)
        self._baseline_queries[key] = value
        logger.debug("Set query baseline", key=key, value=value)

    async def _check_regressions(self) -> List[RegressionDetectionResult]:
        """
        Check for performance regressions against baselines.

        Returns:
            List of detected regressions
        """
        results = []

        # Check latency regressions
        for key, samples in self._latency_samples.items():
            if len(samples) < self.thresholds.regression_detection_window:
                continue

            if key not in self._baseline_latencies:
                continue

            baseline = self._baseline_latencies[key]
            recent_samples = list(samples)[-self.thresholds.regression_detection_window :]
            current = median([s.value for s in recent_samples])

            percent_change = ((current - baseline) / baseline) * 100

            if percent_change > self.thresholds.regression_detection_threshold:
                severity = "critical" if percent_change > 50 else "warning"

                result = RegressionDetectionResult(
                    detected=True,
                    metric_name=f"{key[0]} {key[1]}",
                    baseline_value=baseline,
                    current_value=current,
                    percent_change=percent_change,
                    severity=severity,
                    timestamp=time.time(),
                    details=f"Latency increased by {percent_change:.1f}% from baseline {baseline:.3f}s to {current:.3f}s",
                )

                results.append(result)

                # Record to Prometheus
                regression_detected_total.labels(
                    metric_name=result.metric_name, severity=severity
                ).inc()

                logger.warning(
                    "Performance regression detected",
                    metric_name=result.metric_name,
                    baseline=baseline,
                    current=current,
                    percent_change=percent_change,
                )

        # Check query regressions
        for key, samples in self._query_samples.items():
            if len(samples) < self.thresholds.regression_detection_window:
                continue

            if key not in self._baseline_queries:
                continue

            baseline = self._baseline_queries[key]
            recent_samples = list(samples)[-self.thresholds.regression_detection_window :]
            current = median([s.duration for s in recent_samples])

            percent_change = ((current - baseline) / baseline) * 100

            if percent_change > self.thresholds.regression_detection_threshold:
                severity = "critical" if percent_change > 50 else "warning"

                result = RegressionDetectionResult(
                    detected=True,
                    metric_name=f"{key[0]} {key[1]}",
                    baseline_value=baseline,
                    current_value=current,
                    percent_change=percent_change,
                    severity=severity,
                    timestamp=time.time(),
                    details=f"Query duration increased by {percent_change:.1f}% from baseline {baseline:.3f}s to {current:.3f}s",
                )

                results.append(result)

                # Record to Prometheus
                regression_detected_total.labels(
                    metric_name=result.metric_name, severity=severity
                ).inc()

                logger.warning(
                    "Query performance regression detected",
                    metric_name=result.metric_name,
                    baseline=baseline,
                    current=current,
                    percent_change=percent_change,
                )

        return results

    # ========================================
    # Alert Management
    # ========================================

    def _trigger_alert(
        self,
        alert_type: str,
        severity: str,
        metric_name: str,
        current_value: float,
        threshold_value: float,
        message: str,
        context: Dict[str, Any],
    ) -> None:
        """Trigger a performance alert."""
        with self._alert_lock:
            alert = PerformanceAlert(
                alert_type=alert_type,
                severity=severity,
                metric_name=metric_name,
                current_value=current_value,
                threshold_value=threshold_value,
                message=message,
                timestamp=time.time(),
                context=context,
            )

            # Check for duplicate alert (same type, metric, severity within last minute)
            recent_duplicate = any(
                a.alert_type == alert_type
                and a.metric_name == metric_name
                and a.severity == severity
                and (alert.timestamp - a.timestamp) < 60
                for a in self._active_alerts
            )

            if not recent_duplicate:
                self._active_alerts.append(alert)
                logger.warning(
                    "Performance alert triggered",
                    alert_type=alert_type,
                    severity=severity,
                    metric_name=metric_name,
                    current_value=current_value,
                    threshold_value=threshold_value,
                    message=message,
                )

                # Record to Prometheus
                performance_alerts_total.labels(alert_type=alert_type, severity=severity).inc()

    def _cleanup_old_alerts(self, max_age_seconds: int = 300) -> None:
        """Remove old alerts from active list."""
        with self._alert_lock:
            cutoff = time.time() - max_age_seconds
            self._active_alerts = [a for a in self._active_alerts if a.timestamp > cutoff]

        # Update active alerts gauge
        warning_count = sum(1 for a in self._active_alerts if a.severity == "warning")
        critical_count = sum(1 for a in self._active_alerts if a.severity == "critical")

        active_alerts_gauge.labels(severity="warning").set(warning_count)
        active_alerts_gauge.labels(severity="critical").set(critical_count)

    # ========================================
    # Performance Reports
    # ========================================

    def get_latency_report(self) -> Dict[str, Any]:
        """Generate latency performance report."""
        report = {"endpoints": {}, "summary": {}}

        all_values = []

        for key, samples in self._latency_samples.items():
            if len(samples) < 10:
                continue

            method, endpoint = key
            values = [s.value for s in samples]
            sorted_values = sorted(values)
            n = len(sorted_values)

            p50 = sorted_values[n // 2]
            p95 = sorted_values[int(n * 0.95)] if n >= 20 else sorted_values[-1]
            p99 = sorted_values[int(n * 0.99)] if n >= 100 else sorted_values[-1]

            report["endpoints"][f"{method} {endpoint}"] = {
                "count": len(samples),
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
            }

            all_values.extend(values)

        if all_values:
            all_sorted = sorted(all_values)
            n_all = len(all_sorted)
            report["summary"] = {
                "total_requests": len(all_values),
                "p50": all_sorted[n_all // 2],
                "p95": all_sorted[int(n_all * 0.95)] if n_all >= 20 else all_sorted[-1],
                "p99": all_sorted[int(n_all * 0.99)] if n_all >= 100 else all_sorted[-1],
                "error_rate": (self._total_errors / self._total_requests * 100)
                if self._total_requests > 0
                else 0,
            }

        return report

    def get_query_report(self) -> Dict[str, Any]:
        """Generate query performance report."""
        report = {"queries": {}, "slow_queries": [], "summary": {}}

        all_durations = []

        for key, samples in self._query_samples.items():
            if len(samples) < 5:
                continue

            operation, table = key
            durations = [s.duration for s in samples]

            report["queries"][f"{operation} {table}"] = {
                "count": len(samples),
                "avg": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations),
                "total": sum(durations),
            }

            # Track slow queries
            slow = [s for s in samples if s.duration > self.thresholds.slow_query_threshold]
            if slow:
                report["slow_queries"].extend(
                    [
                        {
                            "operation": s.operation,
                            "table": s.table,
                            "duration": s.duration,
                            "timestamp": s.timestamp,
                            "query_hash": s.query_hash,
                            "request_id": s.request_id,
                        }
                        for s in slow[-10:]  # Last 10 slow queries
                    ]
                )

            all_durations.extend(durations)

        if all_durations:
            report["summary"] = {
                "total_queries": len(all_durations),
                "avg_duration": sum(all_durations) / len(all_durations),
                "max_duration": max(all_durations),
                "min_duration": min(all_durations),
                "total_duration": sum(all_durations),
            }

        return report

    def get_memory_report(self) -> Dict[str, Any]:
        """Generate memory usage report."""
        if not self._memory_snapshots:
            return {"error": "No memory snapshots available"}

        snapshots = list(self._memory_snapshots)
        latest = snapshots[-1]

        report = {
            "current": {
                "rss_mb": latest.rss_mb,
                "vms_mb": latest.vms_mb,
                "heap_mb": latest.heap_mb,
                "thread_count": latest.thread_count,
                "open_files": latest.open_files,
                "timestamp": latest.timestamp,
            },
            "history": [],
        }

        # Add historical data points
        for snapshot in snapshots[::10]:  # Every 10th snapshot
            report["history"].append(
                {
                    "timestamp": snapshot.timestamp,
                    "rss_mb": snapshot.rss_mb,
                    "vms_mb": snapshot.vms_mb,
                    "heap_mb": snapshot.heap_mb,
                }
            )

        # Calculate growth rate
        if len(snapshots) >= 2:
            time_diff = latest.timestamp - snapshots[0].timestamp
            if time_diff > 0:
                growth_mb = latest.rss_mb - snapshots[0].rss_mb
                growth_rate = (growth_mb / (time_diff / 60))  # MB per minute
                report["growth_rate_mb_per_min"] = growth_rate

        # GC stats
        for gen in range(3):
            gc_count = gc.get_count()[gen]
            report[f"gc_generation_{gen}_collections"] = gc_count

        return report

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts."""
        with self._alert_lock:
            return [
                {
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "metric_name": a.metric_name,
                    "current_value": a.current_value,
                    "threshold_value": a.threshold_value,
                    "message": a.message,
                    "timestamp": a.timestamp,
                    "context": a.context,
                }
                for a in self._active_alerts
            ]

    def get_full_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            "timestamp": time.time(),
            "latency": self.get_latency_report(),
            "queries": self.get_query_report(),
            "memory": self.get_memory_report(),
            "alerts": self.get_active_alerts(),
        }


# ========================================
# Decorators and Context Managers
# ========================================


@asynccontextmanager
async def track_request_latency(
    method: str,
    endpoint: str,
    request_id: Optional[str] = None,
    monitor: Optional[PerformanceMonitor] = None,
) -> AsyncGenerator[None, None]:
    """
    Context manager to track request latency.

    Usage:
        async with track_request_latency("GET", "/api/programs", request_id="123"):
            # ... request processing ...
    """
    if monitor is None:
        monitor = PerformanceMonitor()

    start_time = time.time()
    status_code = 200  # Default to success

    try:
        yield
    except Exception:
        status_code = 500
        raise
    finally:
        duration = time.time() - start_time
        monitor.record_latency(
            method=method,
            endpoint=endpoint,
            duration=duration,
            status_code=status_code,
            request_id=request_id,
        )


@contextmanager
def track_query_latency(
    operation: str,
    table: str,
    query_hash: str,
    request_id: Optional[str] = None,
    monitor: Optional[PerformanceMonitor] = None,
) -> Generator[None, None, None]:
    """
    Context manager to track query latency.

    Usage:
        with track_query_latency("SELECT", "programs", "hash123"):
            # ... execute query ...
    """
    if monitor is None:
        monitor = PerformanceMonitor()

    start_time = time.time()
    affected_rows = 0

    try:
        yield
    finally:
        duration = time.time() - start_time
        monitor.record_query(
            operation=operation,
            table=table,
            duration=duration,
            query_hash=query_hash,
            affected_rows=affected_rows,
            request_id=request_id,
        )


def track_performance(
    operation_name: str,
    monitor: Optional[PerformanceMonitor] = None,
):
    """
    Decorator to track function/async function performance.

    Args:
        operation_name: Name of the operation being tracked
        monitor: Optional performance monitor instance

    Usage:
        @track_performance("generate_program")
        async def generate_program(user_id: int):
            # ... function body ...
    """
    if monitor is None:
        monitor = PerformanceMonitor()

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                monitor.record_latency(
                    method="FUNCTION",
                    endpoint=operation_name,
                    duration=duration,
                    status_code=200,
                )

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                monitor.record_latency(
                    method="FUNCTION",
                    endpoint=operation_name,
                    duration=duration,
                    status_code=200,
                )

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ========================================
# Global Instance
# ========================================

_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


async def init_performance_monitor() -> None:
    """Initialize the global performance monitor."""
    monitor = get_performance_monitor()
    await monitor.start()


async def shutdown_performance_monitor() -> None:
    """Shutdown the global performance monitor."""
    global _global_monitor
    if _global_monitor:
        await _global_monitor.stop()
