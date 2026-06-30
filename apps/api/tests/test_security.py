from __future__ import annotations

from ai_studio.core.security import create_token, decode_token


def test_jwt_round_trip() -> None:
    token = create_token("user-id", "access", 10)
    payload = decode_token(token)
    assert payload["sub"] == "user-id"
    assert payload["type"] == "access"
