from fastapi import APIRouter

from ai_studio.api.routers import (
    agents,
    auth,
    chat,
    evaluation,
    experiments,
    logs,
    marketplace,
    memory,
    models,
    rag,
    runs,
    settings,
    system,
    tools,
    traces,
    workflows,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(workflows.router)
api_router.include_router(chat.router)
api_router.include_router(memory.router)
api_router.include_router(rag.router)
api_router.include_router(runs.router)
api_router.include_router(evaluation.router)
api_router.include_router(traces.router)
api_router.include_router(system.router)
api_router.include_router(tools.router)
api_router.include_router(experiments.router)
api_router.include_router(settings.router)
api_router.include_router(logs.router)
api_router.include_router(models.router)
api_router.include_router(marketplace.router)
