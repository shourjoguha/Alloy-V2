"""Tests for domain error handler to verify structured JSON error responses."""
import pytest
from datetime import datetime
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.error_handlers import domain_error_handler, ERROR_STATUS_MAP
from app.core.exceptions import (
    DomainError,
    NotFoundError,
    ValidationError,
    BusinessRuleError,
    ConflictError,
    AuthenticationError,
    AuthorizationError,
)


class MockRequest:
    """Mock FastAPI Request object for testing."""
    
    def __init__(self, request_id: str = "test-request-123"):
        self.state = type('State', (), {'request_id': request_id})()


class TestDomainErrorExceptions:
    """Test domain exception classes and their error codes."""
    
    def test_domain_error_base(self):
        """Test base DomainError class."""
        error = DomainError(
            code="TEST_001",
            message="Test error message",
            details={"key": "value"}
        )
        
        assert error.code == "TEST_001"
        assert error.message == "Test error message"
        assert error.details == {"key": "value"}
        assert str(error) == "Test error message"
    
    def test_not_found_error(self):
        """Test NotFoundError generates correct error code."""
        error = NotFoundError("program", "Program not found", {"program_id": 123})
        
        assert error.code == "NF_PROGRAM_001"
        assert error.message == "Program not found"
        assert error.details == {"program_id": 123}
    
    def test_not_found_error_default_message(self):
        """Test NotFoundError generates default message when none provided."""
        error = NotFoundError("user")
        
        assert error.code == "NF_USER_001"
        assert error.message == "user not found"
        assert error.details == {}
    
    def test_validation_error(self):
        """Test ValidationError generates correct error code."""
        error = ValidationError("email", "Invalid email format")
        
        assert error.code == "VAL_EMAIL_001"
        assert error.message == "Validation failed for email: Invalid email format"
        assert error.details == {"field": "email"}
    
    def test_validation_error_with_details(self):
        """Test ValidationError with custom details."""
        error = ValidationError(
            "password",
            "Password too weak",
            {"min_length": 8, "actual_length": 4}
        )
        
        assert error.code == "VAL_PASSWORD_001"
        assert "Password too weak" in error.message
        assert error.details == {"min_length": 8, "actual_length": 4}
    
    def test_business_rule_error_default(self):
        """Test BusinessRuleError with default code."""
        error = BusinessRuleError("Cannot delete active program")
        
        assert error.code == "BR_001"
        assert error.message == "Cannot delete active program"
        assert error.details == {}
    
    def test_business_rule_error_custom_code(self):
        """Test BusinessRuleError with custom code."""
        error = BusinessRuleError(
            "Goal interference detected",
            code="BR_GOAL_INTERFERENCE",
            details={"goals": ["strength", "endurance"]}
        )
        
        assert error.code == "BR_GOAL_INTERFERENCE"
        assert error.message == "Goal interference detected"
        assert error.details == {"goals": ["strength", "endurance"]}
    
    def test_conflict_error_default(self):
        """Test ConflictError with default code."""
        error = ConflictError("Resource already exists")
        
        assert error.code == "CF_001"
        assert error.message == "Resource already exists"
        assert error.details == {}
    
    def test_conflict_error_custom(self):
        """Test ConflictError with custom code and details."""
        error = ConflictError(
            "Email already registered",
            code="CF_EMAIL_EXISTS",
            details={"email": "test@example.com"}
        )
        
        assert error.code == "CF_EMAIL_EXISTS"
        assert error.message == "Email already registered"
        assert error.details == {"email": "test@example.com"}
    
    def test_authentication_error_default(self):
        """Test AuthenticationError with default code."""
        error = AuthenticationError("Invalid credentials")
        
        assert error.code == "AUTH_001"
        assert error.message == "Invalid credentials"
        assert error.details == {}
    
    def test_authentication_error_custom(self):
        """Test AuthenticationError with custom code."""
        error = AuthenticationError(
            "Token expired",
            code="AUTH_TOKEN_EXPIRED",
            details={"expired_at": "2024-01-01T00:00:00Z"}
        )
        
        assert error.code == "AUTH_TOKEN_EXPIRED"
        assert error.message == "Token expired"
        assert error.details == {"expired_at": "2024-01-01T00:00:00Z"}
    
    def test_authorization_error_default(self):
        """Test AuthorizationError with default code."""
        error = AuthorizationError("Insufficient permissions")
        
        assert error.code == "AUTH_006"
        assert error.message == "Insufficient permissions"
        assert error.details == {}
    
    def test_authorization_error_custom(self):
        """Test AuthorizationError with custom details."""
        error = AuthorizationError(
            "Admin access required",
            code="AUTH_ADMIN_ONLY",
            details={"required_role": "admin", "user_role": "user"}
        )
        
        assert error.code == "AUTH_ADMIN_ONLY"
        assert error.message == "Admin access required"
        assert error.details == {"required_role": "admin", "user_role": "user"}


