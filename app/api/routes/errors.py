"""Error aggregation dashboard routes for analyzing error data from audit logs."""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, status, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, case, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.api.routes.dependencies import get_current_user, require_admin, AdminResponse
from app.api.dependencies.audit import get_audit_service
from app.core.exceptions import NotFoundError, AuthorizationError
from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.models.enums import AuditActionType
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.audit_service import AuditService
from app.schemas.pagination import PaginatedResult, PaginationParams
from app.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/errors", tags=["Error Dashboard"])


# ============================================================================
# Error Schema Definitions
# ============================================================================

class ErrorSeverity(str):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorLogResponse(BaseModel):
    """Error log entry response model."""
    id: int
    user_id: int | None = None
    action_type: str
    resource_type: str | None = None
    resource_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict | None = None
    severity: str
    error_code: str | None = None
    error_message: str | None = None
    timestamp: datetime

    class Config:
        from_attributes = True


class ErrorSummaryResponse(BaseModel):
    """Overall error summary statistics."""
    total_errors: int
    unique_users_affected: int
    errors_by_severity: dict[str, int]
    errors_by_type: dict[str, int]
    errors_by_resource_type: dict[str, int]
    period_start: datetime
    period_end: datetime
    average_errors_per_hour: float


class ErrorTrendDataPoint(BaseModel):
    """Single data point in an error trend."""
    timestamp: datetime | str
    count: int
    severity_breakdown: dict[str, int]


class ErrorTrendResponse(BaseModel):
    """Error trends over time."""
    interval: str
    data_points: list[ErrorTrendDataPoint]
    total_errors: int
    trend_percentage: float  # Percentage change from previous period
    peak_error_time: datetime | None = None
    peak_error_count: int = 0


class ErrorDistributionBucket(BaseModel):
    """A bucket in error distribution."""
    category: str
    count: int
    percentage: float


class ErrorDistributionResponse(BaseModel):
    """Error distribution across different dimensions."""
    by_severity: list[ErrorDistributionBucket]
    by_action_type: list[ErrorDistributionBucket]
    by_resource_type: list[ErrorDistributionBucket]
    by_hour_of_day: list[ErrorDistributionBucket]
    by_day_of_week: list[ErrorDistributionBucket]


class TopErrorResponse(BaseModel):
    """Most frequent error response."""
    error_type: str
    error_message: str | None = None
    count: int
    percentage: float
    first_occurrence: datetime | None = None
    last_occurrence: datetime | None = None
    affected_users: int


class UserErrorSummaryResponse(BaseModel):
    """Error summary for a specific user."""
    user_id: int
    total_errors: int
    errors_by_type: dict[str, int]
    errors_by_severity: dict[str, int]
    first_error: datetime | None = None
    last_error: datetime | None = None
    most_common_error: str | None = None


class ErrorFilterParams(BaseModel):
    """Parameters for filtering error logs."""
    user_id: int | None = Field(None, description="Filter by user ID")
    action_type: str | None = Field(None, description="Filter by action type")
    resource_type: str | None = Field(None, description="Filter by resource type")
    resource_id: str | None = Field(None, description="Filter by resource ID")
    ip_address: str | None = Field(None, description="Filter by IP address")
    severity: str | None = Field(None, description="Filter by severity level")
    start_date: datetime | None = Field(None, description="Filter errors after this date")
    end_date: datetime | None = Field(None, description="Filter errors before this date")
    error_code: str | None = Field(None, description="Filter by error code")


