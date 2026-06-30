from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import Depends, Header, HTTPException, Request, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.core.config import get_settings
from ai_studio.core.security import decode_token
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import AuditLog, User, UserRole
from ai_studio.state import get_app_state


async def get_current_user(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Resolve authenticated user from bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.replace("Bearer ", "", 1).strip()
    try:
        payload = decode_token(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    stmt = select(User).where(User.id == user_id, User.is_active.is_(True))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_optional_user(
    authorization: str = Header(default=""),
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    """Resolve user when bearer token is optional (rate-limit identity)."""
    if not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "", 1).strip()
    try:
        payload = decode_token(token)
    except Exception:  # noqa: BLE001
        return None
    if payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        return None

    stmt = select(User).where(User.id == user_id, User.is_active.is_(True))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def require_roles(*roles: UserRole) -> Callable[..., Awaitable[User]]:
    """Require that user role belongs to allowed role list."""
    allowed = set(roles)

    async def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role. Required one of: {', '.join(sorted(r.value for r in allowed))}",
            )
        return user

    return _guard


def read_access_guard() -> Callable[..., Awaitable[User]]:
    return require_roles(UserRole.OWNER, UserRole.EDITOR, UserRole.VIEWER)


def write_access_guard() -> Callable[..., Awaitable[User]]:
    return require_roles(UserRole.OWNER, UserRole.EDITOR)


def owner_access_guard() -> Callable[..., Awaitable[User]]:
    return require_roles(UserRole.OWNER)


def rate_limit(scope: str, rpm: int | None = None) -> Callable[..., Awaitable[None]]:
    """Redis-backed per-minute rate limiter keyed by user or client IP."""

    async def _guard(
        request: Request,
        user: User | None = Depends(get_optional_user),
    ) -> None:
        settings = get_settings()
        threshold = rpm if rpm is not None else settings.rate_limit_rpm
        identity = user.id if user else (request.client.host if request.client else "anonymous")
        bucket = datetime.now(tz=UTC).strftime("%Y%m%d%H%M")
        key = f"ratelimit:{scope}:{identity}:{bucket}"

        try:
            redis = cast(Any, get_app_state().job_queue)
            current = int(await redis.incr(key))
            if current == 1:
                await redis.expire(key, 90)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Rate limit check skipped for scope '{}': {}", scope, exc)
            return

        if current > threshold:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for scope '{scope}'",
            )

    return _guard


async def append_audit_log(
    session: AsyncSession,
    *,
    actor_user_id: str | None,
    action: str,
    target_type: str,
    target_id: str,
    details: dict[str, Any] | None = None,
    commit: bool = False,
) -> None:
    session.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
        )
    )
    if commit:
        await session.commit()


def require_confirmation_token(x_confirm_token: str | None = Header(default=None)) -> None:
    """Require explicit confirmation header for destructive actions."""
    settings = get_settings()
    expected = f"CONFIRM-{settings.app_env.upper()}"
    if x_confirm_token != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing confirmation token header. Use X-Confirm-Token: {expected}",
        )
