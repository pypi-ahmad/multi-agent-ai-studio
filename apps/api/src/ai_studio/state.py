from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, cast

from arq import create_pool
from arq.connections import RedisSettings
from loguru import logger

from ai_studio.core.config import get_settings
from ai_studio.db.session import SessionLocal
from ai_studio.models.entities import SystemMetricSample
from ai_studio.services.agent_runtime import SupervisorRuntime
from ai_studio.services.gpu_monitor import GpuMonitor
from ai_studio.services.model_router import ModelRouter
from ai_studio.services.ollama_client import OllamaClient
from ai_studio.services.rag_service import RagService
from ai_studio.services.system_metrics import SystemMetricsService
from ai_studio.services.tool_registry import ToolManifest, ToolRegistry


@dataclass(slots=True)
class AppState:
    ollama_client: OllamaClient
    model_router: ModelRouter
    supervisor_runtime: SupervisorRuntime
    rag_service: RagService
    tool_registry: ToolRegistry
    system_metrics: SystemMetricsService
    job_queue: object
    metrics_task: asyncio.Task[None] | None


_app_state: AppState | None = None


async def build_app_state() -> AppState:
    settings = get_settings()
    ollama_client = OllamaClient()

    healthy, error = await ollama_client.health()
    if not healthy:
        await ollama_client.close()
        raise RuntimeError(f"Ollama unreachable at {settings.ollama_base_url}: {error}")

    await ollama_client.ensure_models(settings.bootstrap_models)
    model_router = ModelRouter(ollama_client)
    await model_router.refresh()
    if not model_router.snapshot().get("models"):
        await ollama_client.close()
        raise RuntimeError("Ollama reachable but no models discovered for routing")

    supervisor_runtime = SupervisorRuntime(model_router, ollama_client)
    rag_service = RagService(ollama_client, model_router)
    tool_registry = ToolRegistry()
    _register_builtin_tools(tool_registry)
    system_metrics = SystemMetricsService(GpuMonitor())

    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_queue = await create_pool(redis_settings)

    metrics_task = asyncio.create_task(
        _collect_system_metrics_loop(
            system_metrics=system_metrics,
            model_router=model_router,
            interval_seconds=settings.metrics_sample_interval_seconds,
        ),
        name="system-metrics-collector",
    )

    return AppState(
        ollama_client=ollama_client,
        model_router=model_router,
        supervisor_runtime=supervisor_runtime,
        rag_service=rag_service,
        tool_registry=tool_registry,
        system_metrics=system_metrics,
        job_queue=job_queue,
        metrics_task=metrics_task,
    )


def set_app_state(state: AppState) -> None:
    global _app_state
    _app_state = state


def get_app_state() -> AppState:
    if _app_state is None:
        raise RuntimeError("App state not initialized")
    return _app_state


async def shutdown_app_state() -> None:
    app_state = get_app_state()
    if app_state.metrics_task:
        app_state.metrics_task.cancel()
        try:
            await app_state.metrics_task
        except asyncio.CancelledError:
            pass
    await app_state.ollama_client.close()
    await app_state.rag_service.close()
    await app_state.job_queue.close()


async def _collect_system_metrics_loop(
    system_metrics: SystemMetricsService,
    model_router: ModelRouter,
    interval_seconds: int,
) -> None:
    interval = max(interval_seconds, 1)
    while True:
        try:
            snapshot = cast(dict[str, Any], await system_metrics.snapshot())
            gpu = cast(dict[str, Any], snapshot.get("gpu", {}))
            router_snapshot = cast(dict[str, Any], model_router.snapshot())
            sample = SystemMetricSample(
                cpu_percent=float(snapshot["cpu_percent"]),
                memory_total_mb=int(snapshot["memory_total_mb"]),
                memory_used_mb=int(snapshot["memory_used_mb"]),
                memory_percent=float(snapshot["memory_percent"]),
                gpu_available=bool(gpu["available"]),
                gpu_name=str(gpu["name"]),
                gpu_total_mb=int(gpu["total_mb"]),
                gpu_used_mb=int(gpu["used_mb"]),
                gpu_free_mb=int(gpu["free_mb"]),
                gpu_utilization_percent=float(gpu.get("utilization_percent", 0.0)),
                gpu_memory_utilization_percent=float(gpu.get("memory_utilization_percent", 0.0)),
                meta={
                    "model_router": {
                        "last_refresh": router_snapshot.get("last_refresh"),
                        "model_count": len(router_snapshot.get("models", [])),
                    }
                },
            )
            async with SessionLocal() as session:
                session.add(sample)
                await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist system metrics sample: {}", exc)
        await asyncio.sleep(interval)


def _register_builtin_tools(registry: ToolRegistry) -> None:
    registry.register(
        ToolManifest(
            name="filesystem.list",
            description="List directory entries under allowed project roots",
            destructive=False,
            requires_confirmation=False,
            schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        )
    )
    registry.register(
        ToolManifest(
            name="filesystem.search",
            description="Search text recursively inside allowed project roots",
            destructive=False,
            requires_confirmation=False,
            schema={
                "type": "object",
                "properties": {
                    "root": {"type": "string"},
                    "pattern": {"type": "string"},
                    "file_glob": {"type": "string"},
                },
                "required": ["root", "pattern"],
            },
        )
    )
    registry.register(
        ToolManifest(
            name="filesystem.read",
            description="Read file content from allowed project roots",
            destructive=False,
            requires_confirmation=False,
            schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        )
    )
    registry.register(
        ToolManifest(
            name="filesystem.write",
            description="Write file content under allowed project roots",
            destructive=True,
            requires_confirmation=True,
            schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        )
    )
    registry.register(
        ToolManifest(
            name="filesystem.move",
            description="Move file or directory under allowed project roots",
            destructive=True,
            requires_confirmation=True,
            schema={
                "type": "object",
                "properties": {"source": {"type": "string"}, "destination": {"type": "string"}},
                "required": ["source", "destination"],
            },
        )
    )
    registry.register(
        ToolManifest(
            name="filesystem.copy",
            description="Copy file or directory under allowed project roots",
            destructive=True,
            requires_confirmation=True,
            schema={
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "destination": {"type": "string"},
                    "recursive": {"type": "boolean"},
                },
                "required": ["source", "destination"],
            },
        )
    )
    registry.register(
        ToolManifest(
            name="filesystem.delete",
            description="Delete file or directory under allowed project roots",
            destructive=True,
            requires_confirmation=True,
            schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "recursive": {"type": "boolean"}},
                "required": ["path"],
            },
        )
    )
    registry.register(
        ToolManifest(
            name="terminal.exec",
            description="Execute shell command in guarded workspace",
            destructive=True,
            requires_confirmation=True,
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "cwd": {"type": "string"},
                    "timeout_seconds": {"type": "integer"},
                },
                "required": ["command"],
            },
        )
    )
    registry.register(
        ToolManifest(
            name="python.exec",
            description="Execute Python snippet in ephemeral process",
            destructive=True,
            requires_confirmation=True,
            schema={
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "timeout_seconds": {"type": "integer"},
                },
                "required": ["code"],
            },
        )
    )
