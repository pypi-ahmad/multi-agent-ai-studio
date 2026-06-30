from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import User
from ai_studio.schemas.memory import (
    MemoryCreate,
    MemoryForgetRequest,
    MemoryRead,
    MemorySummaryRequest,
    MemorySummaryResponse,
    MemoryType,
    MemoryUpdate,
)
from ai_studio.services.memory_service import MemoryService
from ai_studio.state import get_app_state

router = APIRouter(prefix="/memory", tags=["memory"])
service = MemoryService()


@router.get("", response_model=list[MemoryRead])
async def list_memories(
    scope: str | None = Query(default=None),
    memory_type: MemoryType | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("memory.list")),
) -> list[MemoryRead]:
    await service.prune_expired(session, user.id)
    records = await service.list(session, user.id, scope=scope, memory_type=memory_type, limit=limit)
    return [MemoryRead.model_validate(record) for record in records]


@router.get("/{memory_id}", response_model=MemoryRead)
async def get_memory(
    memory_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("memory.get")),
) -> MemoryRead:
    record = await service.get(session, user.id, memory_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return MemoryRead.model_validate(record)


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def create_memory(
    payload: MemoryCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("memory.create")),
) -> MemoryRead:
    record = await service.create(session, user.id, payload)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="memory.create",
        target_type="memory",
        target_id=record.id,
        details={"scope": record.scope, "memory_type": record.memory_type},
        commit=True,
    )
    return MemoryRead.model_validate(record)


@router.patch("/{memory_id}", response_model=MemoryRead)
async def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("memory.update")),
) -> MemoryRead:
    record = await service.get(session, user.id, memory_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    updated = await service.update(session, record, payload)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="memory.update",
        target_type="memory",
        target_id=updated.id,
        details={"scope": updated.scope, "memory_type": updated.memory_type},
        commit=True,
    )
    return MemoryRead.model_validate(updated)


@router.post("/summary", response_model=MemorySummaryResponse)
async def summarize_memories(
    payload: MemorySummaryRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("memory.summary")),
) -> MemorySummaryResponse:
    records = await service.list(
        session,
        user.id,
        scope=payload.scope,
        memory_type=payload.memory_type,
        limit=payload.limit,
    )
    if not records:
        return MemorySummaryResponse(
            count=0,
            scope=payload.scope,
            memory_type=payload.memory_type,
            summary="No memories found for given filters.",
            ids=[],
        )

    lines = [f"[{item.memory_type}|{item.scope}|{item.salience:.2f}] {item.content}" for item in records]
    prompt = (
        "Summarize these memory entries into short operator-ready notes. "
        "Return max 8 bullet points including conflicts and next-action hints.\n\n"
        + "\n".join(lines)
    )

    app_state = get_app_state()
    try:
        model = await app_state.model_router.pick("summarization")
        summary = await app_state.ollama_client.generate(
            model,
            prompt,
            options={"num_predict": 180, "temperature": 0.1},
        )
    except Exception:  # noqa: BLE001
        summary = "\n".join(f"- {item.content}" for item in records[:8])

    return MemorySummaryResponse(
        count=len(records),
        scope=payload.scope,
        memory_type=payload.memory_type,
        summary=summary,
        ids=[item.id for item in records],
    )


@router.post("/forget")
async def forget_memories(
    payload: MemoryForgetRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("memory.forget")),
) -> dict[str, int]:
    deleted = await service.forget(
        session,
        user.id,
        scope=payload.scope,
        memory_type=payload.memory_type,
        min_salience=payload.min_salience,
    )
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="memory.forget",
        target_type="memory",
        target_id=user.id,
        details={
            "scope": payload.scope,
            "memory_type": payload.memory_type,
            "min_salience": payload.min_salience,
            "deleted": deleted,
        },
        commit=True,
    )
    return {"deleted": deleted}


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("memory.delete")),
) -> None:
    deleted = await service.delete(session, user.id, memory_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="memory.delete",
        target_type="memory",
        target_id=memory_id,
        details={},
        commit=True,
    )
