from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import Agent, User
from ai_studio.schemas.agent import AgentCreate, AgentRead

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentRead])
async def list_agents(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("agents.list")),
) -> list[AgentRead]:
    result = await session.execute(select(Agent).where(Agent.owner_id == user.id).order_by(Agent.updated_at.desc()))
    return [AgentRead.model_validate(item) for item in result.scalars().all()]


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("agents.create")),
) -> AgentRead:
    agent = Agent(
        owner_id=user.id,
        name=payload.name,
        description=payload.description,
        config=payload.config,
        is_template=payload.is_template,
    )
    session.add(agent)
    await session.commit()
    await session.refresh(agent)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="agents.create",
        target_type="agent",
        target_id=agent.id,
        details={"name": agent.name},
        commit=True,
    )
    return AgentRead.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("agents.delete")),
) -> None:
    result = await session.execute(delete(Agent).where(Agent.id == agent_id, Agent.owner_id == user.id))
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    await session.commit()
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="agents.delete",
        target_type="agent",
        target_id=agent_id,
        details={},
        commit=True,
    )
