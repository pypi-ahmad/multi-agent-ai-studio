FROM python:3.12-slim
WORKDIR /app
ENV UV_CACHE_DIR=/tmp/uv-cache
ENV PYTHONPATH=/app/apps/api/src:/app/workers/arq/src
RUN pip install --no-cache-dir uv
COPY pyproject.toml /app/
RUN uv sync --no-dev
COPY apps/api /app/apps/api
COPY workers /app/workers
COPY packages /app/packages
CMD ["sh", "-c", "uv run arq ai_studio_worker.main.WorkerSettings"]
