FROM python:3.12-slim
WORKDIR /app
ENV UV_CACHE_DIR=/tmp/uv-cache
ENV PYTHONPATH=/app/apps/api/src:/app/workers/arq/src
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY pyproject.toml /app/
RUN uv sync --no-dev
COPY apps/api /app/apps/api
COPY workers /app/workers
COPY packages /app/packages
CMD ["sh", "-c", "uv run alembic -c apps/api/alembic.ini upgrade head && uv run uvicorn ai_studio.main:app --app-dir apps/api/src --host 0.0.0.0 --port 8000"]
