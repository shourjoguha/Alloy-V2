"""Middleware for automatic audit logging of authentication events."""
from typing import Optional, Callable, Awaitable, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.services.audit_service import AuditService
from app.models.enums import AuditActionType
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic audit logging of security events.

    This middleware intercepts authentication-related requests and logs
    them to audit log system. It handles:
    - Login attempts (success and failure)
    - Logout events
    - Failed authentication attempts
    - Rate limit violations

    The middleware extracts request information and logs events asynchronously
    without blocking request-response cycle.
    """
    def __init__(
        self,
        app: ASGIApp,
        audit_service_factory: Callable[[], Awaitable[AuditService]],
        enabled: bool = True,
    ):
        """Initialize audit logging middleware.

        Args:
            app: ASGI application
            audit_service_factory: Async factory function to create AuditService instances
            enabled: Whether audit logging is enabled
        """
        super().__init__(app)
        self._audit_service_factory = audit_service_factory
        self._enabled = enabled

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request and log audit events.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint in the chain

        Returns:
            Response from next handler
        """
        if not self._enabled:
            return await call_next(request)

        # Cache request body before processing to avoid "stream consumed" error
        request._body = await request.body()

        # Store original response for audit logging
        response = await call_next(request)

        # Log authentication events based on path and status
        await self._log_auth_event(request, response)
        return response

    async def _log_auth_event(self, request: Request, response: Response) -> None:
        """Log authentication events based on request path and response status.

        Args:
            request: The incoming request
            response: The response from the handler
        """
        path = request.url.path
        method = request.method

        # Only process POST requests to auth endpoints
        if method != "POST":
            return

        try:
            # Get audit service
            audit_service = await self._audit_service_factory()

            # Login endpoint
            if path.endswith("/auth/login"):
                await self._handle_login(request, response, audit_service)

            # Register endpoint
            elif path.endswith("/auth/register"):
                await self._handle_register(request, response, audit_service)

            # Logout endpoint (typically DELETE or POST)
            elif path.endswith("/auth/logout") or path.endswith("/auth/logout"):
                await self._handle_logout(request, response, audit_service)

        except Exception as e:
            # Never fail the request due to audit logging errors
            logger.error(
                "audit_logging_failed",
                path=path,
                method=method,
                error=str(e),
                exc_info=e,
            )

    async def _handle_login(
        self,
        request: Request,
        response: Response,
        audit_service: AuditService,
    ) -> None:
        """Handle login endpoint audit logging.

        Args:
            request: The incoming request
            response: The response from the handler
            audit_service: Audit service instance
        """
        status_code = response.status_code

        if status_code == 200:
            # Successful login - extract user_id from response
            user_id = await self._extract_user_id_from_response(response)
            if user_id:
                await audit_service.log_login(
                    user_id=user_id,
                    request=request,
                    details={"status_code": status_code},
                )

        elif status_code == 401:
            # Failed login - extract email from request body
            email = await self._extract_email_from_request(request)
            await audit_service.log_failed_auth(
                email=email,
                user_id=None,
                request=request,
                reason=f"Status code: {status_code}",
            )

    async def _handle_register(
        self,
        request: Request,
        response: Response,
        audit_service: AuditService,
    ) -> None:
        """Handle register endpoint audit logging.

        Args:
            request: The incoming request
            response: The response from the handler
            audit_service: Audit service instance
        """
        status_code = response.status_code

        if status_code in [200, 201]:
            # Successful registration - extract user_id from response
            user_id = await self._extract_user_id_from_response(response)
            if user_id:
                await audit_service.log_account_creation(
                    user_id=user_id,
                    request=request,
                    details={"status_code": status_code},
                )

    async def _handle_logout(
        self,
        request: Request,
        response: Response,
        audit_service: AuditService,
    ) -> None:
        """Handle logout endpoint audit logging.

        Args:
            request: The incoming request
            response: The response from the handler
            audit_service: Audit service instance
        """
        status_code = response.status_code

        if status_code == 200:
            # Get user_id from request state (set by auth middleware)
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                await audit_service.log_logout(
                    user_id=user_id,
                    request=request,
                    details={"status_code": status_code},
                )

    async def _extract_user_id_from_response(self, response: Response) -> Optional[int]:
        """Extract user_id from response body.

        Args:
            response: The response object

        Returns:
            User ID if found, None otherwise
        """
        try:
            import json

            body = response.body
            if body:
                data = json.loads(body.decode())
                if isinstance(data, dict):
                    return data.get("user_id")
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass
        return None

    async def _extract_email_from_request(self, request: Request) -> Optional[str]:
        """Extract email from request body.

        Args:
            request: The request object

        Returns:
            Email address if found, None otherwise
        """
        try:
            import json

            # Use cached body from request._body
            body_bytes = getattr(request, "_body", None)
            if body_bytes:
                body = json.loads(body_bytes.decode())
                if isinstance(body, dict):
                    return body.get("email")
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass
        return None


