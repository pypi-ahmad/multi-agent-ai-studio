from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import append_audit_log, get_current_user, rate_limit
from ai_studio.core.config import get_settings
from ai_studio.core.security import create_token, decode_token, hash_password, verify_password
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import User
from ai_studio.schemas.auth import CurrentUser, LoginRequest, LogoutRequest, RefreshTokenRequest, RegisterRequest, TokenPair
from ai_studio.state import get_app_state

router = APIRouter(prefix="/auth", tags=["auth"])


def _refresh_cache_key(jti: str) -> str:
    return f"auth:refresh:{jti}"


async def _store_refresh_token(user_id: str, token: str) -> None:
    payload = decode_token(token)
    token_type = payload.get("type")
    jti = payload.get("jti")
    exp = payload.get("exp")
    now_ts = int(datetime.now(tz=UTC).timestamp())

    if token_type != "refresh" or not isinstance(jti, str) or not isinstance(exp, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    ttl_seconds = max(exp - now_ts, 1)
    redis = get_app_state().job_queue
    await redis.set(_refresh_cache_key(jti), user_id, ex=ttl_seconds)


async def _assert_refresh_token_active(token: str, expected_user_id: str | None = None) -> dict[str, object]:
    try:
        payload = decode_token(token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")

    user_id = payload.get("sub")
    jti = payload.get("jti")
    if not isinstance(user_id, str) or not isinstance(jti, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token payload")

    if expected_user_id is not None and user_id != expected_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Refresh token user mismatch")

    redis = get_app_state().job_queue
    cached_user_id = await redis.get(_refresh_cache_key(jti))
    if isinstance(cached_user_id, bytes):
        cached_user_id = cached_user_id.decode("utf-8", errors="ignore")
    if cached_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or expired")

    return payload


async def _issue_token_pair(user_id: str) -> TokenPair:
    settings = get_settings()
    access = create_token(user_id, "access", settings.access_token_minutes)
    refresh = create_token(user_id, "refresh", settings.refresh_token_minutes)
    await _store_refresh_token(user_id, refresh)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=TokenPair, dependencies=[Depends(rate_limit("auth.register", rpm=20))])
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPair:
    existing = await session.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=payload.email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="auth.register",
        target_type="user",
        target_id=user.id,
        details={"email": user.email},
        commit=True,
    )
    return await _issue_token_pair(user.id)


@router.post("/login", response_model=TokenPair, dependencies=[Depends(rate_limit("auth.login", rpm=30))])
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPair:
    result = await session.execute(select(User).where(User.email == payload.email, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token_pair = await _issue_token_pair(user.id)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="auth.login",
        target_type="user",
        target_id=user.id,
        details={"email": user.email},
        commit=True,
    )
    return token_pair


@router.post("/refresh", response_model=TokenPair, dependencies=[Depends(rate_limit("auth.refresh", rpm=60))])
async def refresh_token(payload: RefreshTokenRequest) -> TokenPair:
    claims = await _assert_refresh_token_active(payload.refresh_token)
    old_jti = claims.get("jti")
    user_id = claims.get("sub")
    if not isinstance(old_jti, str) or not isinstance(user_id, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    redis = get_app_state().job_queue
    await redis.delete(_refresh_cache_key(old_jti))
    return await _issue_token_pair(user_id)


@router.post("/logout", dependencies=[Depends(rate_limit("auth.logout", rpm=60))])
async def logout(
    payload: LogoutRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    claims = await _assert_refresh_token_active(payload.refresh_token, expected_user_id=user.id)
    jti = claims.get("jti")
    if not isinstance(jti, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    redis = get_app_state().job_queue
    await redis.delete(_refresh_cache_key(jti))

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="auth.logout",
        target_type="user",
        target_id=user.id,
        details={},
        commit=True,
    )
    return {"status": "ok"}


@router.get("/me", response_model=CurrentUser, dependencies=[Depends(rate_limit("auth.me"))])
async def me(user: User = Depends(get_current_user)) -> CurrentUser:
    return CurrentUser(id=user.id, email=user.email, full_name=user.full_name, role=user.role.value)


@router.get("/github/authorize", dependencies=[Depends(rate_limit("auth.github_authorize", rpm=30))])
async def github_authorize() -> dict[str, str]:
    settings = get_settings()
    if not settings.github_oauth_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub OAuth not configured")

    query = urlencode(
        {
            "client_id": settings.github_oauth_client_id,
            "redirect_uri": settings.github_oauth_callback,
            "scope": "read:user user:email",
        }
    )
    return {"url": f"https://github.com/login/oauth/authorize?{query}"}


@router.get(
    "/github/callback",
    response_model=TokenPair,
    dependencies=[Depends(rate_limit("auth.github_callback", rpm=30))],
)
async def github_callback(code: str = Query(min_length=1), session: AsyncSession = Depends(get_db_session)) -> TokenPair:
    settings = get_settings()
    if not settings.github_oauth_client_id or not settings.github_oauth_client_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GitHub OAuth not configured")

    async with httpx.AsyncClient(timeout=30) as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={
                "client_id": settings.github_oauth_client_id,
                "client_secret": settings.github_oauth_client_secret,
                "code": code,
                "redirect_uri": settings.github_oauth_callback,
            },
        )
        token_resp.raise_for_status()
        token = token_resp.json().get("access_token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="GitHub OAuth exchange failed")

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        user_resp.raise_for_status()
        gh_user = user_resp.json()

        email_resp = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        email_resp.raise_for_status()

    primary_email = ""
    for item in email_resp.json():
        if item.get("primary"):
            primary_email = item.get("email", "")
            break
    if not primary_email:
        primary_email = gh_user.get("email") or f"{gh_user['id']}@users.noreply.github.com"

    stmt = select(User).where(User.email == primary_email)
    existing = await session.execute(stmt)
    user = existing.scalar_one_or_none()
    if not user:
        user = User(
            email=primary_email,
            full_name=gh_user.get("name") or gh_user.get("login", ""),
            password_hash=hash_password(f"oauth-{datetime.now(tz=UTC).timestamp()}"),
            oauth_provider="github",
            oauth_subject=str(gh_user["id"]),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="auth.login.github",
        target_type="user",
        target_id=user.id,
        details={"oauth_provider": "github"},
        commit=True,
    )
    return await _issue_token_pair(user.id)
