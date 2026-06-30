#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

cp .env.example .env || true
export UV_CACHE_DIR="${UV_CACHE_DIR:-/home/ahmad/AI/.uv-cache}"
uv venv --python 3.12.10
uv sync --group dev
PYTHONPATH=apps/api/src uv run alembic -c apps/api/alembic.ini upgrade head
