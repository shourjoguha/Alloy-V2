"""Tests for the audit logging system."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock
from fastapi import Request
import sys
import os

# Direct imports to avoid circular dependency issues
from app.models.audit_log import AuditLog
from app.models.enums import AuditActionType, UserRole


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_request():
    """Mock FastAPI request."""
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.path = "/auth/login"
    request.headers = {"user-agent": "Mozilla/5.0", "x-forwarded-for": "192.168.1.1"}
    request.client = Mock()
    request.client.host = "10.0.0.1"
    request.state = Mock()
    return request


class TestAuditLogModel:
    """Tests for AuditLog model."""

    def test_create_entry_factory(self):
        """Test AuditLog.create_entry factory method."""
        log = AuditLog.create_entry(
            action_type=AuditActionType.LOGIN,
            user_id=1,
            resource_type="user",
            resource_id="1",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            details={"test": "data"},
        )

        assert log.user_id == 1
        assert log.action_type == "login"
        assert log.resource_type == "user"
        assert log.resource_id == "1"
        assert log.ip_address == "192.168.1.1"
        assert log.user_agent == "Mozilla/5.0"
        assert log.details == {"test": "data"}
        assert isinstance(log.timestamp, datetime)

    def test_create_entry_with_string_action(self):
        """Test AuditLog.create_entry with string action type."""
        log = AuditLog.create_entry(
            action_type="login",  # String instead of enum
            user_id=1,
        )

        assert log.action_type == "login"
        assert log.user_id == 1

    def test_to_dict(self):
        """Test AuditLog.to_dict method."""
        log = AuditLog(
            id=1,
            user_id=1,
            action_type="login",
            resource_type="user",
            resource_id="1",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            details={"test": "data"},
            timestamp=datetime.utcnow(),
        )

        result = log.to_dict()

        assert result["id"] == 1
        assert result["user_id"] == 1
        assert result["action_type"] == "login"
        assert result["resource_type"] == "user"
        assert "timestamp" in result

    def test_repr(self):
        """Test AuditLog.__repr__ method."""
        log = AuditLog(
            id=1,
            user_id=1,
            action_type="login",
            timestamp=datetime.utcnow(),
        )

        repr_str = repr(log)
        assert "AuditLog" in repr_str
        assert "id=1" in repr_str
        assert "user_id=1" in repr_str
        assert "login" in repr_str


class TestAuditActionTypeEnum:
    """Tests for AuditActionType enum."""

    def test_all_action_types_defined(self):
        """Verify all expected action types are defined."""
        assert AuditActionType.LOGIN.value == "login"
        assert AuditActionType.LOGOUT.value == "logout"
        assert AuditActionType.PASSWORD_CHANGE.value == "password_change"
        assert AuditActionType.PASSWORD_RESET_REQUEST.value == "password_reset_request"
        assert AuditActionType.PASSWORD_RESET_COMPLETE.value == "password_reset_complete"
        assert AuditActionType.ACCOUNT_CREATION.value == "account_creation"
        assert AuditActionType.ACCOUNT_DELETION.value == "account_deletion"
        assert AuditActionType.ROLE_CHANGE.value == "role_change"
        assert AuditActionType.SETTINGS_UPDATE.value == "settings_update"
        assert AuditActionType.ADMIN_ACTION.value == "admin_action"
        assert AuditActionType.DATA_EXPORT.value == "data_export"
        assert AuditActionType.FAILED_AUTH.value == "failed_auth"
        assert AuditActionType.TOKEN_REFRESH.value == "token_refresh"
        assert AuditActionType.SESSION_TERMINATION.value == "session_termination"
        assert AuditActionType.PERMISSION_DENIED.value == "permission_denied"
        assert AuditActionType.SUSPICIOUS_ACTIVITY.value == "suspicious_activity"
        assert AuditActionType.API_KEY_GENERATED.value == "api_key_generated"
        assert AuditActionType.API_KEY_REVOKED.value == "api_key_revoked"


class TestUserRoleEnum:
    """Tests for UserRole enum."""

    def test_all_user_roles_defined(self):
        """Verify all expected user roles are defined."""
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.SUPER_ADMIN.value == "super_admin"


class TestAuditLogFields:
    """Tests for AuditLog model fields."""

    def test_default_timestamp(self):
        """Test that timestamp defaults to current UTC time."""
        before = datetime.utcnow()
        log = AuditLog.create_entry(action_type=AuditActionType.LOGIN)
        after = datetime.utcnow()

        assert before <= log.timestamp <= after

    def test_nullable_fields(self):
        """Test that optional fields can be None."""
        log = AuditLog(
            id=1,
            action_type="login",
            timestamp=datetime.utcnow(),
            user_id=None,
            resource_type=None,
            resource_id=None,
            ip_address=None,
            user_agent=None,
            details=None,
        )

        assert log.user_id is None
        assert log.resource_type is None
        assert log.resource_id is None
        assert log.ip_address is None
        assert log.user_agent is None
        assert log.details is None

    def test_details_jsonb_field(self):
        """Test that details field accepts JSON data."""
        test_details = {
            "nested": {
                "data": [1, 2, 3],
                "string": "test"
            },
            "number": 42,
            "boolean": True,
        }

        log = AuditLog.create_entry(
            action_type=AuditActionType.ADMIN_ACTION,
            details=test_details,
        )

        assert log.details == test_details
