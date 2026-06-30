"""Initial schema

Revision ID: 20260627_0001
Revises:
Create Date: 2026-06-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260627_0001"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = sa.Enum("OWNER", "EDITOR", "VIEWER", name="userrole", create_type=False)
run_status_enum = sa.Enum("QUEUED", "RUNNING", "FAILED", "COMPLETED", name="runstatus", create_type=False)


def upgrade() -> None:
    user_role_enum.create(op.get_bind(), checkfirst=True)
    run_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("role", user_role_enum, nullable=False, server_default="OWNER"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("oauth_provider", sa.String(length=50), nullable=True),
        sa.Column("oauth_subject", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_template", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "workflows",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("spec", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "prompts",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "chats",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False, server_default="New Chat"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("chat_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("chats.id"), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("token_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "memories",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("memory_type", sa.String(length=40), nullable=False),
        sa.Column("scope", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("salience", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("ttl_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="ingested"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "embeddings_metadata",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("vector_id", sa.String(length=120), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("workflows.id"), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("status", run_status_enum, nullable=False, server_default="QUEUED"),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_usage", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("metric_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("dataset_ref", sa.Text(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "traces",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("trace_id", sa.String(length=200), nullable=False),
        sa.Column("span_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False, server_default="api"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "settings",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=120), nullable=False),
        sa.Column("target_id", sa.String(length=120), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("idx_agents_owner", "agents", ["owner_id"])
    op.create_index("idx_workflows_owner", "workflows", ["owner_id"])
    op.create_index("idx_runs_owner", "agent_runs", ["owner_id"])
    op.create_index("idx_runs_status", "agent_runs", ["status"])
    op.create_index("idx_memories_owner_scope", "memories", ["owner_id", "scope"])
    op.create_index("idx_documents_owner", "documents", ["owner_id"])
    op.create_index("idx_evaluations_owner", "evaluations", ["owner_id"])
    op.create_index("idx_traces_run", "traces", ["run_id"])
    op.create_index("idx_settings_owner_key", "settings", ["owner_id", "key"])
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_index("idx_audit_logs_action", table_name="audit_logs")
    op.drop_index("idx_settings_owner_key", table_name="settings")
    op.drop_index("idx_traces_run", table_name="traces")
    op.drop_index("idx_evaluations_owner", table_name="evaluations")
    op.drop_index("idx_documents_owner", table_name="documents")
    op.drop_index("idx_memories_owner_scope", table_name="memories")
    op.drop_index("idx_runs_status", table_name="agent_runs")
    op.drop_index("idx_runs_owner", table_name="agent_runs")
    op.drop_index("idx_workflows_owner", table_name="workflows")
    op.drop_index("idx_agents_owner", table_name="agents")

    for table_name in [
        "audit_logs",
        "settings",
        "experiments",
        "logs",
        "traces",
        "evaluations",
        "agent_runs",
        "embeddings_metadata",
        "documents",
        "memories",
        "chat_messages",
        "chats",
        "prompts",
        "workflows",
        "agents",
        "users",
    ]:
        op.drop_table(table_name)

    run_status_enum.drop(op.get_bind(), checkfirst=True)
    user_role_enum.drop(op.get_bind(), checkfirst=True)
