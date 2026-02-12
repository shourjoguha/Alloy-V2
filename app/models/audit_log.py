"""Security audit log model for tracking security-related events."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.enums import AuditActionType


class AuditLog(Base):
    """Security audit log for tracking authentication and authorization events.

    This model captures all security-related events including:
    - User authentication (login, logout, failed attempts)
    - Password changes and resets
    - Role and permission changes
    - Administrative actions
    - Data access and exports
    - Suspicious activity detection

    The log is designed for compliance and security monitoring purposes.
    """

    __tablename__ = "audit_logs"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # User context
    user_id = Column(Integer, nullable=True, index=True)

    # Action classification
    action_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of action performed (e.g., login, logout, password_change)"
    )

    # Resource context
    resource_type = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Type of resource affected (e.g., user, program, settings)"
    )

    resource_id = Column(
        String(100),
        nullable=True,
        index=True,
        comment="ID of the affected resource"
    )

    # Request metadata
    ip_address = Column(
        String(45),
        nullable=True,
        index=True,
        comment="IP address of the client (IPv4 or IPv6)"
    )

    user_agent = Column(
        Text,
        nullable=True,
        comment="User-Agent header from the request"
    )

    # Additional context
    details = Column(
        JSONB,
        nullable=True,
        comment="Additional contextual data (JSON) about the event"
    )

    # Timestamp
    timestamp = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="UTC timestamp when the event occurred"
    )

    # Table constraints
    __table_args__ = (
        # Composite index for common query patterns
        Index("idx_audit_logs_user_action", "user_id", "action_type"),
        Index("idx_audit_logs_timestamp_action", "timestamp", "action_type"),
        Index("idx_audit_logs_resource", "resource_type", "resource_id"),
        Index("idx_audit_logs_ip_timestamp", "ip_address", "timestamp"),
        # Ensure action_type is a valid enum value
        CheckConstraint(
            "action_type IN ('login', 'logout', 'password_change', 'password_reset_request', "
            "'password_reset_complete', 'account_creation', 'account_deletion', 'role_change', "
            "'settings_update', 'admin_action', 'data_export', 'failed_auth', 'token_refresh', "
            "'session_termination', 'permission_denied', 'suspicious_activity', "
            "'api_key_generated', 'api_key_revoked')",
            name="check_audit_action_type_valid"
        ),
    )

    def __repr__(self) -> str:
        """String representation of the audit log entry."""
        return (
            f"<AuditLog(id={self.id}, user_id={self.user_id}, "
            f"action_type='{self.action_type}', timestamp={self.timestamp})>"
        )

    def to_dict(self) -> dict:
        """Convert audit log to dictionary representation.

        Returns:
            Dictionary containing all audit log fields
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def create_entry(
        cls,
        action_type: AuditActionType | str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> "AuditLog":
        """Factory method to create a new audit log entry.

        Args:
            action_type: Type of action performed
            user_id: ID of the user who performed the action
            resource_type: Type of resource affected
            resource_id: ID of the affected resource
            ip_address: IP address of the client
            user_agent: User-Agent header value
            details: Additional contextual data

        Returns:
            New AuditLog instance
        """
        # Convert enum to string if necessary
        if isinstance(action_type, AuditActionType):
            action_type = action_type.value

        return cls(
            user_id=user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            timestamp=datetime.utcnow(),
        )
