"""Admin routes for viewing and managing audit logs."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, status, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.dependencies import get_current_user, require_admin, AdminResponse
from app.api.dependencies.audit import get_audit_service
from app.core.exceptions import NotFoundError, AuthorizationError
from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.enums import AuditActionType
from app.repositories.audit_log_repository import AuditLogRepository
from app.services.audit_service import AuditService
from app.schemas.pagination import PaginatedResult
from app.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/admin/audit", tags=["admin-audit"])


# Request/Response models

class AuditLogResponse(BaseModel):
    """Audit log entry response model."""

    id: int
    user_id: int | None
    action_type: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    user_agent: str | None
    details: dict | None
    timestamp: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Paginated audit log list response."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


class ActivitySummaryResponse(BaseModel):
    """Activity summary response."""

    action_counts: dict[str, int]
    total_events: int


class SecurityReportResponse(BaseModel):
    """Security report response."""

    failed_auth_attempts: int
    suspicious_activities: int
    unique_ips_with_failures: int
    high_risk_events: list[dict]


class AuditFilters(BaseModel):
    """Filters for audit log queries."""

    user_id: int | None = Field(None, description="Filter by user ID")
    action_type: str | None = Field(None, description="Filter by action type")
    resource_type: str | None = Field(None, description="Filter by resource type")
    resource_id: str | None = Field(None, description="Filter by resource ID")
    ip_address: str | None = Field(None, description="Filter by IP address")
    start_date: datetime | None = Field(None, description="Filter logs after this date")
    end_date: datetime | None = Field(None, description="Filter logs before this date")


# Routes

@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    user_id: int | None = Query(None, description="Filter by user ID"),
    action_type: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    ip_address: str | None = Query(None, description="Filter by IP address"),
    start_date: datetime | None = Query(None, description="Filter logs after this date"),
    end_date: datetime | None = Query(None, description="Filter logs before this date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs with optional filtering and pagination.

    Requires admin role to access.

    Args:
        user_id: Filter by user ID
        action_type: Filter by action type
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        ip_address: Filter by IP address
        start_date: Filter logs after this date
        end_date: Filter logs before this date
        page: Page number (1-indexed)
        page_size: Number of items per page
        current_user: Current authenticated user
        db: Database session

    Returns:
        Paginated list of audit logs

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

    # Build filters
    filters = {}
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
    from app.schemas.pagination import PaginationParams

    pagination = PaginationParams(
        page=page,
        page_size=page_size,
    )

    # Query logs
    result = await repository.list(filters=filters, pagination=pagination)

    # Log the admin action
    audit_service = AuditService(db)
    await audit_service.log_admin_action(
        admin_id=current_user.id,
        action="viewed_audit_logs",
        request=Request(scope={"type": "http"}),  # Create minimal request
        details={"filters": filters, "page": page, "page_size": page_size},
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific audit log entry by ID.

    Requires admin role to access.

    Args:
        log_id: Audit log ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Audit log entry

    Raises:
        HTTPException: If log not found or user is not an admin
    """
    # Check admin permission
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise AuthorizationError(
            "Admin access required",
            code="AUTH_ADMIN_REQUIRED",
            details={"user_id": current_user.id, "user_role": current_user.role}
        )

    repository = AuditLogRepository(db)
    audit_log = await repository.get_by_id(log_id)

    if not audit_log:
        raise NotFoundError("AuditLog", details={"log_id": log_id})

    return AuditLogResponse.model_validate(audit_log)


@router.get("/user/{user_id}/activity", response_model=AuditLogListResponse)
async def get_user_activity(
    user_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent audit activity for a specific user.

    Requires admin role to access.

    Args:
        user_id: User ID to get activity for
        days: Number of days to look back
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of audit logs for the user

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

    start_date = datetime.utcnow() - timedelta(days=days)
    logs = await repository.get_user_activity(
        user_id=user_id,
        start_date=start_date,
        limit=limit,
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs),
        page=1,
        page_size=len(logs),
    )


