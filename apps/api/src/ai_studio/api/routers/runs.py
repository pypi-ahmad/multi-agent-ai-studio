from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import AgentRun, RunStatus, User
from ai_studio.schemas.run import RunCreate, RunRead
from ai_studio.state import get_app_state

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=list[RunRead])
async def list_runs(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("runs.list")),
) -> list[RunRead]:
    result = await session.execute(
        select(AgentRun).where(AgentRun.owner_id == user.id).order_by(AgentRun.created_at.desc())
    )
    return [RunRead.model_validate(item) for item in result.scalars().all()]


@router.post("", response_model=RunRead, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: RunCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("runs.create")),
) -> RunRead:
    run = AgentRun(
        owner_id=user.id,
        workflow_id=payload.workflow_id,
        agent_id=payload.agent_id,
        status=RunStatus.QUEUED,
        input_payload=payload.input_payload,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    app_state = get_app_state()
    await app_state.job_queue.enqueue_job("execute_agent_run", run.id)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="runs.create",
        target_type="run",
        target_id=run.id,
        details={"workflow_id": payload.workflow_id, "agent_id": payload.agent_id},
        commit=True,
    )
    return RunRead.model_validate(run)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(
    run_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("runs.delete")),
) -> None:
    result = await session.execute(delete(AgentRun).where(AgentRun.id == run_id, AgentRun.owner_id == user.id))
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    await session.commit()
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="runs.delete",
        target_type="run",
        target_id=run_id,
        details={},
        commit=True,
    )