class AuditContextMiddleware(BaseHTTPMiddleware):
    """Middleware to add audit context to request state.

    This middleware extracts audit-related information from the request
    and makes it available via request.state for use in endpoints.
    """
    def __init__(
        self,
        app: ASGIApp,
        enabled: bool = True,
    ):
        """Initialize audit context middleware.

        Args:
            app: ASGI application
            enabled: Whether audit context extraction is enabled
        """
        super().__init__(app)
        self._enabled = enabled

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request and add audit context.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint in the chain

        Returns:
            Response from next handler
        """
        if not self._enabled:
            return await call_next(request)

        # Extract user agent and IP for audit context
        request.state.user_agent = request.headers.get("user-agent", "")
        request.state.ip_address = request.client.host if request.client else "unknown"

        # Continue processing
        return await call_next(request)


class SecurityEventMiddleware(BaseHTTPMiddleware):
    """Middleware for detecting and logging security events.

    This middleware monitors for:
    - Suspicious activity patterns
    - Rate limit violations
    - Brute force attempts
    - Account enumeration attempts
    """
    def __init__(
        self,
        app: ASGIApp,
        audit_service_factory: Callable[[], Awaitable[AuditService]],
        enabled: bool = True,
    ):
        """Initialize security event middleware.

        Args:
            app: ASGI application
            audit_service_factory: Async factory function to create AuditService instances
            enabled: Whether security event detection is enabled
        """
        super().__init__(app)
        self._audit_service_factory = audit_service_factory
        self._enabled = enabled

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process request and detect security events.

        Args:
            request: Incoming request
            call_next: Next middleware/endpoint in the chain

        Returns:
            Response from next handler
        """
        if not self._enabled:
            return await call_next(request)

        try:
            # Get audit service
            audit_service = await self._audit_service_factory()

            # Monitor for suspicious patterns
            path = request.url.path

            # Detect account enumeration attempts
            if "/auth/" in path and request.method == "POST":
                await self._check_account_enumeration(request, audit_service)

            # Detect rate limit violations (check response)
            response = await call_next(request)
            if response.status_code == 429:
                await audit_service.log_suspicious_activity(
                    request=request,
                    user_id=getattr(request.state, "user_id", None),
                    reason="Rate limit violation",
                    severity="medium",
                    details={"path": path},
                )

            return response

        except Exception as e:
            # Never fail the request due to security monitoring errors
            logger.error(
                "security_event_failed",
                error=str(e),
                exc_info=e,
            )
            return await call_next(request)

    async def _check_account_enumeration(
        self,
        request: Request,
        audit_service: AuditService,
    ) -> None:
        """Check for account enumeration patterns.

        Args:
            request: The incoming request
            audit_service: Audit service instance
        """
        try:
            import json

            # Extract email from request
            body_bytes = getattr(request, "_body", None)
            if not body_bytes:
                body_bytes = await request.body()
            
            if body_bytes:
                data = json.loads(body_bytes.decode())
                if isinstance(data, dict):
                    email = data.get("email")

                    # Check if email follows enumeration pattern
                    if email and any(pattern in email for pattern in ["test", "admin", "user"]):
                        await audit_service.log_suspicious_activity(
                            request=request,
                            user_id=None,
                            reason="Possible account enumeration attempt",
                            severity="low",
                            details={"email": email, "pattern": "suspicious_email_format"},
                        )

        except Exception:
            # Ignore errors in enumeration detection
            pass
