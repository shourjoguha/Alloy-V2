"""JWT token utilities for authentication."""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from secrets import token_urlsafe

import bcrypt
from jose import JWTError, jwt

from app.config.settings import get_settings
from app.models.user import UserRole

settings = get_settings()


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token (e.g., {"sub": user_id, "role": role})
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "role": data.get("role", UserRole.USER)})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str) -> Optional[int]:
    """Verify a JWT token and extract the user ID.

    Args:
        token: JWT token string

    Returns:
        User ID if valid, None otherwise
    """
    payload = decode_access_token(token)

    if payload is None:
        return None

    user_id: Optional[int] = payload.get("sub")

    if user_id is None:
        return None

    return int(user_id)


def generate_refresh_token() -> str:
    """Generate a secure random refresh token.

    Returns:
        Cryptographically secure random token string
    """
    return token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token for secure storage.

    Args:
        token: Plain text refresh token

    Returns:
        SHA-256 hashed token (hex string)
    """
    import hashlib
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def verify_refresh_token_hash(token: str, token_hash: str) -> bool:
    """Verify a refresh token against its stored hash.

    Args:
        token: Plain text refresh token
        token_hash: Stored hash

    Returns:
        True if token matches hash, False otherwise
    """
    import hashlib
    computed_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    return computed_hash == token_hash


def create_refresh_token_expiration() -> datetime:
    """Calculate refresh token expiration time.

    Returns:
        Expiration datetime based on settings
    """
    return datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)


def verify_refresh_token_validity(
    token: str,
    token_hash: str,
    expires_at: datetime,
    revoked: bool
) -> Tuple[bool, Optional[str]]:
    """Verify a refresh token is valid (not expired, not revoked, matches hash).

    Args:
        token: Plain text refresh token
        token_hash: Stored bcrypt hash
        expires_at: Token expiration datetime
        revoked: Whether token is revoked

    Returns:
        Tuple of (is_valid, error_message)
    """
    if revoked:
        return False, "Token has been revoked"

    if datetime.utcnow() > expires_at:
        return False, "Token has expired"

    if not verify_refresh_token_hash(token, token_hash):
        return False, "Invalid token"

    return True, None
