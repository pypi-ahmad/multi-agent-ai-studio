from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import Experiment, User

router = APIRouter(prefix="/experiments", tags=["experiments"])


class ExperimentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    config: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=dict)


class ExperimentRead(ExperimentCreate):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[ExperimentRead])
async def list_experiments(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("experiments.list")),
) -> list[ExperimentRead]:
    result = await session.execute(
        select(Experiment).where(Experiment.owner_id == user.id).order_by(Experiment.updated_at.desc())
    )
    rows = result.scalars().all()
    return [ExperimentRead.model_validate(item, from_attributes=True) for item in rows]


@router.post("", response_model=ExperimentRead, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    payload: ExperimentCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("experiments.create")),
) -> ExperimentRead:
    record = Experiment(owner_id=user.id, name=payload.name, config=payload.config, results=payload.results)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="experiments.create",
        target_type="experiment",
        target_id=record.id,
        details={"name": record.name},
        commit=True,
    )
    return ExperimentRead.model_validate(record, from_attributes=True)


@router.patch("/{experiment_id}", response_model=ExperimentRead)
async def update_experiment(
    experiment_id: str,
    payload: ExperimentCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("experiments.update")),
) -> ExperimentRead:
    result = await session.execute(
        select(Experiment).where(Experiment.id == experiment_id, Experiment.owner_id == user.id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")

    record.name = payload.name
    record.config = payload.config
    record.results = payload.results
    session.add(record)
    await session.commit()
    await session.refresh(record)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="experiments.update",
        target_type="experiment",
        target_id=record.id,
        details={"name": record.name},
        commit=True,
    )
    return ExperimentRead.model_validate(record, from_attributes=True)


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experiment(
    experiment_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("experiments.delete")),
) -> None:
    result = await session.execute(
        delete(Experiment).where(Experiment.id == experiment_id, Experiment.owner_id == user.id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    await session.commit()
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="experiments.delete",
        target_type="experiment",
        target_id=experiment_id,
        details={},
        commit=True,
    )
