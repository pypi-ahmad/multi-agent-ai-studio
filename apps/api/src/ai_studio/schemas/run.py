from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunCreate(BaseModel):
    workflow_id: str | None = None
    agent_id: str | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    workflow_id: str | None
    agent_id: str | None
    status: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    error_message: str
    model_usage: dict[str, Any]
    created_at: datetime
    updated_at: datetime