class ErrorResponseList(BaseModel):
    """Paginated error log list response."""
    items: list[ErrorLogResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class ErrorInsightsResponse(BaseModel):
    """Insights and recommendations based on error data."""
    summary: ErrorSummaryResponse
    top_errors: list[TopErrorResponse]
    trends: ErrorTrendResponse
    distribution: ErrorDistributionResponse
    recommendations: list[str]
    critical_issues: list[dict]


# ============================================================================
# Error Classification Helper Functions
# ============================================================================

def classify_error_severity(action_type: str, details: dict | None = None) -> str:
    """Classify error severity based on action type and details.

    Args:
        action_type: The audit action type
        details: Additional error details

    Returns:
        Severity level (low, medium, high, critical)
    """
    critical_actions = {
        AuditActionType.FAILED_AUTH.value,
        AuditActionType.SUSPICIOUS_ACTIVITY.value,
        AuditActionType.PERMISSION_DENIED.value,
    }

    high_actions = {
        AuditActionType.ACCOUNT_DELETION.value,
    }

    medium_actions = {
        AuditActionType.PASSWORD_RESET_REQUEST.value,
        AuditActionType.ROLE_CHANGE.value,
    }

    if action_type in critical_actions:
        return "critical"
    elif action_type in high_actions:
        return "high"
    elif action_type in medium_actions:
        return "medium"

    # Check details for severity indicator
    if details:
        severity = details.get("severity")
        if severity in ("critical", "high", "medium", "low"):
            return severity
        if details.get("http_status_code", 0) >= 500:
            return "critical"
        elif details.get("http_status_code", 0) >= 400:
            return "high"

    return "low"


def extract_error_code(details: dict | None = None) -> str | None:
    """Extract error code from details."""
    if not details:
        return None
    return details.get("error_code") or details.get("code")


def extract_error_message(details: dict | None = None) -> str | None:
    """Extract error message from details."""
    if not details:
        return None
    return details.get("error_message") or details.get("message")


# ============================================================================
# Error Aggregation Repository Methods
# ============================================================================

class ErrorAggregationRepository:
    """Repository for error aggregation queries."""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _get_error_action_types(self) -> list[str]:
        """Get list of action types that represent errors."""
        return [
            AuditActionType.FAILED_AUTH.value,
            AuditActionType.PERMISSION_DENIED.value,
            AuditActionType.SUSPICIOUS_ACTIVITY.value,
            AuditActionType.ACCOUNT_DELETION.value,
            AuditActionType.PASSWORD_RESET_REQUEST.value,
        ]

    async def get_error_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: int | None = None,
    ) -> dict:
        """Get overall error summary for the specified period.

        Args:
            start_date: Start of period
            end_date: End of period
            user_id: Optional user filter

        Returns:
            Dictionary with error summary statistics
        """
        error_types = self._get_error_action_types()

        # Build base query
        query = select(AuditLog).where(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.action_type.in_(error_types),
            )
        )

        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)

        # Get all error logs for the period
        result = await self._session.execute(query)
        errors = result.scalars().all()

        if not errors:
            return {
                "total_errors": 0,
                "unique_users_affected": 0,
                "errors_by_severity": {},
                "errors_by_type": {},
                "errors_by_resource_type": {},
                "period_start": start_date,
                "period_end": end_date,
                "average_errors_per_hour": 0.0,
            }

        # Calculate statistics
        total_errors = len(errors)
        unique_users = len(set(e.user_id for e in errors if e.user_id))

        errors_by_severity = {}
        errors_by_type = {}
        errors_by_resource_type = {}

        for error in errors:
            # Classify severity
            severity = classify_error_severity(error.action_type, error.details)
            errors_by_severity[severity] = errors_by_severity.get(severity, 0) + 1

            # Count by type
            errors_by_type[error.action_type] = errors_by_type.get(error.action_type, 0) + 1

            # Count by resource type
            if error.resource_type:
                errors_by_resource_type[error.resource_type] = errors_by_resource_type.get(
                    error.resource_type, 0
                ) + 1

        # Calculate average errors per hour
        period_hours = (end_date - start_date).total_seconds() / 3600
        avg_per_hour = total_errors / period_hours if period_hours > 0 else 0.0

        return {
            "total_errors": total_errors,
            "unique_users_affected": unique_users,
            "errors_by_severity": errors_by_severity,
            "errors_by_type": errors_by_type,
            "errors_by_resource_type": errors_by_resource_type,
            "period_start": start_date,
            "period_end": end_date,
            "average_errors_per_hour": round(avg_per_hour, 2),
        }

    async def get_error_trends(
        self,
        start_date: datetime,
        end_date: datetime,
        interval: str = "hour",
        user_id: int | None = None,
    ) -> dict:
        """Get error trends over time.

        Args:
            start_date: Start of period
            end_date: End of period
            interval: Time interval (hour, day, week)
            user_id: Optional user filter

        Returns:
            Dictionary with trend data
        """
        error_types = self._get_error_action_types()

        # Determine date truncation function based on interval
        if interval == "hour":
            trunc_func = func.date_trunc("hour", AuditLog.timestamp)
        elif interval == "day":
            trunc_func = func.date_trunc("day", AuditLog.timestamp)
        elif interval == "week":
            trunc_func = func.date_trunc("week", AuditLog.timestamp)
        else:
            trunc_func = func.date_trunc("hour", AuditLog.timestamp)

        # Build query for grouped counts
        query = select(
            trunc_func.label("time_bucket"),
            func.count(AuditLog.id).label("count"),
        ).where(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.action_type.in_(error_types),
            )
        )

        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)

        query = query.group_by("time_bucket").order_by("time_bucket")

        result = await self._session.execute(query)
        rows = result.all()

        # Build data points
        data_points = []
        total_errors = 0
        peak_count = 0
        peak_time = None

        for row in rows:
            count = row.count
            total_errors += count

            if count > peak_count:
                peak_count = count
                peak_time = row.time_bucket

            # Get severity breakdown for this bucket
            severity_query = select(
                AuditLog.action_type,
                func.count(AuditLog.id).label("count"),
            ).where(
                and_(
                    AuditLog.timestamp >= row.time_bucket,
                    AuditLog.timestamp < row.time_bucket + timedelta(hours=1)
                    if interval == "hour"
                    else AuditLog.timestamp < row.time_bucket + timedelta(days=1),
                    AuditLog.action_type.in_(error_types),
                )
            )

            if user_id is not None:
                severity_query = severity_query.where(AuditLog.user_id == user_id)

            severity_query = severity_query.group_by(AuditLog.action_type)
            severity_result = await self._session.execute(severity_query)

            severity_breakdown = {}
            for s_row in severity_result:
                severity = classify_error_severity(s_row.action_type)
                severity_breakdown[severity] = severity_breakdown.get(severity, 0) + s_row.count

            data_points.append(
                ErrorTrendDataPoint(
                    timestamp=row.time_bucket.isoformat() if row.time_bucket else "",
                    count=count,
                    severity_breakdown=severity_breakdown,
                )
            )

        # Calculate trend percentage (compare first half to second half)
        trend_percentage = 0.0
        if len(data_points) >= 2:
            mid_point = len(data_points) // 2
            first_half_sum = sum(dp.count for dp in data_points[:mid_point])
            second_half_sum = sum(dp.count for dp in data_points[mid_point:])
            if first_half_sum > 0:
                trend_percentage = ((second_half_sum - first_half_sum) / first_half_sum) * 100

        return {
            "interval": interval,
            "data_points": data_points,
            "total_errors": total_errors,
            "trend_percentage": round(trend_percentage, 2),
            "peak_error_time": peak_time,
            "peak_error_count": peak_count,
        }

    async def get_error_distribution(
        self,
        start_date: datetime,
        end_date: datetime,
        user_id: int | None = None,
    ) -> dict:
        """Get error distribution across various dimensions.

        Args:
            start_date: Start of period
            end_date: End of period
            user_id: Optional user filter

        Returns:
            Dictionary with distribution data
        """
        error_types = self._get_error_action_types()

        # Get all errors for the period
        query = select(AuditLog).where(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.action_type.in_(error_types),
            )
        )

        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)

        result = await self._session.execute(query)
        errors = result.scalars().all()

        if not errors:
            return {
                "by_severity": [],
                "by_action_type": [],
                "by_resource_type": [],
                "by_hour_of_day": [],
                "by_day_of_week": [],
            }

        total = len(errors)

        # Distribution by severity
        severity_dist = {}
        action_type_dist = {}
        resource_type_dist = {}
        hour_dist = {}
        day_dist = {}

        for error in errors:
            # Severity distribution
            severity = classify_error_severity(error.action_type, error.details)
            severity_dist[severity] = severity_dist.get(severity, 0) + 1

            # Action type distribution
            action_type_dist[error.action_type] = action_type_dist.get(error.action_type, 0) + 1

            # Resource type distribution
            if error.resource_type:
                resource_type_dist[error.resource_type] = resource_type_dist.get(
                    error.resource_type, 0
                ) + 1

            # Hour of day distribution
            hour = error.timestamp.hour if error.timestamp else 0
            hour_dist[hour] = hour_dist.get(hour, 0) + 1

            # Day of week distribution
            day = error.timestamp.strftime("%A") if error.timestamp else "Unknown"
            day_dist[day] = day_dist.get(day, 0) + 1

        def create_buckets(dist: dict) -> list[ErrorDistributionBucket]:
            """Create distribution buckets with percentages."""
            return sorted(
                [
                    ErrorDistributionBucket(
                        category=k,
                        count=v,
                        percentage=round((v / total) * 100, 2),
                    )
                    for k, v in dist.items()
                ],
                key=lambda x: x.count,
                reverse=True,
            )

        return {
            "by_severity": create_buckets(severity_dist),
            "by_action_type": create_buckets(action_type_dist),
            "by_resource_type": create_buckets(resource_type_dist),
            "by_hour_of_day": create_buckets(hour_dist),
            "by_day_of_week": create_buckets(day_dist),
        }

    async def get_top_errors(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 10,
        user_id: int | None = None,
    ) -> list[dict]:
        """Get most frequent errors.

        Args:
            start_date: Start of period
            end_date: End of period
            limit: Maximum number of errors to return
            user_id: Optional user filter

        Returns:
            List of top errors
        """
        error_types = self._get_error_action_types()

        # Group by action type and count
        query = select(
            AuditLog.action_type,
            func.count(AuditLog.id).label("count"),
            func.min(AuditLog.timestamp).label("first_occurrence"),
            func.max(AuditLog.timestamp).label("last_occurrence"),
            func.count(func.distinct(AuditLog.user_id)).label("affected_users"),
        ).where(
            and_(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.action_type.in_(error_types),
            )
        )

        if user_id is not None:
            query = query.where(AuditLog.user_id == user_id)

        query = query.group_by(AuditLog.action_type).order_by(
            func.count(AuditLog.id).desc()
        ).limit(limit)

        result = await self._session.execute(query)
        rows = result.all()

        # Get total count for percentage calculation
        total_query = select(func.count()).select_from(
            select(AuditLog.id).where(
                and_(
                    AuditLog.timestamp >= start_date,
                    AuditLog.timestamp <= end_date,
                    AuditLog.action_type.in_(error_types),
                )
            )
        )

        if user_id is not None:
            total_query = total_query.where(AuditLog.user_id == user_id)

        total_result = await self._session.execute(total_query)
        total = total_result.scalar() or 0

        top_errors = []
        for row in rows:
            # Get sample error message
            sample_query = (
                select(AuditLog)
                .where(AuditLog.action_type == row.action_type)
                .limit(1)
            )

            if user_id is not None:
                sample_query = sample_query.where(AuditLog.user_id == user_id)

            sample_result = await self._session.execute(sample_query)
            sample_error = sample_result.scalar_one_or_none()

            error_message = None
            if sample_error and sample_error.details:
                error_message = extract_error_message(sample_error.details)

            top_errors.append(
                {
                    "error_type": row.action_type,
                    "error_message": error_message,
                    "count": row.count,
                    "percentage": round((row.count / total) * 100, 2) if total > 0 else 0,
                    "first_occurrence": row.first_occurrence,
                    "last_occurrence": row.last_occurrence,
                    "affected_users": row.affected_users,
                }
            )

        return top_errors

    async def get_user_error_summary(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> dict | None:
        """Get error summary for a specific user.

        Args:
            user_id: User ID
            start_date: Start of period
            end_date: End of period

        Returns:
            User error summary or None if no errors
        """
        error_types = self._get_error_action_types()

        query = select(AuditLog).where(
            and_(
                AuditLog.user_id == user_id,
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date,
                AuditLog.action_type.in_(error_types),
            )
        ).order_by(AuditLog.timestamp.desc())

        result = await self._session.execute(query)
        errors = result.scalars().all()

        if not errors:
            return None

        errors_by_type = {}
        errors_by_severity = {}
        first_error = None
        last_error = errors[0].timestamp

        for error in errors:
            errors_by_type[error.action_type] = errors_by_type.get(error.action_type, 0) + 1

            severity = classify_error_severity(error.action_type, error.details)
            errors_by_severity[severity] = errors_by_severity.get(severity, 0) + 1

            if first_error is None or error.timestamp < first_error:
                first_error = error.timestamp

        # Find most common error
        most_common_error = max(errors_by_type, key=errors_by_type.get) if errors_by_type else None

        return {
            "user_id": user_id,
            "total_errors": len(errors),
            "errors_by_type": errors_by_type,
            "errors_by_severity": errors_by_severity,
            "first_error": first_error,
            "last_error": last_error,
            "most_common_error": most_common_error,
        }


# ============================================================================
# API Routes
# ============================================================================

@router.get("/list", response_model=ErrorResponseList)
async def list_errors(
    user_id: int | None = Query(None, description="Filter by user ID"),
    action_type: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    ip_address: str | None = Query(None, description="Filter by IP address"),
    severity: str | None = Query(None, description="Filter by severity level"),
    start_date: datetime | None = Query(None, description="Filter errors after this date"),
    end_date: datetime | None = Query(None, description="Filter errors before this date"),
    error_code: str | None = Query(None, description="Filter by error code"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List error logs with optional filtering and pagination.

    Requires admin role to access.

    Args:
        user_id: Filter by user ID
        action_type: Filter by action type
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        ip_address: Filter by IP address
        severity: Filter by severity level
        start_date: Filter errors after this date
        end_date: Filter errors before this date
        error_code: Filter by error code
        page: Page number (1-indexed)
        page_size: Number of items per page
        current_user: Current authenticated user
        db: Database session

    Returns:
        Paginated list of error logs

    Raises:
        HTTPException: If user is not an admin
    """
    # Check admin permission
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise AuthorizationError(
            "Admin access required",
            code="AUTH_ADMIN_REQUIRED",
            details={"user_id": current_user.id, "user_role": current_user.role}
        )

    repository = AuditLogRepository(db)

    # Build filters - only include error-related action types
    error_types = [
        AuditActionType.FAILED_AUTH.value,
        AuditActionType.PERMISSION_DENIED.value,
        AuditActionType.SUSPICIOUS_ACTIVITY.value,
        AuditActionType.ACCOUNT_DELETION.value,
        AuditActionType.PASSWORD_RESET_REQUEST.value,
    ]

    filters = {"action_type_list": error_types}

    if user_id is not None:
        filters["user_id"] = user_id
    if action_type:
        filters["action_type"] = action_type
    if resource_type:
        filters["resource_type"] = resource_type
    if resource_id:
        filters["resource_id"] = resource_id
    if ip_address:
        filters["ip_address"] = ip_address
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date

    # Create pagination params
    pagination = PaginationParams(
        page=page,
        page_size=page_size,
    )

    # Query logs
    result = await repository.list(filters=filters, pagination=pagination)

    # Filter by severity and error code (need post-processing)
    filtered_items = []
    for log in result.items:
        # Classify severity
        log_severity = classify_error_severity(log.action_type, log.details)

        # Check severity filter
        if severity and log_severity != severity:
            continue

        # Check error code filter
        log_error_code = extract_error_code(log.details)
        if error_code and log_error_code != error_code:
            continue

        # Create error response
        error_response = ErrorLogResponse(
            id=log.id,
            user_id=log.user_id,
            action_type=log.action_type,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            details=log.details,
            severity=log_severity,
            error_code=log_error_code,
            error_message=extract_error_message(log.details),
            timestamp=log.timestamp,
        )
        filtered_items.append(error_response)

    # Log the admin action
    audit_service = AuditService(db)
    await audit_service.log_admin_action(
        admin_id=current_user.id,
        action="viewed_error_logs",
        request=Request(scope={"type": "http"}),
        details={"filters": filters, "page": page, "page_size": page_size},
    )

    return ErrorResponseList(
        items=filtered_items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        has_next=result.page * result.page_size < result.total,
        has_prev=result.page > 1,
    )


@router.get("/summary", response_model=ErrorSummaryResponse)
async def get_error_summary(
    hours: int = Query(24, ge=1, le=720, description="Number of hours to look back"),
    user_id: int | None = Query(None, description="Filter by user ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get error summary statistics for the specified time period.

    Requires admin role to access.

    Args:
        hours: Number of hours to look back (1-720 hours)
        user_id: Optional user filter
        current_user: Current authenticated user
        db: Database session

    Returns:
        Error summary statistics

    Raises:
        HTTPException: If user is not an admin
    """
    # Check admin permission
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise AuthorizationError(
            "Admin access required",
            code="AUTH_ADMIN_REQUIRED",
            details={"user_id": current_user.id, "user_role": current_user.role}
        )

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)

    error_repo = ErrorAggregationRepository(db)
    summary = await error_repo.get_error_summary(start_date, end_date, user_id)

    return ErrorSummaryResponse(**summary)


@router.get("/trends", response_model=ErrorTrendResponse)
async def get_error_trends(
    hours: int = Query(24, ge=1, le=720, description="Number of hours to look back"),
    interval: str = Query("hour", regex="^(hour|day|week)$", description="Time interval"),
    user_id: int | None = Query(None, description="Filter by user ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get error trends over time.

    Requires admin role to access.

    Args:
        hours: Number of hours to look back
        interval: Time interval (hour, day, week)
        user_id: Optional user filter
        current_user: Current authenticated user
        db: Database session

    Returns:
        Error trend data

    Raises:
        HTTPException: If user is not an admin
    """
    # Check admin permission
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise AuthorizationError(
            "Admin access required",
            code="AUTH_ADMIN_REQUIRED",
            details={"user_id": current_user.id, "user_role": current_user.role}
        )

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)

    error_repo = ErrorAggregationRepository(db)
    trends = await error_repo.get_error_trends(start_date, end_date, interval, user_id)

    return ErrorTrendResponse(**trends)


@router.get("/distribution", response_model=ErrorDistributionResponse)
async def get_error_distribution(
    hours: int = Query(24, ge=1, le=720, description="Number of hours to look back"),
    user_id: int | None = Query(None, description="Filter by user ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get error distribution across various dimensions.

    Requires admin role to access.

    Args:
        hours: Number of hours to look back
        user_id: Optional user filter
        current_user: Current authenticated user
        db: Database session

    Returns:
        Error distribution data

    Raises:
        HTTPException: If user is not an admin
    """
    # Check admin permission
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise AuthorizationError(
            "Admin access required",
            code="AUTH_ADMIN_REQUIRED",
            details={"user_id": current_user.id, "user_role": current_user.role}
        )

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)

    error_repo = ErrorAggregationRepository(db)
    distribution = await error_repo.get_error_distribution(start_date, end_date, user_id)

    return ErrorDistributionResponse(**distribution)


@router.get("/top", response_model=list[TopErrorResponse])
async def get_top_errors(
    hours: int = Query(24, ge=1, le=720, description="Number of hours to look back"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of errors to return"),
    user_id: int | None = Query(None, description="Filter by user ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get most frequent errors.

    Requires admin role to access.

    Args:
        hours: Number of hours to look back
        limit: Maximum number of errors to return
        user_id: Optional user filter
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of top errors

    Raises:
        HTTPException: If user is not an admin
    """
    # Check admin permission
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise AuthorizationError(
            "Admin access required",
            code="AUTH_ADMIN_REQUIRED",
            details={"user_id": current_user.id, "user_role": current_user.role}
        )

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)

    error_repo = ErrorAggregationRepository(db)
    top_errors = await error_repo.get_top_errors(start_date, end_date, limit, user_id)

    return [TopErrorResponse(**error) for error in top_errors]


@router.get("/user/{user_id}", response_model=UserErrorSummaryResponse)
async def get_user_error_summary(
    user_id: int,
    hours: int = Query(24, ge=1, le=720, description="Number of hours to look back"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get error summary for a specific user.

    Requires admin role to access.

    Args:
        user_id: User ID to get error summary for
        hours: Number of hours to look back
        current_user: Current authenticated user
        db: Database session

    Returns:
        User error summary

    Raises:
        HTTPException: If user is not an admin or user not found
    """
    # Check admin permission
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise AuthorizationError(
            "Admin access required",
            code="AUTH_ADMIN_REQUIRED",
            details={"user_id": current_user.id, "user_role": current_user.role}
        )

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)

    error_repo = ErrorAggregationRepository(db)
    summary = await error_repo.get_user_error_summary(user_id, start_date, end_date)

    if not summary:
        raise NotFoundError("UserErrorSummary", details={"user_id": user_id, "hours": hours})

    return UserErrorSummaryResponse(**summary)


@router.get("/insights", response_model=ErrorInsightsResponse)
async def get_error_insights(
    hours: int = Query(24, ge=1, le=720, description="Number of hours to look back"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive error insights including summary, trends, and recommendations.

    Requires admin role to access.

    Args:
        hours: Number of hours to look back
        current_user: Current authenticated user
        db: Database session

    Returns:
        Comprehensive error insights

    Raises:
        HTTPException: If user is not an admin
    """
    # Check admin permission
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise AuthorizationError(
            "Admin access required",
            code="AUTH_ADMIN_REQUIRED",
            details={"user_id": current_user.id, "user_role": current_user.role}
        )

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(hours=hours)

    error_repo = ErrorAggregationRepository(db)

    # Get all data
    summary_data = await error_repo.get_error_summary(start_date, end_date)
    trends_data = await error_repo.get_error_trends(start_date, end_date, "hour")
    distribution_data = await error_repo.get_error_distribution(start_date, end_date)
    top_errors_data = await error_repo.get_top_errors(start_date, end_date, 10)

    # Generate recommendations
    recommendations = []
    critical_issues = []

    # Check for high error rate
    if summary_data["average_errors_per_hour"] > 10:
        recommendations.append(
            "High error rate detected. Consider reviewing system stability "
            f"({summary_data['average_errors_per_hour']:.2f} errors/hour)"
        )

    # Check for critical errors
    critical_count = summary_data["errors_by_severity"].get("critical", 0)
    if critical_count > 0:
        recommendations.append(
            f"{critical_count} critical errors detected. Immediate attention required."
        )
        for error in top_errors_data[:3]:
            error_repo_error = AuditLogRepository(db)
            error_log_query = select(AuditLog).where(
                AuditLog.action_type == error["error_type"]
            ).limit(1)
            error_log_result = await db.execute(error_log_query)
            error_log = error_log_result.scalar_one_or_none()
            if error_log and classify_error_severity(error_log.action_type, error_log.details) == "critical":
                critical_issues.append({
                    "error_type": error["error_type"],
                    "count": error["count"],
                    "affected_users": error["affected_users"],
                })

    # Check for suspicious activity
    suspicious_count = summary_data["errors_by_type"].get("suspicious_activity", 0)
    if suspicious_count > 0:
        recommendations.append(
            f"{suspicious_count} suspicious activity events detected. Review security logs."
        )

    # Check for failed authentication spikes
    failed_auth_count = summary_data["errors_by_type"].get("failed_auth", 0)
    if failed_auth_count > 50:
        recommendations.append(
            f"High number of failed authentication attempts ({failed_auth_count}). "
            "Check for potential brute force attacks."
        )

    # Trend-based recommendations
    if trends_data["trend_percentage"] > 50:
        recommendations.append(
            f"Error rate increasing by {trends_data['trend_percentage']:.1f}%. "
            "Investigate recent deployments or system changes."
        )
    elif trends_data["trend_percentage"] < -50:
        recommendations.append(
            f"Error rate decreasing by {abs(trends_data['trend_percentage']):.1f}%. "
            "Recent improvements appear effective."
        )

    # Peak time recommendations
    if trends_data["peak_error_time"]:
        peak_hour = trends_data["peak_error_time"].hour if hasattr(trends_data["peak_error_time"], "hour") else 0
        if 9 <= peak_hour <= 17:
            recommendations.append(
                f"Peak errors occur during business hours ({peak_hour}:00). "
                "Consider scaling resources during peak times."
            )

    # Resource-specific recommendations
    resource_errors = summary_data["errors_by_resource_type"]
    if resource_errors:
        top_resource = max(resource_errors, key=resource_errors.get)
        recommendations.append(
            f"Most errors related to '{top_resource}' resource. "
            f"Review {top_resource} functionality and dependencies."
        )

    return ErrorInsightsResponse(
        summary=ErrorSummaryResponse(**summary_data),
        trends=ErrorTrendResponse(**trends_data),
        distribution=ErrorDistributionResponse(**distribution_data),
        top_errors=[TopErrorResponse(**error) for error in top_errors_data],
        recommendations=recommendations,
        critical_issues=critical_issues,
    )


@router.delete("/cleanup", response_model=AdminResponse)
async def cleanup_old_errors(
    days_to_keep: int = Query(30, ge=7, le=365, description="Number of days to retain"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete error logs older than the retention period.

    Only super_admin can perform this action.

    Args:
        days_to_keep: Number of days of logs to retain
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success message with count of deleted logs

    Raises:
        HTTPException: If user is not a super admin
    """
    # Check super admin permission
    if current_user.role != UserRole.SUPER_ADMIN:
        raise AuthorizationError(
            "Super admin access required",
            code="AUTH_SUPER_ADMIN_REQUIRED",
            details={"user_id": current_user.id, "user_role": current_user.role}
        )

    error_types = [
        AuditActionType.FAILED_AUTH.value,
        AuditActionType.PERMISSION_DENIED.value,
        AuditActionType.SUSPICIOUS_ACTIVITY.value,
        AuditActionType.ACCOUNT_DELETION.value,
        AuditActionType.PASSWORD_RESET_REQUEST.value,
    ]

    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

    from sqlalchemy import delete

    delete_stmt = delete(AuditLog).where(
        and_(
            AuditLog.timestamp < cutoff_date,
            AuditLog.action_type.in_(error_types),
        )
    )

    result = await db.execute(delete_stmt)
    deleted_count = result.rowcount
    await db.commit()

    # Log the cleanup action
    audit_service = AuditService(db)
    await audit_service.log_admin_action(
        admin_id=current_user.id,
        action="cleanup_old_error_logs",
        request=Request(scope={"type": "http"}),
        details={
            "days_to_keep": days_to_keep,
            "deleted_count": deleted_count,
        },
    )

    return AdminResponse(
        success=True,
        message=f"Deleted {deleted_count} error logs older than {days_to_keep} days",
    )
