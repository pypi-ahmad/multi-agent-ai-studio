# Troubleshooting Guide

## API cannot reach Ollama

- Check `OLLAMA_BASE_URL` in `.env`.
- Verify `curl http://localhost:11434/api/tags`.

## GPU not detected

- Run `nvidia-smi` manually.
- Confirm NVIDIA driver loaded in host and Docker runtime.

## Qdrant retrieval empty

- Ensure ingestion completed.
- Validate embedding model availability and vector dimensions.

## Unauthorized API errors

- Confirm `Authorization: Bearer <token>` header.
- Re-login to refresh expired token.
