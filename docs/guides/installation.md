# Installation Guide

## Prerequisites

- Linux with Docker and Docker Compose.
- Python 3.12.10 available through `uv`.
- Node.js 24+.
- Ollama installed locally.
- Optional GPU runtime (`nvidia-smi`) for accelerated inference.

## Backend Setup

```bash
cd /home/ahmad/AI/multi-agent-ai-studio
cp .env.example .env
make setup
make run-api
```

`make setup` now includes `alembic upgrade head` to ensure schema revision matches runtime.

## Frontend Setup

```bash
cd /home/ahmad/AI/multi-agent-ai-studio/apps/web
npm install
npm run dev
```

## Full Stack via Docker

```bash
cd /home/ahmad/AI/multi-agent-ai-studio
docker compose up -d --build
```
