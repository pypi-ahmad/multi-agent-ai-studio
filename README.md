# Multi-Agent AI Studio

Production-grade, privacy-first, local agentic AI platform for building, running, debugging, evaluating, and monitoring multi-agent systems on your own machine.

Core stack in this repository:
- FastAPI backend (`apps/api`)
- LangGraph-based supervisor orchestration
- Ollama-first local inference
- PostgreSQL + Qdrant + Redis + MinIO
- Next.js frontend (`apps/web`)
- OpenTelemetry/Langfuse-ready tracing and metrics
- Docker Compose deployment
- MkDocs Material documentation

## Real Run Verification (No Mock Runs)

This repository was executed end-to-end with real services and real requests on **June 29, 2026**.

- Latest run ID: `20260629T160239Z`
- Artifacts directory: `artifacts/e2e-live/20260629T160239Z/`
- Summary file: `artifacts/e2e-live/20260629T160239Z/summary.json`

Verified `summary.json` checks (all `true`):
- `api_auth`
- `model_router`
- `supervisor_chat_run`
- `chat_stream`
- `memory`
- `rag_ingest_retrieve`
- `evaluation`
- `marketplace`
- `tools`
- `metrics_timeseries`
- `postgres`
- `qdrant`
- `web`

---

## 1) Compile + Dependency Check (Executed)

The following commands were executed successfully:

```bash
cd /home/ahmad/AI/multi-agent-ai-studio
export UV_CACHE_DIR=/tmp/uv-cache

uv sync --group dev
uv run ruff check .
uv run mypy apps/api/src
uv run pytest -q

cd apps/web
npm ci
npm run build
cd /home/ahmad/AI/multi-agent-ai-studio

uv run mkdocs build --strict
```

Observed results from the real run:
- `ruff`: passed
- `mypy`: passed (`60` files checked)
- `pytest`: passed (`8 passed`)
- `next build`: passed
- `mkdocs --strict`: passed (`site/` generated)

---

## 2) E2E Live Execution (Executed)

Real stack startup:

```bash
docker compose up -d --build postgres redis qdrant minio otel-collector api worker web
```

Real E2E execution:

```bash
./scripts/e2e_live_run.sh
```

Script result:
- `Live E2E run completed successfully.`
- Artifacts generated in: `artifacts/e2e-live/20260629T160239Z/`

---

## 3) Result Verification (Executed)

### Build artifacts

Verified present:
- `apps/web/.next/`
- `apps/web/.next/BUILD_ID`
- `site/`
- `site/index.html`

### Live service status

Verified running via `docker compose ps`:
- `api`
- `worker`
- `web`
- `postgres`
- `redis`
- `qdrant`
- `minio`
- `ollama`
- `otel-collector`

### Live API/Web responses

Verified:

```json
GET /
{"service":"multi-agent-ai-studio-api","status":"ok"}
```

`GET /api/v1/system/health` (authorized) returned:
- status `ok`
- database `up`
- redis `up`
- qdrant `up`
- ollama `up`
- model_router `ok`

Web check:
- `http://localhost:3000` responds and redirects to `/dashboard`.

### Live persistence checks

PostgreSQL (real query results from this run):
- users count: `26`
- inserted run document (`summary.ids.document_id`) exists: `1` row
- inserted trace (`summary.ids.trace_id`) exists: `1` row

Qdrant (real query result):
- collection: `studio_chunks`
- status: `green`
- points count: `131`

---

## Zero-to-Hero Setup Guide

This section is based on the real commands used to run this repository successfully.

## Prerequisites

- Linux
- Docker + Docker Compose
- `uv`
- Node.js + npm
- Ollama installed locally
- Optional but recommended: NVIDIA GPU + CUDA

## Project location

```bash
cd /home/ahmad/AI/multi-agent-ai-studio
```

## Environment setup

```bash
cp .env.example .env
uv venv --python 3.12.10
export UV_CACHE_DIR=/tmp/uv-cache
uv sync --group dev
```

## Frontend setup

```bash
cd apps/web
npm ci
cd /home/ahmad/AI/multi-agent-ai-studio
```

## Build + quality checks

```bash
uv run ruff check .
uv run mypy apps/api/src
uv run pytest -q
cd apps/web && npm run build
cd /home/ahmad/AI/multi-agent-ai-studio
uv run mkdocs build --strict
```

## Run the platform

```bash
docker compose up -d --build postgres redis qdrant minio otel-collector api worker web
```

