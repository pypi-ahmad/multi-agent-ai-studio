from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryType = Literal[
    "short_term",
    "long_term",
    "semantic",
    "episodic",
    "conversation",
    "project",
    "agent",
]


class MemoryCreate(BaseModel):
    memory_type: MemoryType
    scope: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1)
    salience: float = Field(default=0.5, ge=0.0, le=1.0)
    ttl_days: int = Field(default=30, ge=1, le=3650)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryRead(MemoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="meta")
    created_at: datetime
    updated_at: datetime


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    salience: float | None = Field(default=None, ge=0.0, le=1.0)
    ttl_days: int | None = Field(default=None, ge=1, le=3650)
    metadata: dict[str, Any] | None = None


class MemorySummaryRequest(BaseModel):
    scope: str | None = Field(default=None, min_length=1, max_length=80)
    memory_type: MemoryType | None = None
    limit: int = Field(default=30, ge=1, le=300)


class MemorySummaryResponse(BaseModel):
    count: int
    scope: str | None = None
    memory_type: MemoryType | None = None
    summary: str
    ids: list[str] = Field(default_factory=list)


class MemoryForgetRequest(BaseModel):
    scope: str | None = Field(default=None, min_length=1, max_length=80)
    memory_type: MemoryType | None = None
    min_salience: float | None = Field(default=None, ge=0.0, le=1.0)
