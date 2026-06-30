from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.models.entities import MemoryRecord
from ai_studio.schemas.memory import MemoryCreate, MemoryType, MemoryUpdate


class MemoryService:
    """Persistence service for multi-layer memory records."""

    @staticmethod
    async def create(session: AsyncSession, owner_id: str, payload: MemoryCreate) -> MemoryRecord:
        record = MemoryRecord(
            owner_id=owner_id,
            memory_type=payload.memory_type,
            scope=payload.scope,
            content=payload.content,
            salience=payload.salience,
            ttl_days=payload.ttl_days,
            meta=payload.metadata,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    @staticmethod
    async def get(session: AsyncSession, owner_id: str, memory_id: str) -> MemoryRecord | None:
        stmt = select(MemoryRecord).where(MemoryRecord.owner_id == owner_id, MemoryRecord.id == memory_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        session: AsyncSession,
        owner_id: str,
        scope: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 200,
    ) -> list[MemoryRecord]:
        stmt = select(MemoryRecord).where(MemoryRecord.owner_id == owner_id)
        if scope:
            stmt = stmt.where(MemoryRecord.scope == scope)
        if memory_type:
            stmt = stmt.where(MemoryRecord.memory_type == memory_type)
        stmt = stmt.order_by(MemoryRecord.salience.desc(), MemoryRecord.updated_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update(session: AsyncSession, record: MemoryRecord, payload: MemoryUpdate) -> MemoryRecord:
        if payload.content is not None:
            record.content = payload.content
        if payload.salience is not None:
            record.salience = payload.salience
        if payload.ttl_days is not None:
            record.ttl_days = payload.ttl_days
        if payload.metadata is not None:
            record.meta = payload.metadata

        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    @staticmethod
    async def delete(session: AsyncSession, owner_id: str, memory_id: str) -> int:
        result = await session.execute(
            delete(MemoryRecord).where(MemoryRecord.owner_id == owner_id, MemoryRecord.id == memory_id)
        )
        await session.commit()
        return int(result.rowcount or 0)

    @staticmethod
    async def forget(
        session: AsyncSession,
        owner_id: str,
        scope: str | None = None,
        memory_type: MemoryType | None = None,
        min_salience: float | None = None,
    ) -> int:
        stmt = delete(MemoryRecord).where(MemoryRecord.owner_id == owner_id)
        if scope:
            stmt = stmt.where(MemoryRecord.scope == scope)
        if memory_type:
            stmt = stmt.where(MemoryRecord.memory_type == memory_type)
        if min_salience is not None:
            stmt = stmt.where(MemoryRecord.salience <= min_salience)

        result = await session.execute(stmt)
        await session.commit()
        return int(result.rowcount or 0)

    @staticmethod
    async def prune_expired(session: AsyncSession, owner_id: str) -> int:
        now = datetime.now(tz=UTC)
        records = await MemoryService.list(session, owner_id, limit=2000)
        expired_ids: list[str] = []
        for record in records:
            expiry = record.created_at + timedelta(days=record.ttl_days)
            if expiry < now:
                expired_ids.append(record.id)

        if not expired_ids:
            return 0

        result = await session.execute(
            delete(MemoryRecord).where(MemoryRecord.owner_id == owner_id, MemoryRecord.id.in_(expired_ids))
        )
        await session.commit()
        return int(result.rowcount or 0)
