from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    mime_type: str
    source_uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRead(DocumentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="meta")
    status: str
    created_at: datetime
    updated_at: datetime


class ConnectorIngestRequest(BaseModel):
    connector: Literal["github", "web"]
    source_uri: str = Field(min_length=4)
    name: str = Field(min_length=1, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)


class ConnectorIngestResponse(BaseModel):
    document: DocumentRead
    chunks_indexed: int


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    mode: Literal["semantic", "keyword", "hybrid"] = "hybrid"
    rerank: bool = True
    candidate_pool: int = Field(default=30, ge=5, le=200)
    filters: dict[str, Any] = Field(default_factory=dict)


class RetrievalHit(BaseModel):
    document_id: str
    chunk_id: str
    score: float
    text: str
    highlights: list[str] = Field(default_factory=list)
    metadata: dict[str, Any]


class RetrievalResponse(BaseModel):
    query: str
    mode: Literal["semantic", "keyword", "hybrid"]
    hits: list[RetrievalHit]
