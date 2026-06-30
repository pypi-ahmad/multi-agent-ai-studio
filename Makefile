UV_CACHE_DIR ?= /home/ahmad/AI/.uv-cache

.PHONY: setup run-api run-worker test lint format compose-up compose-down

setup:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv venv --python 3.12.10
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync --group dev
	PYTHONPATH=apps/api/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run alembic -c apps/api/alembic.ini upgrade head

run-api:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run uvicorn ai_studio.main:app --app-dir apps/api/src --host 0.0.0.0 --port 8000 --reload

run-worker:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m ai_studio_worker.main

test:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run pytest -q

lint:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff check .
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run mypy apps/api/src

format:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff check --fix .

compose-up:
	docker compose up -d --build

compose-down:
	docker compose down -v
