from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ai_studio.api.deps import rate_limit, read_access_guard, write_access_guard
from ai_studio.models.entities import User
from ai_studio.services.model_router import TaskType
from ai_studio.state import get_app_state

router = APIRouter(prefix="/models", tags=["models"])


class RoutingRulePayload(BaseModel):
    task: TaskType
    model_name: str


class RoutingRuleDeletePayload(BaseModel):
    task: TaskType


@router.get("/snapshot")
async def model_snapshot(
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("models.snapshot")),
) -> dict[str, object]:
    state = get_app_state()
    return state.model_router.snapshot()


@router.post("/refresh")
async def model_refresh(
    _user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("models.refresh", rpm=30)),
) -> dict[str, object]:
    state = get_app_state()
    try:
        await state.model_router.refresh()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Model refresh failed: {exc}") from exc
    return state.model_router.snapshot()


@router.post("/routing-rules")
async def set_routing_rule(
    payload: RoutingRulePayload,
    _user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("models.set_rule")),
) -> dict[str, object]:
    state = get_app_state()
    snapshot = state.model_router.snapshot()
    models = snapshot.get("models", [])
    model_names = {item.get("model_name") for item in models if isinstance(item, dict)}
    if payload.model_name not in model_names:
        raise HTTPException(status_code=400, detail=f"Unknown model '{payload.model_name}'")

    state.model_router.set_custom_rule(payload.task, payload.model_name)
    return {"status": "ok", "snapshot": state.model_router.snapshot()}


@router.delete("/routing-rules")
async def clear_routing_rule(
    payload: RoutingRuleDeletePayload,
    _user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("models.clear_rule")),
) -> dict[str, object]:
    state = get_app_state()
    state.model_router.clear_custom_rule(payload.task)
    return {"status": "ok", "snapshot": state.model_router.snapshot()}
