from __future__ import annotations

from statistics import mean

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import EvaluationRun, User
from ai_studio.schemas.evaluation import CostEstimate, EvaluationCreate, EvaluationRead
from ai_studio.services.cost_estimator import CostEstimator

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
estimator = CostEstimator()


@router.get("", response_model=list[EvaluationRead])
async def list_evaluations(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("evaluation.list")),
) -> list[EvaluationRead]:
    result = await session.execute(
        select(EvaluationRun).where(EvaluationRun.owner_id == user.id).order_by(EvaluationRun.created_at.desc())
    )
    return [EvaluationRead.model_validate(item) for item in result.scalars().all()]


@router.get("/summary")
async def evaluation_summary(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("evaluation.summary")),
) -> dict[str, object]:
    result = await session.execute(
        select(EvaluationRun).where(EvaluationRun.owner_id == user.id).order_by(EvaluationRun.created_at.asc())
    )
    evaluations = result.scalars().all()

    metric_map: dict[str, list[float]] = {}
    all_values: list[float] = []
    for item in evaluations:
        for key, value in item.metric_scores.items():
            value_f = float(value)
            metric_map.setdefault(key, []).append(value_f)
            all_values.append(value_f)

    return {
        "count": len(evaluations),
        "avg_score": round(mean(all_values), 4) if all_values else 0.0,
        "best_score": round(max(all_values), 4) if all_values else 0.0,
        "metrics": {key: round(mean(values), 4) for key, values in metric_map.items()},
        "timeline": [
            {
                "id": item.id,
                "name": item.name,
                "created_at": item.created_at,
                "metric_scores": item.metric_scores,
            }
            for item in evaluations
        ],
    }


@router.post("", response_model=EvaluationRead, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    payload: EvaluationCreate,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("evaluation.create")),
) -> EvaluationRead:
    evaluation = EvaluationRun(
        owner_id=user.id,
        name=payload.name,
        dataset_ref=payload.dataset_ref,
        metric_scores=payload.metric_scores,
        notes=payload.notes,
    )
    session.add(evaluation)
    await session.commit()
    await session.refresh(evaluation)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="evaluation.create",
        target_type="evaluation",
        target_id=evaluation.id,
        details={"name": evaluation.name},
        commit=True,
    )
    return EvaluationRead.model_validate(evaluation)


@router.post("/estimate-cost", response_model=CostEstimate)
async def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    latency_ms: float,
    gpu_seconds: float,
    cpu_seconds: float,
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("evaluation.estimate_cost")),
) -> CostEstimate:
    return estimator.estimate(prompt_tokens, completion_tokens, latency_ms, gpu_seconds, cpu_seconds)


@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluation(
    evaluation_id: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("evaluation.delete")),
) -> None:
    result = await session.execute(
        delete(EvaluationRun).where(EvaluationRun.id == evaluation_id, EvaluationRun.owner_id == user.id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    await session.commit()
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="evaluation.delete",
        target_type="evaluation",
        target_id=evaluation_id,
        details={},
        commit=True,
    )
