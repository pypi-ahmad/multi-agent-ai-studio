"""Add system metrics timeseries table

Revision ID: 20260628_0002
Revises: 20260627_0001
Create Date: 2026-06-28
"""

from __future__ import annotations

from alembic import op

revision = "20260628_0002"
down_revision = "20260627_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS system_metrics (
            id UUID PRIMARY KEY,
            recorded_at TIMESTAMPTZ NOT NULL,
            cpu_percent DOUBLE PRECISION NOT NULL DEFAULT 0,
            memory_total_mb INTEGER NOT NULL DEFAULT 0,
            memory_used_mb INTEGER NOT NULL DEFAULT 0,
            memory_percent DOUBLE PRECISION NOT NULL DEFAULT 0,
            gpu_available BOOLEAN NOT NULL DEFAULT FALSE,
            gpu_name VARCHAR(200) NOT NULL DEFAULT '',
            gpu_total_mb INTEGER NOT NULL DEFAULT 0,
            gpu_used_mb INTEGER NOT NULL DEFAULT 0,
            gpu_free_mb INTEGER NOT NULL DEFAULT 0,
            gpu_utilization_percent DOUBLE PRECISION NOT NULL DEFAULT 0,
            gpu_memory_utilization_percent DOUBLE PRECISION NOT NULL DEFAULT 0,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS system_metrics")
