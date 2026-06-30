# Deployment Guide

## Local Production-Like Deployment

1. Configure `.env` with secrets and service endpoints.
2. Start dependencies via Docker Compose.
3. Run DB migrations.
4. Start API and worker processes.
5. Start frontend service.
6. Validate health endpoints and core user journeys.

## Validation Checklist

- Auth login + token refresh path.
- Agent/workflow CRUD.
- Supervisor chat run.
- RAG ingest and retrieval.
- Tool execution with confirmation.
- Evaluation write/read.
- Trace and system metrics visibility.
