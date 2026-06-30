from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import Agent, User

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class TemplateRead(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PublishTemplateRequest(BaseModel):
    agent_id: str


class ImportTemplateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)


@router.get("/templates", response_model=list[TemplateRead])
async def list_templates(
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("marketplace.templates.list")),
) -> list[TemplateRead]:
    result = await session.execute(select(Agent).where(Agent.is_template.is_(True)).order_by(Agent.updated_at.desc()))
    return [TemplateRead.model_validate(item, from_attributes=True) for item in result.scalars().all()]


@router.post("/templates/publish", response_model=TemplateRead)
async def publish_template(
    payload: PublishTemplateRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("marketplace.templates.publish")),
) -> TemplateRead:
    result = await session.execute(
        select(Agent).where(Agent.id == payload.agent_id, Agent.owner_id == user.id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    agent.is_template = True
    session.add(agent)
    await session.commit()
    await session.refresh(agent)

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="marketplace.template.publish",
        target_type="agent",
        target_id=agent.id,
        details={"name": agent.name},
        commit=True,
    )
    return TemplateRead.model_validate(agent, from_attributes=True)


@router.post("/templates/{template_id}/import", response_model=TemplateRead, status_code=status.HTTP_201_CREATED)
async def import_template(
    template_id: str,
    payload: ImportTemplateRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("marketplace.templates.import")),
) -> TemplateRead:
    result = await session.execute(select(Agent).where(Agent.id == template_id, Agent.is_template.is_(True)))
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    imported = Agent(
        owner_id=user.id,
        name=payload.name or f"{template.name} (Imported)",
        description=template.description,
        config=template.config,
        is_template=False,
    )
    session.add(imported)
    await session.commit()
    await session.refresh(imported)

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="marketplace.template.import",
        target_type="agent",
        target_id=imported.id,
        details={"template_id": template_id},
        commit=True,
    )
    return TemplateRead.model_validate(imported, from_attributes=True)
