from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=240)


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1)
    model: str | None = None
    agent_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    title: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="meta")
    created_at: datetime
    updated_at: datetime


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chat_id: str
    role: str
    content: str
    citations: list[dict[str, Any]]
    token_usage: dict[str, Any]
    created_at: datetime
    updated_at: datetime
