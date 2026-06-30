# Docker Guide

## Core Stack (API + Worker + Ollama + Data Services)

```bash
docker compose up -d --build
```

This brings up:

- `api` (FastAPI)
- `worker` (ARQ background jobs)
- `ollama` (local model runtime)
- `postgres`, `redis`, `qdrant`, `minio`

## Guaranteed Ollama Connectivity

Compose wiring guarantees API/worker startup after Ollama health check:

- `api` and `worker` depend on `ollama: service_healthy`
- API startup fails fast if Ollama is unreachable or has no discoverable models
- `OLLAMA_BASE_URL` defaults to `http://ollama:11434` for container networking

## Optional Model Bootstrap

Pull configured Ollama models after stack starts:

```bash
docker compose --profile ollama-bootstrap up -d ollama-bootstrap
```

Configure model list via `OLLAMA_BOOTSTRAP_MODELS` in `.env`.

## Optional Langfuse Profile

```bash
docker compose --profile observability up -d
```

## Stop and Clean Volumes

```bash
docker compose down -v
```
