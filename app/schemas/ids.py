from uuid import UUID
from pydantic import BaseModel, Field


class ResourceId(BaseModel):
    """UUID v7 resource identifier."""
    value: UUID = Field(..., description="UUID v7 resource identifier")


class LegacyId(BaseModel):
    """Legacy integer ID for backward compatibility."""
    value: int = Field(..., description="Legacy integer ID")


class MigrationId(BaseModel):
    """Migration ID supporting both UUID and legacy integer IDs."""
    resource_id: ResourceId | None = None
    legacy_id: LegacyId | None = None
