from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import LogRecord, User

router = APIRouter(prefix="/logs", tags=["logs"])


class LogCreate(BaseModel):
    level: str = Field(min_length=2, max_length=20)
    message: str = Field(min_length=1)
    source: str = Field(default="api", max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LogRead(BaseModel):
    id: str
    level: str
    message: str
    source: str
    metadata: dict[str, Any]
    created_at: datetime


@router.get("", response_model=list[LogRead])
async def list_logs(
    level: str | None = Query(default=None),
    source: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("logs.list")),
) -> list[LogRead]:
    stmt = select(LogRecord)
    if level:
        stmt = stmt.where(LogRecord.level == level)
    if source:
        stmt = stmt.where(LogRecord.source == source)
    stmt = stmt.order_by(LogRecord.created_at.desc()).limit(limit)

    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        LogRead(
            id=item.id,
            level=item.level,
            message=item.message,
            source=item.source,
            metadata=item.meta,
            created_at=item.created_at,
        )
        for item in rows
    ]


@router.post("", response_model=LogRead, status_code=status.HTTP_201_CREATED)
async def create_log(
    payload: LogCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("logs.create")),
) -> LogRead:
    record = LogRecord(level=payload.level.upper(), message=payload.message, source=payload.source, meta=payload.metadata)
    session.add(record)
    await session.commit()
    await session.refresh(record)

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="logs.create",
        target_type="log",
        target_id=record.id,
        details={"level": record.level, "source": record.source},
        commit=True,
    )

    return LogRead(
        id=record.id,
        level=record.level,
        message=record.message,
        source=record.source,
        metadata=record.meta,
        created_at=record.created_at,
    )
