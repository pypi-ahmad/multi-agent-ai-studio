from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def _build_alembic_config() -> Config:
    current = Path(__file__).resolve()
    api_root = current.parents[3]
    ini_path = api_root / "alembic.ini"
    script_path = api_root / "alembic"

    if not ini_path.exists() or not script_path.exists():
        raise RuntimeError(
            f"Alembic configuration not found. Expected '{ini_path}' and '{script_path}'"
        )

    config = Config(str(ini_path))
    config.set_main_option("script_location", str(script_path))
    return config


async def ensure_schema_current(engine: AsyncEngine) -> None:
    """Fail fast when runtime schema revision differs from Alembic head."""
    config = _build_alembic_config()
    script = ScriptDirectory.from_config(config)
    expected_heads = set(script.get_heads())

    if not expected_heads:
        raise RuntimeError("No Alembic heads found. Migration tree is invalid")

    try:
        async with engine.connect() as conn:
            rows = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current_heads = {str(row[0]) for row in rows.fetchall()}
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Database schema revision missing. Run: 'uv run alembic -c apps/api/alembic.ini upgrade head'"
        ) from exc

    if not current_heads:
        raise RuntimeError(
            "Database schema revision not set. Run: 'uv run alembic -c apps/api/alembic.ini upgrade head'"
        )

    if current_heads != expected_heads:
        expected = ",".join(sorted(expected_heads))
        current = ",".join(sorted(current_heads))
        raise RuntimeError(
            "Database schema out of date. "
            f"Current={current}. Expected={expected}. "
            "Run: 'uv run alembic -c apps/api/alembic.ini upgrade head'"
        )
