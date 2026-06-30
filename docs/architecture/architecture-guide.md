# Architecture Guide

## What It Does

Multi-Agent AI Studio provides an integrated environment to design, execute, monitor, and evaluate local-first agentic AI workflows.

## Why It Exists

Most agent tools optimize either experimentation or production operations. This platform bridges both: engineering velocity and operational rigor with privacy-first local execution.

## How It Works

- Frontend (`Next.js`) renders product surfaces for chat, workflows, memory, evaluation, and monitoring.
- Backend (`FastAPI`) hosts REST + SSE APIs, orchestration services, model routing, and persistence.
- Supervisor runtime (`LangGraph`) coordinates planner, executor, reviewer, and critic stages.
- Worker layer (`ARQ`) executes asynchronous jobs for long-running tasks.
- Data stores:
  - PostgreSQL: transactional metadata.
  - Qdrant: vector retrieval.
  - Redis: queues and caching.
  - MinIO: object storage.
- Observability via OpenTelemetry + Langfuse.

## Design Decisions

- **Modular monolith backend** for lower ops overhead while keeping domain isolation.
- **Versioned workflow DSL** to make graph execution deterministic and auditable.
- **Capability-based model router** to avoid brittle hardcoded model names.
- **Confirmation-gated destructive tools** for safe local automation.

## Alternative Implementations

- Full microservices: stronger isolation, higher complexity.
- Fixed model mapping: simpler, less adaptive.
- No worker queue: easier setup, weaker reliability for heavy workloads.

## Best Practices

- Keep agent prompts and tool permissions minimal per role.
- Track run/evaluation regressions before changing model-routing weights.
- Keep workflow specs versioned and backward-compatible.
