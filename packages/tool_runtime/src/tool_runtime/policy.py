from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConfirmationPolicy:
    header_name: str = "X-Confirm-Token"

    def expected_token(self, env_name: str) -> str:
        return f"CONFIRM-{env_name.upper()}"
