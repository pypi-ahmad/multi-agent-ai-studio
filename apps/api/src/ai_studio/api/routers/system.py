from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import rate_limit, read_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import SystemMetricSample, User
from ai_studio.state import get_app_state

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
async def health(
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("system.health")),
) -> dict[str, object]:
    app_state = get_app_state()
    metrics = await app_state.system_metrics.snapshot()
    ollama_ok, ollama_error = await app_state.ollama_client.health()

    model_status = "ok"
    if not app_state.model_router.snapshot().get("models"):
        model_status = "degraded"

    status = "ok" if ollama_ok and model_status == "ok" else "degraded"
    return {
        "status": status,
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "services": {
            "database": "up",
            "redis": "up",
            "qdrant": "up",
            "ollama": "up" if ollama_ok else "down",
            "model_router": model_status,
        },
        "errors": {
            "ollama": ollama_error,
            "model_router": app_state.model_router.snapshot().get("last_error"),
        },
        "metrics": metrics,
    }


@router.get("/models")
async def models(
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("system.models")),
) -> dict[str, object]:
    app_state = get_app_state()
    try:
        await asyncio.wait_for(app_state.model_router.refresh(), timeout=10)
        snapshot = app_state.model_router.snapshot()
        count_raw = snapshot.get("count", 0)
        count = count_raw if isinstance(count_raw, int) else 0
        status = "ok" if count > 0 else "degraded"
        return {"status": status, **snapshot}
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "degraded",
            "error": str(exc),
            **app_state.model_router.snapshot(),
        }


@router.get("/metrics/timeseries")
async def metrics_timeseries(
    minutes: int = Query(default=60, ge=5, le=1440),
    limit: int = Query(default=720, ge=10, le=5000),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("system.metrics_timeseries")),
) -> dict[str, object]:
    since = datetime.now(tz=UTC) - timedelta(minutes=minutes)
    result = await session.execute(
        select(SystemMetricSample)
        .where(SystemMetricSample.recorded_at >= since)
        .order_by(SystemMetricSample.recorded_at.asc())
        .limit(limit)
    )
    samples = result.scalars().all()

    return {
        "minutes": minutes,
        "count": len(samples),
        "series": [
            {
                "id": item.id,
                "recorded_at": item.recorded_at,
                "cpu_percent": item.cpu_percent,
                "memory_total_mb": item.memory_total_mb,
                "memory_used_mb": item.memory_used_mb,
                "memory_percent": item.memory_percent,
                "gpu_available": item.gpu_available,
                "gpu_name": item.gpu_name,
                "gpu_total_mb": item.gpu_total_mb,
                "gpu_used_mb": item.gpu_used_mb,
                "gpu_free_mb": item.gpu_free_mb,
                "gpu_utilization_percent": item.gpu_utilization_percent,
                "gpu_memory_utilization_percent": item.gpu_memory_utilization_percent,
                "metadata": item.meta,
            }
            for item in samples
        ],
    }
