from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class StudioBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(StudioBaseModel):
    error: str
    details: dict[str, Any] | None = None


class Pagination(StudioBaseModel):
    total: int
    limit: int
    offset: int


class HealthResponse(StudioBaseModel):
    status: str
    timestamp: datetime
    services: dict[str, str]