Useful URLs:
- API docs: `http://localhost:8001/docs`
- OpenAPI JSON: `http://localhost:8001/openapi.json`
- Web app: `http://localhost:3000`
- Qdrant: `http://localhost:6333`
- MinIO: `http://localhost:9001`

## Run full live E2E flow

```bash
./scripts/e2e_live_run.sh
```

This script performs real authenticated and persisted operations across:
- auth register/login/refresh/me/logout
- model router refresh/rules/snapshot
- agent + workflow CRUD
- chat execution + SSE streaming
- traces + timeline
- memory create/edit/summarize/forget
- RAG ingest + retrieve with citations
- evaluation + experiment + settings + logs
- marketplace publish/import/list
- filesystem/terminal/python tools
- metrics timeseries
- postgres + qdrant integrity checks
- web availability check

---

## Architecture Overview

## Backend

Path: `apps/api/src/ai_studio/`

Main modules:
- `api/routers/`: route handlers and request/response contracts
- `services/agent_runtime.py`: multi-agent orchestration runtime
- `services/model_router.py`: capability-based model routing
- `services/rag_service.py`: ingestion, chunking, embedding, retrieval
- `services/system_metrics.py`: CPU/RAM/GPU/system telemetry
- `db/` and `models/entities.py`: SQLAlchemy models + persistence
- `workers/arq/`: async background processing

## Frontend

Path: `apps/web/`

Next.js app with pages for dashboard, chat, agent/workflow management, memory, RAG, evaluation, traces, experiments, settings, logs, model manager, and system monitoring.

## Infrastructure

- PostgreSQL for transactional state
- Qdrant for vector search
- Redis for cache/rate-limit/queue state
- MinIO for object storage
- Ollama for local model inference
- OpenTelemetry collector for traces/metrics

## Agent orchestration logic

The supervisor runtime executes a staged graph:
1. planner
2. decomposer
3. router
4. specialist
5. reviewer
6. critic

Execution metadata is persisted and can be inspected via `/api/v1/runs` and `/api/v1/traces`.

---

## API Surface (Live OpenAPI)

Base: `http://localhost:8001`

Route groups available in this codebase:
- `/api/v1/auth/*`
- `/api/v1/agents*`
- `/api/v1/workflows*`
- `/api/v1/chat*`
- `/api/v1/memory*`
- `/api/v1/rag*`
- `/api/v1/runs*`
- `/api/v1/traces*`
- `/api/v1/evaluation*`
- `/api/v1/experiments*`
- `/api/v1/settings*`
- `/api/v1/logs*`
- `/api/v1/models*`
- `/api/v1/system*`
- `/api/v1/tools*`
- `/api/v1/marketplace*`

---

## Security and Safety Controls

Implemented in code and used during E2E execution:
- JWT access + refresh auth
- token revocation checks
- role-based authorization guards
- request validation via Pydantic
- rate limiting
- destructive tool safeguards using confirmation header:
  - `X-Confirm-Token: CONFIRM-DEVELOPMENT`
- filesystem/terminal tool root restrictions for host and container paths

---

## Documentation Index

- `docs/guides/installation.md`
- `docs/architecture/architecture-guide.md`
- `docs/architecture/architecture-diagrams.md`
- `docs/api/api-guide.md`
- `docs/guides/langgraph-guide.md`
- `docs/guides/agent-development-guide.md`
- `docs/guides/folder-structure.md`
- `docs/guides/memory-guide.md`
- `docs/guides/tool-calling-guide.md`
- `docs/guides/rag-guide.md`
- `docs/guides/evaluation-guide.md`
- `docs/guides/observability-guide.md`
- `docs/operations/deployment-guide.md`
- `docs/operations/docker-guide.md`
- `docs/guides/ollama-guide.md`
- `docs/guides/gpu-guide.md`
- `docs/operations/troubleshooting-guide.md`
- `docs/operations/faq.md`
- `docs/guides/performance-guide.md`
- `docs/guides/beginner-learning-guide.md`

---

## Cleanup (Post-run)

Safe cleanup commands used for temporary local caches/logs:

```bash
rm -rf /tmp/uv-cache
rm -f /tmp/openapi_live.json /tmp/live_api_root.json /tmp/live_system_health_auth.json /tmp/live_qdrant_collection.json
```

Optional: stop stack when done:

```bash
docker compose down
```

---

## License

MIT

<p align="center">Made with ❤️ by Ahmad Mujtaba</p>
