# API Documentation

## Authentication

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/github/authorize`
- `GET /api/v1/auth/github/callback`

## Core Domain APIs

- Agents: `GET/POST/DELETE /api/v1/agents`
- Workflows:
  - `GET/POST /api/v1/workflows`
  - `GET/PUT/DELETE /api/v1/workflows/{workflow_id}`
  - `POST /api/v1/workflows/validate`
- Chat: `GET/POST /api/v1/chat`, `GET/POST /api/v1/chat/{chat_id}/messages`, `GET /api/v1/chat/{chat_id}/stream`
- Runs: `GET/POST/DELETE /api/v1/runs`
- Memory: `GET/POST/PATCH/DELETE /api/v1/memory`, `POST /api/v1/memory/summary`, `POST /api/v1/memory/forget`
- Experiments: `GET/POST/PATCH/DELETE /api/v1/experiments`
- Settings: `GET /api/v1/settings`, `GET/PUT /api/v1/settings/{key}`
- Logs: `GET/POST /api/v1/logs`

## RAG APIs

- Documents: `GET/POST /api/v1/rag/documents`
- File ingest: `POST /api/v1/rag/documents/{id}/ingest`
- Connector catalog: `GET /api/v1/rag/connectors`
- Connector ingest (GitHub/Web): `POST /api/v1/rag/connectors/ingest`
- Retrieval: `POST /api/v1/rag/retrieve`

## Evaluation + Cost APIs

- Evaluation list/create/delete: `GET/POST/DELETE /api/v1/evaluation`
- Evaluation summary: `GET /api/v1/evaluation/summary`
- Cost estimate: `POST /api/v1/evaluation/estimate-cost`

## Trace + Observability APIs

- Trace list: `GET /api/v1/traces`
- Trace detail: `GET /api/v1/traces/{trace_id}`
- Trace timeline: `GET /api/v1/traces/{trace_id}/timeline`
- Delete trace: `DELETE /api/v1/traces/{trace_id}`
- System health: `GET /api/v1/system/health`
- Model router snapshot: `GET /api/v1/system/models`
- System time-series metrics: `GET /api/v1/system/metrics/timeseries`
- Model manager snapshot: `GET /api/v1/models/snapshot`
- Model refresh: `POST /api/v1/models/refresh`
- Model routing rules: `POST/DELETE /api/v1/models/routing-rules`

## Marketplace + Tooling APIs

- Marketplace templates: `GET /api/v1/marketplace/templates`
- Publish template: `POST /api/v1/marketplace/templates/publish`
- Import template: `POST /api/v1/marketplace/templates/{template_id}/import`
- Tool catalog: `GET /api/v1/tools`
- Unified tool executor: `POST /api/v1/tools/execute`
- Filesystem tools:
  - `POST /api/v1/tools/filesystem/read`
  - `POST /api/v1/tools/filesystem/list`
  - `POST /api/v1/tools/filesystem/search`
  - `POST /api/v1/tools/filesystem/write`
  - `POST /api/v1/tools/filesystem/move`
  - `POST /api/v1/tools/filesystem/copy`
  - `POST /api/v1/tools/filesystem/delete`
- Terminal exec: `POST /api/v1/tools/terminal/exec`
- Python exec: `POST /api/v1/tools/python/exec`

## API Contract Notes

- Authenticated endpoints require `Authorization: Bearer <access_token>`.
- Token rotation supported through `POST /api/v1/auth/refresh`.
- Destructive tool endpoints require `X-Confirm-Token: CONFIRM-<ENV>`.
- Rate limiting is enforced per-scope via Redis-backed counters.
- Workflow payloads must satisfy `WorkflowSpec` JSON schema.
