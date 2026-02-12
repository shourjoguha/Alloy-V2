from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NIN = "nin"
    LIKE = "like"


class FilterExpression(BaseModel):
    field: str
    operator: FilterOperator
    value: Any


class FilterRequest(BaseModel):
    filters: list[FilterExpression] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
