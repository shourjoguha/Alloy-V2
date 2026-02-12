from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar('T')

class PaginationParams(BaseModel):
    cursor: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    direction: str = Field(default="next", pattern="^(next|prev)$")

class PaginatedResult(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    items: list[T]
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    has_more: bool = False
