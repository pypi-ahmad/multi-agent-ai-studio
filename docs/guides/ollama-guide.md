# Ollama Guide

## What It Does

Runs local language, OCR, embedding, and translation models used by routing and orchestration.

## Runtime Notes

- API endpoint default: `http://localhost:11434`.
- Model router discovers capabilities from Ollama metadata.
- No model names hardcoded in routing logic.

## Best Practices

- Keep at least one embedding-capable model available.
- Prefer 2B-4B models for concurrent workflows on 8GB VRAM.
- Warm key models before heavy runs.
