from __future__ import annotations

from ai_studio.core.config import get_settings
from ai_studio.db.session import SessionLocal
from ai_studio.models.entities import AgentRun, RunStatus, TraceRecord
from ai_studio.services.agent_runtime import SupervisorRuntime
from ai_studio.services.model_router import ModelRouter
from ai_studio.services.ollama_client import OllamaClient
from arq.connections import RedisSettings
from sqlalchemy import select


async def execute_agent_run(_ctx: dict[str, object], run_id: str) -> None:
    ollama = OllamaClient()
    healthy, error = await ollama.health()
    if not healthy:
        await ollama.close()
        raise RuntimeError(f"Ollama unavailable for worker run {run_id}: {error}")

    router = ModelRouter(ollama)
    await router.refresh()
    runtime = SupervisorRuntime(router, ollama)

    async with SessionLocal() as session:
        result = await session.execute(select(AgentRun).where(AgentRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            await ollama.close()
            return

        run.status = RunStatus.RUNNING
        await session.commit()

        try:
            output = await runtime.run_with_trace(str(run.input_payload.get("prompt", "")))
            run.output_payload = output
            run.model_usage = output.get("metadata", {})
            run.status = RunStatus.COMPLETED
            run.error_message = ""

            session.add(
                TraceRecord(
                    run_id=run.id,
                    trace_id=str(output.get("trace_id", run.id)),
                    span_count=len(output.get("timeline", [])),
                    meta={
                        "timeline": output.get("timeline", []),
                        "prompt_preview": str(run.input_payload.get("prompt", ""))[:200],
                        "response_preview": str(output.get("response", ""))[:400],
                    },
                )
            )
        except Exception as exc:  # noqa: BLE001
            run.status = RunStatus.FAILED
            run.error_message = str(exc)
        finally:
            await session.commit()

    await ollama.close()


class WorkerSettings:
    settings = get_settings()
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [execute_agent_run]
    max_jobs = 8
