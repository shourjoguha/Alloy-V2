from pydantic import BaseModel, Field
from typing import Any
from app.models.enums import CircuitType

class CircuitTemplateBase(BaseModel):
    name: str
    description: str | None = None
    circuit_type: CircuitType
    exercises_json: list[dict[str, Any]] = []
    default_rounds: int | None = None
    default_duration_seconds: int | None = None
    tags: list[str] = []
    difficulty_tier: int = 1

class CircuitTemplateCreate(CircuitTemplateBase):
    pass

class CircuitTemplateResponse(CircuitTemplateBase):
    id: int

    class Config:
        from_attributes = True


class CircuitTemplateUpdate(BaseModel):
    exercises_json: list[dict[str, Any]]


class CircuitTemplateAdminDetail(CircuitTemplateResponse):
    raw_workout: str | None = None
