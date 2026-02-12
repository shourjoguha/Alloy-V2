class DomainError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(DomainError):
    def __init__(self, entity: str, message: str | None = None, details: dict | None = None):
        code = f"NF_{entity.upper()}_001"
        msg = message or f"{entity} not found"
        super().__init__(code, msg, details)


class ValidationError(DomainError):
    def __init__(self, field: str, message: str, details: dict | None = None):
        code = f"VAL_{field.upper()}_001"
        msg = f"Validation failed for {field}: {message}"
        super().__init__(code, msg, details or {"field": field})


class PasswordValidationError(DomainError):
    def __init__(self, message: str, details: dict | None = None):
        code = "VAL_PASSWORD_WEAK"
        super().__init__(code, message, details)


class BusinessRuleError(DomainError):
    def __init__(self, message: str, code: str = "BR_001", details: dict | None = None):
        super().__init__(code, message, details)


class ConflictError(DomainError):
    def __init__(self, message: str, code: str = "CF_001", details: dict | None = None):
        super().__init__(code, message, details)


class AuthenticationError(DomainError):
    def __init__(self, message: str, code: str = "AUTH_001", details: dict | None = None):
        super().__init__(code, message, details)


class AuthorizationError(DomainError):
    def __init__(self, message: str, code: str = "AUTH_006", details: dict | None = None):
        super().__init__(code, message, details)
