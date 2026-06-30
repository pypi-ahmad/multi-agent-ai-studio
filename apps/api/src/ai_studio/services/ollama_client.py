from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from ai_studio.core.config import get_settings


@dataclass(slots=True)
class OllamaModel:
    name: str
    parameter_size: str
    families: list[str]
    context_length: int
    embedding_length: int | None
    capabilities: list[str]


class OllamaClient:
    """Async Ollama client with health and model bootstrap helpers."""

    def __init__(self) -> None:
        settings = get_settings()
        self._settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_request_timeout,
        )

    async def health(self) -> tuple[bool, str]:
        """Return runtime reachability and optional error."""
        try:
            response = await self._client.get("/api/tags", timeout=self._settings.ollama_health_timeout)
            response.raise_for_status()
            return True, ""
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    async def list_models(self) -> list[OllamaModel]:
        response = await self._client.get("/api/tags")
        response.raise_for_status()
        payload = response.json()
        result: list[OllamaModel] = []
        for model in payload.get("models", []):
            details = model.get("details", {})
            families = details.get("families") or []
            result.append(
                OllamaModel(
                    name=model["name"],
                    parameter_size=details.get("parameter_size", ""),
                    families=families,
                    context_length=int(details.get("context_length", 0) or 0),
                    embedding_length=details.get("embedding_length"),
                    capabilities=model.get("capabilities", []),
                )
            )
        return result

    async def pull_model(self, model: str) -> None:
        """Pull model into local runtime."""
        response = await self._client.post(
            "/api/pull",
            json={"model": model, "stream": False},
            timeout=None,
        )
        response.raise_for_status()

    async def ensure_models(self, models: list[str]) -> None:
        """Ensure models available when auto-pull enabled."""
        if not self._settings.ollama_auto_pull_models or not models:
            return

        available = {item.name for item in await self.list_models()}
        for model in models:
            if model in available:
                continue
            logger.info("Pulling missing Ollama model '{}'", model)
            await self.pull_model(model)

    async def embeddings(self, model: str, text: str) -> list[float]:
        response = await self._client.post("/api/embeddings", json={"model": model, "prompt": text}, timeout=None)
        response.raise_for_status()
        data = response.json()
        return list(data.get("embedding", []))

    def _generation_payload(self, model: str, prompt: str, stream: bool, options: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": options or {},
        }
        if self._settings.ollama_disable_thinking:
            payload["think"] = False
        return payload

    async def generate(self, model: str, prompt: str, options: dict[str, Any] | None = None) -> str:
        response = await self._client.post(
            "/api/generate",
            json=self._generation_payload(model=model, prompt=prompt, stream=False, options=options),
            timeout=None,
        )
        response.raise_for_status()
        data = response.json()
        return str(data.get("response", ""))

    async def stream_generate(self, model: str, prompt: str) -> AsyncIterator[str]:
        async with self._client.stream(
            "POST",
            "/api/generate",
            json=self._generation_payload(model=model, prompt=prompt, stream=True),
            timeout=None,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = httpx.Response(200, content=line).json()
                except ValueError:
                    continue
                chunk = data.get("response")
                if chunk:
                    yield str(chunk)

    async def close(self) -> None:
        await self._client.aclose()
