"""Authentication endpoints for user registration and login."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, status, Request, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.config.settings import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    PasswordValidationError,
    ValidationError,
)
from app.db.database import get_db
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    verify_token,
    generate_refresh_token,
    hash_refresh_token,
    create_refresh_token_expiration,
    verify_refresh_token_validity,
)
from app.api.dependencies.audit import get_audit_service
from app.api.routes.dependencies import get_current_user

router = APIRouter()
settings = get_settings()


class UserRegister(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str
    name: str | None = None


class UserLogin(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int


class UserResponse(BaseModel):
    """User profile response."""
    id: int
    email: str
    name: str | None
    is_active: bool


async def create_refresh_token_for_user(
    user_id: int,
    db: AsyncSession,
    device_name: str | None = None,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> RefreshToken:
    """Create and store a refresh token for a user.

    Args:
        user_id: User ID to create token for
        db: Database session
        device_name: Optional device name for tracking
        user_agent: Optional user agent string
        ip_address: Optional IP address

    Returns:
        Created RefreshToken instance
    """
    plain_token = generate_refresh_token()
    token_hash = hash_refresh_token(plain_token)
    expires_at = create_refresh_token_expiration()

    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_name=device_name,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    db.add(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)

    # Store plain token temporarily on the object for return
    refresh_token.plain_token = plain_token

    return refresh_token


async def revoke_refresh_token_for_user(
    user_id: int,
    db: AsyncSession,
    token: str | None = None,
) -> None:
    """Revoke refresh tokens for a user.

    Args:
        user_id: User ID to revoke tokens for
        db: Database session
        token: Optional specific token to revoke. If None, revokes all tokens.
    """
    if token:
        # Revoke specific token
        token_hash = hash_refresh_token(token)
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.revoked == False
                )
            )
        )
        refresh_token = result.scalar_one_or_none()
        if refresh_token:
            refresh_token.revoked = True
            refresh_token.revoked_at = datetime.utcnow()
    else:
        # Revoke all active tokens for user
        result = await db.execute(
            select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked == False
                )
            )
        )
        refresh_tokens = result.scalars().all()
        for rt in refresh_tokens:
            rt.revoked = True
            rt.revoked_at = datetime.utcnow()

    await db.commit()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
    audit_service = Depends(get_audit_service),
):
    """Register a new user.

    Args:
        user_data: User registration data (email, password, name)
        request: FastAPI Request object
        db: Database session
        audit_service: Audit service for logging

    Returns:
        JWT access token, refresh token, and user ID

    Raises:
        HTTPException: If email already registered
    """
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise ConflictError(
            "Email already registered",
            details={"email": user_data.email}
        )

    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        name=user_data.name,
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Log account creation
    await audit_service.log_account_creation(
        user_id=new_user.id,
        request=request,
        email=new_user.email,
    )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(new_user.id)},
        expires_delta=access_token_expires,
    )

    # Create refresh token
    refresh_token = await create_refresh_token_for_user(
        user_id=new_user.id,
        db=db,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    # Log successful login (first login after registration)
    await audit_service.log_login(
        user_id=new_user.id,
        request=request,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token.plain_token,
        user_id=new_user.id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
    audit_service = Depends(get_audit_service),
):
    """Authenticate user and return JWT token.

    Args:
        user_data: User login credentials (email, password)
        request: FastAPI Request object
        db: Database session
        audit_service: Audit service for logging

    Returns:
        JWT access token, refresh token, and user ID

    Raises:
        HTTPException: If credentials are invalid
    """
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_data.password, user.hashed_password):
        # Log failed authentication attempt
        await audit_service.log_failed_auth(
            email=user_data.email,
            user_id=user.id if user else None,
            request=request,
            reason="Invalid email or password",
        )
        raise AuthenticationError(
            "Incorrect email or password",
            details={"email": user_data.email}
        )

    if not user.is_active:
        # Log failed authentication due to inactive account
        await audit_service.log_failed_auth(
            email=user_data.email,
            user_id=user.id,
            request=request,
            reason="User account is inactive",
        )
        raise AuthorizationError(
            "User account is inactive",
            code="AUTH_ACCOUNT_INACTIVE",
            details={"user_id": user.id, "email": user_data.email}
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )

    # Create refresh token
    refresh_token = await create_refresh_token_for_user(
        user_id=user.id,
        db=db,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    # Log successful login
    await audit_service.log_login(
        user_id=user.id,
        request=request,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token.plain_token,
        user_id=user.id,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    token_request: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using a refresh token.

    Args:
        token_request: Request containing the refresh token
        request: FastAPI Request object
        db: Database session

    Returns:
        New JWT access token and refresh token, and user ID

    Raises:
        HTTPException: If refresh token is invalid, expired, or revoked
    """
    plain_token = token_request.refresh_token

    # Find the refresh token by hash
    token_hash = hash_refresh_token(plain_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    refresh_token = result.scalar_one_or_none()

    if not refresh_token:
        raise AuthenticationError(
            "Invalid refresh token",
            details={"reason": "token_not_found"}
        )

    # Verify token validity
    is_valid, error_msg = verify_refresh_token_validity(
        token=plain_token,
        token_hash=refresh_token.token_hash,
        expires_at=refresh_token.expires_at,
        revoked=refresh_token.revoked,
    )

    if not is_valid:
        raise AuthenticationError(
            error_msg,
            details={"reason": "token_invalid"}
        )

    # Get user to ensure they still exist and are active
    result = await db.execute(
        select(User).where(User.id == refresh_token.user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        # Revoke the token if user is inactive or deleted
        refresh_token.revoked = True
        refresh_token.revoked_at = datetime.utcnow()
        await db.commit()

        if not user:
            raise NotFoundError(
                "User",
                "User account deleted",
                details={"user_id": refresh_token.user_id}
            )
        else:
            raise AuthorizationError(
                "User account is inactive",
                code="AUTH_ACCOUNT_INACTIVE",
                details={"user_id": user.id}
            )

    # Create new access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )

    # Create new refresh token (rotate tokens for security)
    await revoke_refresh_token_for_user(
        user_id=user.id,
        db=db,
        token=plain_token,
    )
    new_refresh_token = await create_refresh_token_for_user(
        user_id=user.id,
        db=db,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token.plain_token,
        user_id=user.id,
    )


@router.get("/verify-token", response_model=UserResponse)
async def verify_token_endpoint(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Verify a JWT token and return user information.

    Args:
        token: JWT access token
        db: Database session

    Returns:
        User information

    Raises:
        HTTPException: If token is invalid or user not found
    """
    user_id = verify_token(token)

    if user_id is None:
        raise AuthenticationError(
            "Invalid token",
            details={"reason": "token_invalid"}
        )

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundError(
            "User",
            details={"user_id": user_id}
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
    )


@router.post("/logout")
async def logout(
    request: Request,
    refresh_token: str | None = Header(None, alias="X-Refresh-Token"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit_service = Depends(get_audit_service),
):
    """Logout current user and revoke refresh token.

    Args:
        request: FastAPI Request object
        refresh_token: Refresh token to revoke (optional, from X-Refresh-Token header)
        current_user: Current authenticated user
        db: Database session
        audit_service: Audit service for logging

    Returns:
        Success message

    Note:
        This logs the logout event and revokes the provided refresh token.
        Clients should delete both access and refresh tokens.
    """
    # Revoke the provided refresh token if present
    if refresh_token:
        await revoke_refresh_token_for_user(
            user_id=current_user.id,
            db=db,
            token=refresh_token,
        )

    # Log logout event
    await audit_service.log_logout(
        user_id=current_user.id,
        request=request,
    )

    return {"message": "Logged out successfully"}
