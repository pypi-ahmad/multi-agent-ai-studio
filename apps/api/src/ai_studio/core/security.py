from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from ai_studio.core.config import get_settings

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash password using Argon2id."""
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def create_token(subject: str, token_type: str, minutes: int) -> str:
    """Create signed JWT token."""
    settings = get_settings()
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.app_jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate JWT token."""
    settings = get_settings()
    return jwt.decode(token, settings.app_secret_key, algorithms=[settings.app_jwt_algorithm])
