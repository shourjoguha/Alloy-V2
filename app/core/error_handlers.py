from datetime import datetime

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)


ERROR_STATUS_MAP: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_400_BAD_REQUEST,
    BusinessRuleError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ConflictError: status.HTTP_409_CONFLICT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AuthorizationError: status.HTTP_403_FORBIDDEN,
}


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = ERROR_STATUS_MAP.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JSONResponse(
        status_code=status_code,
        content={
            "data": None,
            "meta": {
                "request_id": getattr(request.state, "request_id", None),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
            "errors": [
                {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            ],
        },
    )
