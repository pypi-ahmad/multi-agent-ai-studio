from __future__ import annotations

from pydantic import BaseModel, Field


class WorkflowNodeV1(BaseModel):
    id: str
    kind: str
    config: dict[str, object] = Field(default_factory=dict)


class WorkflowEdgeV1(BaseModel):
    source: str
    target: str
    condition: str | None = None


class WorkflowSpecV1(BaseModel):
    version: int = 1
    entrypoint: str
    nodes: list[WorkflowNodeV1]
    edges: list[WorkflowEdgeV1]
