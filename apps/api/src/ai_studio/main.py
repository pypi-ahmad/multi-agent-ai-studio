from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from ai_studio.api.router import api_router
from ai_studio.core.config import get_settings
from ai_studio.core.logging import configure_logging
from ai_studio.db.migrations import ensure_schema_current
from ai_studio.db.session import engine
from ai_studio.observability.tracing import configure_tracing
from ai_studio.state import build_app_state, set_app_state, shutdown_app_state


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await ensure_schema_current(engine)

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    state = await build_app_state()
    set_app_state(state)

    yield

    await shutdown_app_state()


app = FastAPI(
    title="Multi-Agent AI Studio API",
    description="Production-grade local multi-agent platform API",
    version="0.1.0",
    lifespan=lifespan,
)
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_tracing(app)
app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "multi-agent-ai-studio-api", "status": "ok"}
