from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    dataset_ref: str
    metric_scores: dict[str, float] = Field(default_factory=dict)
    notes: str = ""


class EvaluationRead(EvaluationCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


class CostEstimate(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    gpu_seconds: float
    cpu_seconds: float
    cloud_equivalent_usd: float
