from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import AgentRun, TraceRecord, User

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=list[dict[str, object]])
async def list_traces(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("traces.list")),
) -> list[dict[str, object]]:
    result = await session.execute(
        select(TraceRecord, AgentRun)
        .join(AgentRun, AgentRun.id == TraceRecord.run_id)
        .where(AgentRun.owner_id == user.id)
        .order_by(TraceRecord.created_at.desc())
        .limit(200)
    )
    rows = result.all()
    return [
        {
            "id": trace.id,
            "run_id": trace.run_id,
            "run_status": run.status.value if hasattr(run.status, "value") else str(run.status),
            "trace_id": trace.trace_id,
            "span_count": trace.span_count,
            "metadata": trace.meta,
            "created_at": trace.created_at,
        }
        for trace, run in rows
    ]


@router.get("/{trace_id}", response_model=dict[str, object])
async def get_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("traces.get")),
) -> dict[str, object]:
    result = await session.execute(
        select(TraceRecord, AgentRun)
        .join(AgentRun, AgentRun.id == TraceRecord.run_id)
        .where(TraceRecord.id == trace_id, AgentRun.owner_id == user.id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    trace, run = row
    return {
        "id": trace.id,
        "trace_id": trace.trace_id,
        "run_id": trace.run_id,
        "run_status": run.status.value if hasattr(run.status, "value") else str(run.status),
        "span_count": trace.span_count,
        "created_at": trace.created_at,
        "updated_at": trace.updated_at,
        "metadata": trace.meta,
        "run": {
            "input_payload": run.input_payload,
            "output_payload": run.output_payload,
            "model_usage": run.model_usage,
            "error_message": run.error_message,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        },
    }


@router.get("/{trace_id}/timeline", response_model=list[dict[str, object]])
async def get_trace_timeline(
    trace_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("traces.timeline")),
) -> list[dict[str, object]]:
    result = await session.execute(
        select(TraceRecord, AgentRun)
        .join(AgentRun, AgentRun.id == TraceRecord.run_id)
        .where(TraceRecord.id == trace_id, AgentRun.owner_id == user.id)
    )
    row = result.first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    trace, _run = row
    timeline = trace.meta.get("timeline", []) if isinstance(trace.meta, dict) else []
    return [
        {
            "index": index,
            "stage": item.get("stage", ""),
            "latency_ms": item.get("latency_ms", 0),
            "model": item.get("model", ""),
        }
        for index, item in enumerate(timeline)
    ]


@router.delete("/{trace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("traces.delete")),
) -> None:
    result = await session.execute(
        delete(TraceRecord)
        .where(TraceRecord.id == trace_id)
        .where(TraceRecord.run_id.in_(select(AgentRun.id).where(AgentRun.owner_id == user.id)))
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")
    await session.commit()
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="traces.delete",
        target_type="trace",
        target_id=trace_id,
        details={},
        commit=True,
    )
