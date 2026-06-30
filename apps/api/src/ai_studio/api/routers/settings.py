from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, rate_limit, read_access_guard, write_access_guard
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import User, UserSetting

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingUpsert(BaseModel):
    value: dict[str, Any] = Field(default_factory=dict)


class SettingRead(BaseModel):
    id: str
    owner_id: str
    key: str
    value: dict[str, Any]
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[SettingRead])
async def list_settings(
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("settings.list")),
) -> list[SettingRead]:
    result = await session.execute(
        select(UserSetting).where(UserSetting.owner_id == user.id).order_by(UserSetting.key.asc())
    )
    return [SettingRead.model_validate(item, from_attributes=True) for item in result.scalars().all()]


@router.get("/{key}", response_model=SettingRead)
async def get_setting(
    key: str,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("settings.get")),
) -> SettingRead:
    result = await session.execute(
        select(UserSetting).where(UserSetting.owner_id == user.id, UserSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    if setting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found")
    return SettingRead.model_validate(setting, from_attributes=True)


@router.put("/{key}", response_model=SettingRead)
async def upsert_setting(
    key: str,
    payload: SettingUpsert,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(write_access_guard()),
    _limit: None = Depends(rate_limit("settings.upsert")),
) -> SettingRead:
    result = await session.execute(
        select(UserSetting).where(UserSetting.owner_id == user.id, UserSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = UserSetting(owner_id=user.id, key=key, value=payload.value)
        session.add(setting)
    else:
        setting.value = payload.value
        session.add(setting)

    await session.commit()
    await session.refresh(setting)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="settings.upsert",
        target_type="setting",
        target_id=setting.id,
        details={"key": key},
        commit=True,
    )
    return SettingRead.model_validate(setting, from_attributes=True)