class TestErrorStatusMap:
    """Test ERROR_STATUS_MAP mapping."""
    
    def test_status_map_complete(self):
        """Verify all domain errors have status codes mapped."""
        assert NotFoundError in ERROR_STATUS_MAP
        assert ValidationError in ERROR_STATUS_MAP
        assert BusinessRuleError in ERROR_STATUS_MAP
        assert ConflictError in ERROR_STATUS_MAP
        assert AuthenticationError in ERROR_STATUS_MAP
        assert AuthorizationError in ERROR_STATUS_MAP
    
    def test_not_found_status(self):
        """Test NotFoundError maps to 404."""
        assert ERROR_STATUS_MAP[NotFoundError] == 404
    
    def test_validation_status(self):
        """Test ValidationError maps to 400."""
        assert ERROR_STATUS_MAP[ValidationError] == 400
    
    def test_business_rule_status(self):
        """Test BusinessRuleError maps to 422."""
        assert ERROR_STATUS_MAP[BusinessRuleError] == 422
    
    def test_conflict_status(self):
        """Test ConflictError maps to 409."""
        assert ERROR_STATUS_MAP[ConflictError] == 409
    
    def test_authentication_status(self):
        """Test AuthenticationError maps to 401."""
        assert ERROR_STATUS_MAP[AuthenticationError] == 401
    
    def test_authorization_status(self):
        """Test AuthorizationError maps to 403."""
        assert ERROR_STATUS_MAP[AuthorizationError] == 403


