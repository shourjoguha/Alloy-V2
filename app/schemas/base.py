from datetime import datetime
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')

class ResponseMeta(BaseModel):
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    warnings: list[str] = Field(default_factory=list)

class APIError(BaseModel):
    code: str
    message: str
    details: dict | None = None

class APIResponse(BaseModel, Generic[T]):
    data: T | None = None
    meta: ResponseMeta | None = None
    errors: list[APIError] = Field(default_factory=list)

class ListResponseWrapper(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    has_next: bool = False
    has_prev: bool = False
    total_pages: int = 1
    current_page: int = 1
    filters_applied: dict | None = None
