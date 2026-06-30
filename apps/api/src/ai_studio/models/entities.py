from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative SQLAlchemy base class."""


class TimestampMixin:
    """Reusable timestamps for mutable entities."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(tz=UTC), onupdate=lambda: datetime.now(tz=UTC)
    )


class UserRole(str, Enum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[UserRole] = mapped_column(SqlEnum(UserRole), default=UserRole.OWNER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_subject: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)


class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    spec: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class PromptTemplate(Base, TimestampMixin):
    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class Chat(Base, TimestampMixin):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), default="New Chat")
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    chat_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("chats.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class MemoryRecord(Base, TimestampMixin):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scope: Mapped[str] = mapped_column(String(80), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    salience: Mapped[float] = mapped_column(Float, default=0.5)
    ttl_days: Mapped[int] = mapped_column(Integer, default=30)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="ingested")
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class EmbeddingMetadata(Base, TimestampMixin):
    __tablename__ = "embeddings_metadata"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_id: Mapped[str] = mapped_column(String(120), nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class AgentRun(Base, TimestampMixin):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    workflow_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("workflows.id"), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("agents.id"), nullable=True)
    status: Mapped[RunStatus] = mapped_column(SqlEnum(RunStatus), default=RunStatus.QUEUED)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    output_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str] = mapped_column(Text, default="")
    model_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class EvaluationRun(Base, TimestampMixin):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    metric_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    dataset_ref: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")


class TraceRecord(Base, TimestampMixin):
    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("agent_runs.id"), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(200), nullable=False)
    span_count: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class LogRecord(Base, TimestampMixin):
    __tablename__ = "logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(120), default="api")
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class SystemMetricSample(Base, TimestampMixin):
    __tablename__ = "system_metrics"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(tz=UTC))
    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0)
    memory_total_mb: Mapped[int] = mapped_column(Integer, default=0)
    memory_used_mb: Mapped[int] = mapped_column(Integer, default=0)
    memory_percent: Mapped[float] = mapped_column(Float, default=0.0)
    gpu_available: Mapped[bool] = mapped_column(Boolean, default=False)
    gpu_name: Mapped[str] = mapped_column(String(200), default="")
    gpu_total_mb: Mapped[int] = mapped_column(Integer, default=0)
    gpu_used_mb: Mapped[int] = mapped_column(Integer, default=0)
    gpu_free_mb: Mapped[int] = mapped_column(Integer, default=0)
    gpu_utilization_percent: Mapped[float] = mapped_column(Float, default=0.0)
    gpu_memory_utilization_percent: Mapped[float] = mapped_column(Float, default=0.0)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class Experiment(Base, TimestampMixin):
    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    results: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class UserSetting(Base, TimestampMixin):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    actor_user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(120), nullable=False)
    target_id: Mapped[str] = mapped_column(String(120), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
