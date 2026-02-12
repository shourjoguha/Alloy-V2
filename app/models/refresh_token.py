"""Refresh token model for JWT authentication flow."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.db.database import Base


class RefreshToken(Base):
    """Refresh token for JWT authentication flow.

    Refresh tokens allow users to obtain new access tokens without
    re-entering credentials. They are stored in the database for
    revocation support and security monitoring.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Securely hashed refresh token (bcrypt)
    token_hash = Column(String(255), nullable=False, unique=True)

    # Token metadata
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    # Device/client tracking for security
    device_name = Column(String(100), nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    # Composite index for efficient token lookup and cleanup
    __table_args__ = (
        Index("ix_refresh_tokens_user_id_revoked", "user_id", "revoked"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={self.revoked})>"

    def is_expired(self) -> bool:
        """Check if the refresh token has expired."""
        return datetime.utcnow() > self.expires_at

    def is_revoked(self) -> bool:
        """Check if the refresh token has been revoked."""
        return self.revoked

    def is_valid(self) -> bool:
        """Check if the refresh token is valid (not expired and not revoked)."""
        return not self.is_expired() and not self.is_revoked()
