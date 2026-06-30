from __future__ import annotations

from pydantic import BaseModel, Field


class AgentSpecV1(BaseModel):
    name: str
    role: str
    system_prompt: str
    tools: list[str] = Field(default_factory=list)
    model_policy: dict[str, object] = Field(default_factory=dict)
    memory_policy: dict[str, object] = Field(default_factory=dict)
