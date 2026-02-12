"""Shared dependencies for API routes."""
import warnings
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.db.database import get_db
from app.models.user import User, UserRole
from app.security import verify_token
settings = get_settings()

P = ParamSpec('P')
T = TypeVar('T')


async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from JWT token.

    For MVP: Falls back to default_user_id if no token provided.

    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
        db: Database session

    Returns:
        User object

    Raises:
        AuthenticationError: If token is invalid
    """
    if not authorization:
        if settings.default_user_id:
            user = await db.get(User, settings.default_user_id)
            if user:
                return user
        raise AuthenticationError("No authorization header provided")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise AuthenticationError("Invalid authentication scheme")
    except ValueError:
        raise AuthenticationError("Invalid authorization header format")

    user_id = verify_token(token)

    if user_id is None:
        raise AuthenticationError("Invalid or expired token")

    user = await db.get(User, user_id)
    if not user:
        raise AuthenticationError("User not found")

    return user


async def get_current_user_id(
    authorization: str | None = Header(None, alias="Authorization"),
) -> int:
    """Get current user ID from JWT token.

    For MVP: Falls back to default_user_id if no token provided.

    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")

    Returns:
        User ID from token or default user ID

    Raises:
        HTTPException: If token is invalid
    """
    if not authorization:
        return settings.default_user_id

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication scheme",
            )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format",
        )

    user_id = verify_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return user_id


def require_role(*allowed_roles: UserRole):
    """Decorator factory for role-based access control.

    Args:
        *allowed_roles: List of allowed UserRole values

    Returns:
        Decorator function

    Example:
        ```python
        @router.get("/admin/data")
        @require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
        async def get_admin_data(current_user: User = Depends(get_current_user)):
            # Only accessible by admin or super_admin
            return {"data": "admin_only"}
        ```
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            current_user = kwargs.get('current_user')
            if not current_user:
                raise AuthorizationError("User not authenticated")

            if current_user.role not in allowed_roles:
                raise AuthorizationError(
                    f"Requires one of roles: {[r.value for r in allowed_roles]}",
                    {
                        "required_roles": [r.value for r in allowed_roles],
                        "user_role": current_user.role.value
                    }
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def require_admin(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> bool:
    """Verify admin token for protected endpoints.
    
    DEPRECATED: Use JWT with admin role instead. See docs/authentication/rbac
    
    This dependency validates admin authentication using of X-Admin-Token header.
    If no admin token is configured in settings, access is allowed for development.
    
    Args:
        x_admin_token: Admin token from X-Admin-Token header
        
    Returns:
        True if authenticated
        
    Raises:
        HTTPException: If authentication fails (401 Unauthorized)
        
    Example:
        ```python
        @router.get("/admin/data")
        async def get_admin_data(admin: bool = Depends(require_admin)):
            # Only accessible with valid admin token
            return {"data": "admin_only"}
        ```
    """
    warnings.warn(
        "X-Admin-Token is deprecated. Use JWT with admin role instead. "
        "See docs/authentication/rbac for migration guide.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if not settings.admin_api_token:
        # If no admin token is configured, allow access (development mode)
        return True
    if x_admin_token != settings.admin_api_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
            headers={
                "WWW-Authenticate": "Bearer",
                "X-Admin-Token": "required",
                "Deprecation": "Use JWT with admin role",
            },
        )
    return True


# Admin response models
class AdminResponse(BaseModel):
    """Base response model for admin endpoints.

    Attributes:
        success: Whether the operation was successful
        message: Human-readable message describing the result
    """

    success: bool
    message: str


class AdminErrorResponse(BaseModel):
    """Error response for admin endpoints.

    Attributes:
        error: Error type or category
        detail: Detailed error message (optional)
    """

    error: str
    detail: str | None = None