class TestDomainErrorHandler:
    """Test domain_error_handler function."""
    
    @pytest.mark.asyncio
    async def test_not_found_error_response(self):
        """Test NotFoundError returns 404 with structured JSON."""
        error = NotFoundError("program", "Program with ID 999 not found", {"program_id": 999})
        request = MockRequest(request_id="req-123")
        
        response = await domain_error_handler(request, error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        
        content = response.body.decode()
        import json
        data = json.loads(content)
        
        assert "data" in data
        assert data["data"] is None
        assert "meta" in data
        assert "errors" in data
        assert len(data["errors"]) == 1
        
        error_dict = data["errors"][0]
        assert error_dict["code"] == "NF_PROGRAM_001"
        assert error_dict["message"] == "Program with ID 999 not found"
        assert error_dict["details"] == {"program_id": 999}
    
    @pytest.mark.asyncio
    async def test_validation_error_response(self):
        """Test ValidationError returns 400 with structured JSON."""
        error = ValidationError("email", "Invalid email format")
        request = MockRequest(request_id="req-456")
        
        response = await domain_error_handler(request, error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        
        import json
        data = json.loads(response.body.decode())
        
        error_dict = data["errors"][0]
        assert error_dict["code"] == "VAL_EMAIL_001"
        assert "Invalid email format" in error_dict["message"]
        assert error_dict["details"]["field"] == "email"
    
    @pytest.mark.asyncio
    async def test_business_rule_error_response(self):
        """Test BusinessRuleError returns 422 with structured JSON."""
        error = BusinessRuleError(
            "Cannot modify completed program",
            code="BR_COMPLETED_PROGRAM",
            details={"program_id": 123, "status": "completed"}
        )
        request = MockRequest(request_id="req-789")
        
        response = await domain_error_handler(request, error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 422
        
        import json
        data = json.loads(response.body.decode())
        
        error_dict = data["errors"][0]
        assert error_dict["code"] == "BR_COMPLETED_PROGRAM"
        assert error_dict["message"] == "Cannot modify completed program"
        assert error_dict["details"] == {"program_id": 123, "status": "completed"}
    
    @pytest.mark.asyncio
    async def test_conflict_error_response(self):
        """Test ConflictError returns 409 with structured JSON."""
        error = ConflictError(
            "Email already in use",
            code="CF_EMAIL_EXISTS",
            details={"email": "test@example.com"}
        )
        request = MockRequest(request_id="req-abc")
        
        response = await domain_error_handler(request, error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 409
        
        import json
        data = json.loads(response.body.decode())
        
        error_dict = data["errors"][0]
        assert error_dict["code"] == "CF_EMAIL_EXISTS"
        assert error_dict["details"]["email"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_authentication_error_response(self):
        """Test AuthenticationError returns 401 with structured JSON."""
        error = AuthenticationError("Invalid or expired token")
        request = MockRequest(request_id="req-auth")
        
        response = await domain_error_handler(request, error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        
        import json
        data = json.loads(response.body.decode())
        
        error_dict = data["errors"][0]
        assert error_dict["code"] == "AUTH_001"
        assert error_dict["message"] == "Invalid or expired token"
    
    @pytest.mark.asyncio
    async def test_authorization_error_response(self):
        """Test AuthorizationError returns 403 with structured JSON."""
        error = AuthorizationError(
            "Admin access required",
            code="AUTH_ADMIN_ONLY",
            details={"required_role": "admin", "user_role": "user"}
        )
        request = MockRequest(request_id="req-authz")
        
        response = await domain_error_handler(request, error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 403
        
        import json
        data = json.loads(response.body.decode())
        
        error_dict = data["errors"][0]
        assert error_dict["code"] == "AUTH_ADMIN_ONLY"
        assert error_dict["details"]["required_role"] == "admin"
    
    @pytest.mark.asyncio
    async def test_response_includes_metadata(self):
        """Test error response includes request_id and timestamp."""
        error = NotFoundError("test_entity")
        request = MockRequest(request_id="test-request-id-12345")
        
        response = await domain_error_handler(request, error)
        
        import json
        data = json.loads(response.body.decode())
        
        assert "meta" in data
        assert data["meta"]["request_id"] == "test-request-id-12345"
        assert "timestamp" in data["meta"]
        
        # Verify timestamp is a valid ISO datetime string
        datetime.fromisoformat(data["meta"]["timestamp"].replace('Z', '+00:00'))
    
    @pytest.mark.asyncio
    async def test_unknown_domain_error_returns_500(self):
        """Test unknown DomainError subclass returns 500."""
        
        class CustomDomainError(DomainError):
            """Custom domain error not in status map."""
            pass
        
        error = CustomDomainError("CUSTOM_001", "Custom error message")
        request = MockRequest(request_id="req-custom")
        
        response = await domain_error_handler(request, error)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500  # Default for unmapped errors
        
        import json
        data = json.loads(response.body.decode())
        
        error_dict = data["errors"][0]
        assert error_dict["code"] == "CUSTOM_001"
        assert error_dict["message"] == "Custom error message"
    
    @pytest.mark.asyncio
    async def test_error_with_empty_details(self):
        """Test error response when details dict is empty."""
        error = NotFoundError("user")
        request = MockRequest(request_id="req-empty")
        
        response = await domain_error_handler(request, error)
        
        import json
        data = json.loads(response.body.decode())
        
        error_dict = data["errors"][0]
        assert error_dict["details"] == {}
    
    @pytest.mark.asyncio
    async def test_error_with_none_request_id(self):
        """Test error response when request has no request_id."""
        error = ValidationError("field", "Invalid field")
        
        # Create a mock request without request_id in state
        request = type('Request', (), {
            'state': type('State', (), {})()
        })()
        
        response = await domain_error_handler(request, error)
        
        import json
        data = json.loads(response.body.decode())
        
        # Should handle missing request_id gracefully
        assert data["meta"]["request_id"] is None


class TestErrorResponseStructure:
    """Test that all error responses have consistent structure."""
    
    @pytest.mark.asyncio
    async def test_all_errors_have_consistent_structure(self):
        """Verify all domain error types return consistent response structure."""
        errors = [
            NotFoundError("test", "Not found"),
            ValidationError("field", "Validation failed"),
            BusinessRuleError("Business rule violation"),
            ConflictError("Conflict detected"),
            AuthenticationError("Authentication failed"),
            AuthorizationError("Authorization failed"),
        ]
        
        request = MockRequest(request_id="test-req")
        
        for error in errors:
            response = await domain_error_handler(request, error)
            
            import json
            data = json.loads(response.body.decode())
            
            # Verify top-level structure
            assert "data" in data
            assert "meta" in data
            assert "errors" in data
            
            # Verify data is null for errors
            assert data["data"] is None
            
            # Verify meta structure
            assert "request_id" in data["meta"]
            assert "timestamp" in data["meta"]
            
            # Verify errors array structure
            assert isinstance(data["errors"], list)
            assert len(data["errors"]) == 1
            
            # Verify error object structure
            error_obj = data["errors"][0]
            assert "code" in error_obj
            assert "message" in error_obj
            assert "details" in error_obj
            
            # Verify types
            assert isinstance(error_obj["code"], str)
            assert isinstance(error_obj["message"], str)
            assert isinstance(error_obj["details"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
