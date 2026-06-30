from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    is_template: bool = False


class AgentRead(AgentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
