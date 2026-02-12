from fastapi import Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    return Response(
        content='{"error": "Rate limit exceeded"}',
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        media_type="application/json"
    )