@router.get("/login-history", response_model=AuditLogListResponse)
async def get_login_history(
    user_id: int | None = Query(None, description="Filter by user ID"),
    ip_address: str | None = Query(None, description="Filter by IP address"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get login history (both successful and failed attempts).

    Requires admin role to access.

    Args:
        user_id: Filter by user ID
        ip_address: Filter by IP address
        days: Number of days to look back
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of login-related audit logs

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

    start_date = datetime.utcnow() - timedelta(days=days)
    logs = await repository.get_login_history(
        user_id=user_id,
        ip_address=ip_address,
        start_date=start_date,
        limit=limit,
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs),
        page=1,
        page_size=len(logs),
    )


@router.get("/failed-auth", response_model=AuditLogListResponse)
async def get_failed_auth_attempts(
    ip_address: str | None = Query(None, description="Filter by IP address"),
    user_id: int | None = Query(None, description="Filter by user ID"),
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get failed authentication attempts for security monitoring.

    Requires admin role to access.

    Args:
        ip_address: Filter by IP address
        user_id: Filter by user ID
        hours: Number of hours to look back
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of failed authentication audit logs

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

    since = datetime.utcnow() - timedelta(hours=hours)
    logs = await repository.get_failed_auth_attempts(
        ip_address=ip_address,
        user_id=user_id,
        since=since,
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs),
        page=1,
        page_size=len(logs),
    )


@router.get("/suspicious-activity", response_model=AuditLogListResponse)
async def get_suspicious_activity(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all suspicious activity logs.

    Requires admin role to access.

    Args:
        days: Number of days to look back
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of suspicious activity audit logs

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

    start_date = datetime.utcnow() - timedelta(days=days)
    logs = await repository.get_suspicious_activity(
        start_date=start_date,
        limit=limit,
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs),
        page=1,
        page_size=len(logs),
    )


@router.get("/admin-actions", response_model=AuditLogListResponse)
async def get_admin_actions(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all administrative action logs.

    Requires admin role to access.

    Args:
        days: Number of days to look back
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of admin action audit logs

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

    start_date = datetime.utcnow() - timedelta(days=days)
    logs = await repository.get_admin_actions(
        start_date=start_date,
        limit=limit,
    )

    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs),
        page=1,
        page_size=len(logs),
    )


@router.get("/summary", response_model=ActivitySummaryResponse)
async def get_activity_summary(
    user_id: int | None = Query(None, description="Filter by user ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a summary of audit activity grouped by action type.

    Requires admin role to access.

    Args:
        user_id: Filter by user ID
        days: Number of days to look back
        current_user: Current authenticated user
        db: Database session

    Returns:
        Activity summary with counts by action type

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

    start_date = datetime.utcnow() - timedelta(days=days)
    summary = await repository.get_activity_summary(
        user_id=user_id,
        start_date=start_date,
    )

    total_events = sum(summary.values())

    return ActivitySummaryResponse(
        action_counts=summary,
        total_events=total_events,
    )


@router.get("/security-report", response_model=SecurityReportResponse)
async def get_security_report(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a security report with high-risk events.

    Requires admin role to access.

    Args:
        hours: Number of hours to look back
        current_user: Current authenticated user
        db: Database session

    Returns:
        Security report with high-risk events

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
    since = datetime.utcnow() - timedelta(hours=hours)

    # Get failed auth attempts
    failed_auth = await repository.get_failed_auth_attempts(since=since)

    # Get suspicious activity
    suspicious = await repository.get_suspicious_activity(start_date=since)

    # Count unique IPs with failures
    unique_ips = set(log.ip_address for log in failed_auth if log.ip_address)

    # Get high-risk events
    high_risk_events = []
    for log in suspicious:
        if log.details and log.details.get("severity") in ("high", "critical"):
            high_risk_events.append(log.to_dict())

    return SecurityReportResponse(
        failed_auth_attempts=len(failed_auth),
        suspicious_activities=len(suspicious),
        unique_ips_with_failures=len(unique_ips),
        high_risk_events=high_risk_events,
    )


@router.delete("/cleanup", response_model=AdminResponse)
async def cleanup_old_logs(
    days_to_keep: int = Query(90, ge=30, le=365, description="Number of days to retain"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete audit logs older than the retention period.

    This endpoint should be called periodically (e.g., via cron job)
    to manage database size. Only super_admin can perform this action.

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

    repository = AuditLogRepository(db)

    deleted_count = await repository.delete_old_logs(days_to_keep=days_to_keep)

    # Log the cleanup action
    audit_service = AuditService(db)
    await audit_service.log_admin_action(
        admin_id=current_user.id,
        action="cleanup_old_audit_logs",
        request=Request(scope={"type": "http"}),  # Create minimal request
        details={
            "days_to_keep": days_to_keep,
            "deleted_count": deleted_count,
        },
    )

    return AdminResponse(
        success=True,
        message=f"Deleted {deleted_count} audit logs older than {days_to_keep} days",
    )


# Add action types list endpoint for reference
@router.get("/action-types", response_model=list[str])
async def get_action_types(
    current_user: User = Depends(get_current_user),
):
    """Get list of available audit action types.

    Args:
        current_user: Current authenticated user

    Returns:
        List of action type values

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

    return [action.value for action in AuditActionType]
