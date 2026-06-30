from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import User, Workflow
from ai_studio.schemas.workflow import (
    WorkflowCreate,
    WorkflowRead,
    WorkflowUpdate,
    WorkflowValidationRequest,
    WorkflowValidationResult,
)
from ai_studio.services.workflow_compiler import WorkflowCompiler

router = APIRouter(prefix="/workflows", tags=["workflows"])
compiler = WorkflowCompiler()


@router.get("", response_model=list[WorkflowRead])
async def list_workflows(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("workflows.list")),
) -> list[WorkflowRead]:
    result = await session.execute(
        select(Workflow).where(Workflow.owner_id == user.id).order_by(Workflow.updated_at.desc())
    )
    return [WorkflowRead.model_validate(item) for item in result.scalars().all()]


@router.post("/validate", response_model=WorkflowValidationResult)
async def validate_workflow(
    payload: WorkflowValidationRequest,
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("workflows.validate")),
) -> WorkflowValidationResult:
    compiled = compiler.compile(payload.spec)
    return WorkflowValidationResult(
        node_count=compiled.node_count,
        edge_count=compiled.edge_count,
        entrypoint=compiled.entrypoint,
        reachable_node_count=compiled.reachable_node_count,
        warnings=compiled.warnings,
    )


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("workflows.create")),
) -> WorkflowRead:
    compiler.compile(payload.spec)
    workflow = Workflow(owner_id=user.id, name=payload.name, version=payload.spec.version, spec=payload.spec.model_dump())
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="workflows.create",
        target_type="workflow",
        target_id=workflow.id,
        details={"name": workflow.name},
        commit=True,
    )
    return WorkflowRead.model_validate(workflow)


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("workflows.get")),
) -> WorkflowRead:
    result = await session.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.owner_id == user.id))
    workflow = result.scalar_one_or_none()
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return WorkflowRead.model_validate(workflow)


@router.put("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("workflows.update")),
) -> WorkflowRead:
    compiler.compile(payload.spec)
    result = await session.execute(select(Workflow).where(Workflow.id == workflow_id, Workflow.owner_id == user.id))
    workflow = result.scalar_one_or_none()
    if workflow is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    workflow.name = payload.name
    workflow.version = payload.spec.version
    workflow.spec = payload.spec.model_dump()
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="workflows.update",
        target_type="workflow",
        target_id=workflow.id,
        details={"name": workflow.name, "version": workflow.version},
        commit=True,
    )
    return WorkflowRead.model_validate(workflow)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("workflows.delete")),
) -> None:
    result = await session.execute(
        delete(Workflow).where(Workflow.id == workflow_id, Workflow.owner_id == user.id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    await session.commit()
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="workflows.delete",
        target_type="workflow",
        target_id=workflow_id,
        details={},
        commit=True,
    )
