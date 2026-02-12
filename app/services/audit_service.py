"""Service for managing security audit logging."""
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.enums import AuditActionType, UserRole
from app.repositories.audit_log_repository import AuditLogRepository
from app.core.logging import get_logger


logger = get_logger(__name__)


class AuditService:
    """Service for logging and managing security audit events.

    This service provides a high-level interface for logging various
    security-related events such as authentication, authorization,
    and administrative actions.
    """

    def __init__(self, session: AsyncSession):
        """Initialize audit service with database session.

        Args:
            session: Async SQLAlchemy session
        """
        self._session = session
        self._repository = AuditLogRepository(session)

    async def log_event(
        self,
        action_type: AuditActionType | str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a generic audit event.

        Args:
            action_type: Type of action performed
            user_id: ID of the user who performed the action
            resource_type: Type of resource affected
            resource_id: ID of the affected resource
            ip_address: IP address of the client
            user_agent: User-Agent header value
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        audit_log = AuditLog.create_entry(
            action_type=action_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )

        created_log = await self._repository.create(audit_log)

        # Log to application logger for immediate visibility
        logger.info(
            "audit_log_created",
            action_type=action_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            audit_log_id=created_log.id,
        )

        return created_log

    async def log_from_request(
        self,
        action_type: AuditActionType | str,
        request: Request,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log an audit event using data from a FastAPI request.

        This convenience method extracts IP address and user agent from
        the request object automatically.

        Args:
            action_type: Type of action performed
            request: FastAPI Request object
            user_id: ID of the user who performed the action
            resource_type: Type of resource affected
            resource_id: ID of the affected resource
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        # Extract client IP address
        ip_address = self._get_client_ip(request)

        # Extract user agent
        user_agent = request.headers.get("user-agent")

        return await self.log_event(
            action_type=action_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request headers.

        Handles proxy scenarios by checking for forwarded headers.

        Args:
            request: FastAPI Request object

        Returns:
            Client IP address or None
        """
        # Check for forwarded IP (behind proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # x-forwarded-for can contain multiple IPs, use the first one
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        return request.client.host if request.client else None

    # Authentication events

    async def log_login(
        self,
        user_id: int,
        request: Request,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a successful user login.

        Args:
            user_id: ID of the user who logged in
            request: FastAPI Request object
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        return await self.log_from_request(
            action_type=AuditActionType.LOGIN,
            request=request,
            user_id=user_id,
            resource_type="user",
            resource_id=str(user_id),
            details=details,
        )

    async def log_logout(
        self,
        user_id: int,
        request: Request,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a user logout.

        Args:
            user_id: ID of the user who logged out
            request: FastAPI Request object
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        return await self.log_from_request(
            action_type=AuditActionType.LOGOUT,
            request=request,
            user_id=user_id,
            resource_type="user",
            resource_id=str(user_id),
            details=details,
        )

    async def log_failed_auth(
        self,
        email: Optional[str] = None,
        user_id: Optional[int] = None,
        request: Optional[Request] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> AuditLog:
        """Log a failed authentication attempt.

        Args:
            email: Email address used for login attempt
            user_id: User ID if the user was identified
            request: FastAPI Request object (optional)
            ip_address: IP address if request not provided
            user_agent: User agent if request not provided
            reason: Reason for failure

        Returns:
            Created audit log entry
        """
        details: Dict[str, Any] = {}
        if email:
            details["email"] = email
        if reason:
            details["failure_reason"] = reason

        if request:
            return await self.log_from_request(
                action_type=AuditActionType.FAILED_AUTH,
                request=request,
                user_id=user_id,
                resource_type="auth",
                details=details,
            )

        return await self.log_event(
            action_type=AuditActionType.FAILED_AUTH,
            user_id=user_id,
            resource_type="auth",
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )

    async def log_token_refresh(
        self,
        user_id: int,
        request: Request,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a token refresh event.

        Args:
            user_id: ID of the user refreshing token
            request: FastAPI Request object
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        return await self.log_from_request(
            action_type=AuditActionType.TOKEN_REFRESH,
            request=request,
            user_id=user_id,
            resource_type="token",
            details=details,
        )

    async def log_session_termination(
        self,
        user_id: int,
        request: Request,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a session termination event.

        Args:
            user_id: ID of the user whose session was terminated
            request: FastAPI Request object
            reason: Reason for termination
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        if reason:
            details["termination_reason"] = reason

        return await self.log_from_request(
            action_type=AuditActionType.SESSION_TERMINATION,
            request=request,
            user_id=user_id,
            resource_type="session",
            details=details,
        )

    # Password events

    async def log_password_change(
        self,
        user_id: int,
        request: Request,
        changed_by: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a password change event.

        Args:
            user_id: ID of the user whose password was changed
            request: FastAPI Request object
            changed_by: ID of the user who changed the password (if different)
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        if changed_by and changed_by != user_id:
            details["changed_by"] = changed_by
            details["admin_initiated"] = True

        return await self.log_from_request(
            action_type=AuditActionType.PASSWORD_CHANGE,
            request=request,
            user_id=user_id,
            resource_type="user",
            resource_id=str(user_id),
            details=details,
        )

    async def log_password_reset_request(
        self,
        email: str,
        request: Request,
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a password reset request.

        Args:
            email: Email address for reset request
            request: FastAPI Request object
            user_id: User ID if identified
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        details["email"] = email

        return await self.log_from_request(
            action_type=AuditActionType.PASSWORD_RESET_REQUEST,
            request=request,
            user_id=user_id,
            resource_type="user",
            details=details,
        )

    async def log_password_reset_complete(
        self,
        user_id: int,
        request: Request,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a successful password reset completion.

        Args:
            user_id: ID of the user who reset password
            request: FastAPI Request object
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        return await self.log_from_request(
            action_type=AuditActionType.PASSWORD_RESET_COMPLETE,
            request=request,
            user_id=user_id,
            resource_type="user",
            resource_id=str(user_id),
            details=details,
        )

    # Account events

    async def log_account_creation(
        self,
        user_id: int,
        request: Request,
        email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a new account creation.

        Args:
            user_id: ID of the newly created user
            request: FastAPI Request object
            email: Email address of the new user
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        if email:
            details["email"] = email

        return await self.log_from_request(
            action_type=AuditActionType.ACCOUNT_CREATION,
            request=request,
            user_id=user_id,
            resource_type="user",
            resource_id=str(user_id),
            details=details,
        )

    async def log_account_deletion(
        self,
        user_id: int,
        request: Request,
        deleted_by: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log an account deletion.

        Args:
            user_id: ID of the deleted user
            request: FastAPI Request object
            deleted_by: ID of the admin who deleted the account
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        if deleted_by:
            details["deleted_by"] = deleted_by

        return await self.log_from_request(
            action_type=AuditActionType.ACCOUNT_DELETION,
            request=request,
            user_id=deleted_by,
            resource_type="user",
            resource_id=str(user_id),
            details=details,
        )

    # Role and permission events

    async def log_role_change(
        self,
        user_id: int,
        old_role: UserRole,
        new_role: UserRole,
        request: Request,
        changed_by: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a user role change.

        Args:
            user_id: ID of the user whose role was changed
            old_role: Previous role
            new_role: New role
            request: FastAPI Request object
            changed_by: ID of the admin who changed the role
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        details.update({
            "old_role": old_role.value if isinstance(old_role, UserRole) else old_role,
            "new_role": new_role.value if isinstance(new_role, UserRole) else new_role,
            "changed_by": changed_by,
        })

        return await self.log_from_request(
            action_type=AuditActionType.ROLE_CHANGE,
            request=request,
            user_id=changed_by,
            resource_type="user",
            resource_id=str(user_id),
            details=details,
        )

    async def log_permission_denied(
        self,
        user_id: Optional[int],
        resource_type: str,
        resource_id: Optional[str],
        request: Request,
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a permission denied event.

        Args:
            user_id: ID of the user who was denied access
            resource_type: Type of resource accessed
            resource_id: ID of the resource
            request: FastAPI Request object
            required_permission: Required permission that was missing
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        if required_permission:
            details["required_permission"] = required_permission

        return await self.log_from_request(
            action_type=AuditActionType.PERMISSION_DENIED,
            request=request,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )

    # Admin events

    async def log_admin_action(
        self,
        admin_id: int,
        action: str,
        request: Request,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log an administrative action.

        Args:
            admin_id: ID of the admin performing the action
            action: Description of the admin action
            request: FastAPI Request object
            resource_type: Type of resource affected
            resource_id: ID of the affected resource
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        details["admin_action"] = action

        return await self.log_from_request(
            action_type=AuditActionType.ADMIN_ACTION,
            request=request,
            user_id=admin_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )

    async def log_settings_update(
        self,
        user_id: int,
        request: Request,
        settings_changed: Dict[str, Any],
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a settings update event.

        Args:
            user_id: ID of the user who updated settings
            request: FastAPI Request object
            settings_changed: Dictionary of changed settings
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        details["settings_changed"] = settings_changed

        return await self.log_from_request(
            action_type=AuditActionType.SETTINGS_UPDATE,
            request=request,
            user_id=user_id,
            resource_type="settings",
            details=details,
        )

    async def log_data_export(
        self,
        user_id: int,
        request: Request,
        export_type: str,
        record_count: int,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log a data export event.

        Args:
            user_id: ID of the user who exported data
            request: FastAPI Request object
            export_type: Type of data exported
            record_count: Number of records exported
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        details.update({
            "export_type": export_type,
            "record_count": record_count,
        })

        return await self.log_from_request(
            action_type=AuditActionType.DATA_EXPORT,
            request=request,
            user_id=user_id,
            resource_type=export_type,
            details=details,
        )

    # API Key events

    async def log_api_key_generated(
        self,
        user_id: int,
        request: Request,
        key_name: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log an API key generation event.

        Args:
            user_id: ID of the user who generated the key
            request: FastAPI Request object
            key_name: Name of the generated key
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        details["key_name"] = key_name

        return await self.log_from_request(
            action_type=AuditActionType.API_KEY_GENERATED,
            request=request,
            user_id=user_id,
            resource_type="api_key",
            details=details,
        )

    async def log_api_key_revoked(
        self,
        user_id: int,
        request: Request,
        key_name: str,
        revoked_by: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log an API key revocation event.

        Args:
            user_id: ID of the user who owned the key
            request: FastAPI Request object
            key_name: Name of the revoked key
            revoked_by: ID of the admin who revoked the key
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        details.update({
            "key_name": key_name,
            "key_owner": user_id,
        })
        if revoked_by and revoked_by != user_id:
            details["revoked_by"] = revoked_by

        return await self.log_from_request(
            action_type=AuditActionType.API_KEY_REVOKED,
            request=request,
            user_id=revoked_by or user_id,
            resource_type="api_key",
            details=details,
        )

    # Security monitoring

    async def log_suspicious_activity(
        self,
        request: Request,
        user_id: Optional[int] = None,
        reason: str = "",
        severity: str = "medium",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Log suspicious activity for security monitoring.

        Args:
            request: FastAPI Request object
            user_id: Optional user ID if identified
            reason: Description of why the activity is suspicious
            severity: Severity level (low, medium, high, critical)
            details: Additional contextual data

        Returns:
            Created audit log entry
        """
        if details is None:
            details = {}
        details.update({
            "suspicion_reason": reason,
            "severity": severity,
        })

        log = await self.log_from_request(
            action_type=AuditActionType.SUSPICIOUS_ACTIVITY,
            request=request,
            user_id=user_id,
            resource_type="security",
            details=details,
        )

        # Log at warning level for immediate visibility
        logger.warning(
            "suspicious_activity_detected",
            user_id=user_id,
            reason=reason,
            severity=severity,
            ip_address=self._get_client_ip(request),
            audit_log_id=log.id,
        )

        return log

    # Query methods (delegated to repository)

    async def get_user_activity(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list:
        """Get recent audit logs for a specific user.

        Args:
            user_id: User ID to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Maximum number of records to return

        Returns:
            List of audit logs for the user
        """
        return await self._repository.get_user_activity(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    async def count_failed_auth_attempts(
        self,
        ip_address: Optional[str] = None,
        user_id: Optional[int] = None,
        within_minutes: int = 15,
    ) -> int:
        """Count failed authentication attempts within a time window.

        Args:
            ip_address: Optional IP address to filter by
            user_id: Optional user ID to filter by
            within_minutes: Time window in minutes to count within

        Returns:
            Number of failed authentication attempts
        """
        return await self._repository.count_failed_auth_attempts(
            ip_address=ip_address,
            user_id=user_id,
            within_minutes=within_minutes,
        )

    async def get_login_history(
        self,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> list:
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
        return await self._repository.get_login_history(
            user_id=user_id,
            ip_address=ip_address,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

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
        return await self._repository.get_activity_summary(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
