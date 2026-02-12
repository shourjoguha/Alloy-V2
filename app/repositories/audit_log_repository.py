"""Repository for AuditLog model with specialized query methods."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.enums import AuditActionType
from app.schemas.pagination import PaginationParams, PaginatedResult


class AuditLogRepository:
    """Repository for audit log operations with specialized security queries."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session

    async def create(self, audit_log: AuditLog) -> AuditLog:
        """Create a new audit log entry.

        Args:
            audit_log: AuditLog instance to persist

        Returns:
            Created audit log with generated ID
        """
        self._session.add(audit_log)
        await self._session.flush()
        await self._session.refresh(audit_log)
        return audit_log

    async def get_by_id(self, log_id: int) -> Optional[AuditLog]:
        """Retrieve audit log by ID.

        Args:
            log_id: Audit log ID

        Returns:
            AuditLog instance or None
        """
        result = await self._session.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        filters: Optional[dict] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> PaginatedResult[AuditLog]:
        """List audit logs with optional filtering and pagination.

        Args:
            filters: Dictionary of filter criteria:
                - user_id: Filter by user ID
                - action_type: Filter by action type
                - resource_type: Filter by resource type
                - resource_id: Filter by resource ID
                - ip_address: Filter by IP address
                - start_date: Filter logs after this datetime
                - end_date: Filter logs before this datetime
            pagination: Pagination parameters

        Returns:
            Paginated result with audit logs
        """
        query = select(AuditLog)

        if filters:
            if filters.get("user_id") is not None:
                query = query.where(AuditLog.user_id == filters["user_id"])
            if filters.get("action_type"):
                query = query.where(AuditLog.action_type == filters["action_type"])
            if filters.get("resource_type"):
                query = query.where(AuditLog.resource_type == filters["resource_type"])
            if filters.get("resource_id"):
                query = query.where(AuditLog.resource_id == filters["resource_id"])
            if filters.get("ip_address"):
                query = query.where(AuditLog.ip_address == filters["ip_address"])
            if filters.get("start_date"):
                query = query.where(AuditLog.timestamp >= filters["start_date"])
            if filters.get("end_date"):
                query = query.where(AuditLog.timestamp <= filters["end_date"])

        # Order by timestamp descending (newest first)
        query = query.order_by(desc(AuditLog.timestamp))

        # Apply pagination
        if pagination:
            total_query = select(func.count()).select_from(query.subquery())
            total_result = await self._session.execute(total_query)
            total = total_result.scalar()

            query = query.offset(pagination.offset).limit(pagination.limit)

            result = await self._session.execute(query)
            items = result.scalars().all()

            return PaginatedResult(
                items=items,
                total=total,
                page=pagination.page,
                page_size=pagination.limit,
            )

        result = await self._session.execute(query)
        items = result.scalars().all()

        return PaginatedResult(
            items=items,
            total=len(items),
            page=1,
            page_size=len(items),
        )

    async def get_user_activity(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get recent audit logs for a specific user.

        Args:
            user_id: User ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Maximum number of records to return

        Returns:
            List of audit logs for the user
        """
        query = select(AuditLog).where(AuditLog.user_id == user_id)

        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)

        query = query.order_by(desc(AuditLog.timestamp)).limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_failed_auth_attempts(
        self,
        ip_address: Optional[str] = None,
        user_id: Optional[int] = None,
        since: Optional[datetime] = None,
    ) -> List[AuditLog]:
        """Get failed authentication attempts for security monitoring.

        Args:
            ip_address: Optional IP address to filter by
            user_id: Optional user ID to filter by
            since: Only return attempts after this datetime

        Returns:
            List of failed authentication audit logs
        """
        query = select(AuditLog).where(
            AuditLog.action_type == AuditActionType.FAILED_AUTH.value
        )

        if ip_address:
            query = query.where(AuditLog.ip_address == ip_address)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if since:
            query = query.where(AuditLog.timestamp >= since)

        query = query.order_by(desc(AuditLog.timestamp))

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def count_failed_auth_attempts(
        self,
        ip_address: Optional[str] = None,
        user_id: Optional[int] = None,
        within_minutes: int = 15,
    ) -> int:
        """Count failed authentication attempts within a time window.

        Useful for rate limiting and brute force detection.

        Args:
            ip_address: Optional IP address to filter by
            user_id: Optional user ID to filter by
            within_minutes: Time window in minutes to count within

        Returns:
            Number of failed authentication attempts
        """
        since = datetime.utcnow() - timedelta(minutes=within_minutes)

        query = select(func.count()).select_from(
            select(AuditLog.id).where(
                and_(
                    AuditLog.action_type == AuditActionType.FAILED_AUTH.value,
                    AuditLog.timestamp >= since,
                )
            )
        )

        if ip_address:
            query = query.where(AuditLog.ip_address == ip_address)
        if user_id:
            query = query.where(AuditLog.user_id == user_id)

        result = await self._session.execute(query)
        return result.scalar() or 0

    async def get_suspicious_activity(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[AuditLog]:
        """Get all suspicious activity logs.

        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Maximum number of records to return

        Returns:
            List of suspicious activity audit logs
        """
        query = select(AuditLog).where(
            AuditLog.action_type == AuditActionType.SUSPICIOUS_ACTIVITY.value
        )

        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)

        query = query.order_by(desc(AuditLog.timestamp)).limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_admin_actions(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get all administrative action logs.

        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Maximum number of records to return

        Returns:
            List of admin action audit logs
        """
        query = select(AuditLog).where(
            AuditLog.action_type == AuditActionType.ADMIN_ACTION.value
        )

        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)

        query = query.order_by(desc(AuditLog.timestamp)).limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_login_history(
        self,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[AuditLog]:
        """Get login history (both successful and failed).

        Args:
            user_id: Optional user ID to filter by
            ip_address: Optional IP address to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Maximum number of records to return

        Returns:
            List of login-related audit logs
        """
        query = select(AuditLog).where(
            or_(
                AuditLog.action_type == AuditActionType.LOGIN.value,
                AuditLog.action_type == AuditActionType.FAILED_AUTH.value,
            )
        )

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if ip_address:
            query = query.where(AuditLog.ip_address == ip_address)
        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)

        query = query.order_by(desc(AuditLog.timestamp)).limit(limit)

        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def delete_old_logs(self, days_to_keep: int = 90) -> int:
        """Delete audit logs older than the specified retention period.

        This method should be used for periodic cleanup to manage database size.

        Args:
            days_to_keep: Number of days of logs to retain

        Returns:
            Number of audit logs deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        from sqlalchemy import delete

        delete_stmt = delete(AuditLog).where(
            AuditLog.timestamp < cutoff_date
        )

        result = await self._session.execute(delete_stmt)
        return result.rowcount

    async def get_activity_summary(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Get a summary of audit activity grouped by action type.

        Args:
            user_id: Optional user ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            Dictionary with action types as keys and counts as values
        """
        query = select(
            AuditLog.action_type,
            func.count(AuditLog.id).label("count")
        )

        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        if start_date:
            query = query.where(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.timestamp <= end_date)

        query = query.group_by(AuditLog.action_type)

        result = await self._session.execute(query)
        rows = result.all()

        return {action_type: count for action_type, count in rows}
