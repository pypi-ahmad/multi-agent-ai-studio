from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkflowNode(BaseModel):
    id: str
    kind: Literal[
        "supervisor",
        "agent",
        "tool",
        "condition",
        "loop",
        "human_approval",
        "checkpoint",
    ]
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    source: str
    target: str
    condition: str | None = None


class WorkflowSpec(BaseModel):
    version: int = 1
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    entrypoint: str


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    spec: WorkflowSpec


class WorkflowUpdate(WorkflowCreate):
    pass


class WorkflowValidationRequest(BaseModel):
    spec: WorkflowSpec


class WorkflowValidationResult(BaseModel):
    node_count: int
    edge_count: int
    entrypoint: str
    reachable_node_count: int
    warnings: list[str] = Field(default_factory=list)


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    version: int
    spec: WorkflowSpec
    created_at: datetime
    updated_at: datetime
