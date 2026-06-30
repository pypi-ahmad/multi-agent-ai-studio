from __future__ import annotations

from dataclasses import dataclass

from ai_studio.services.model_router import ModelRouter
from ai_studio.services.ollama_client import OllamaModel


@dataclass
class FakeOllamaClient:
    async def list_models(self) -> list[OllamaModel]:
        return [
            OllamaModel(
                name="qwen3.5:4b",
                parameter_size="4B",
                families=["qwen"],
                context_length=32768,
                embedding_length=None,
                capabilities=[],
            ),
            OllamaModel(
                name="qwen3-embedding:4b",
                parameter_size="4B",
                families=["qwen"],
                context_length=8192,
                embedding_length=1024,
                capabilities=["embedding"],
            ),
            OllamaModel(
                name="glm-ocr:latest",
                parameter_size="3B",
                families=["glm"],
                context_length=8192,
                embedding_length=None,
                capabilities=[],
            ),
        ]


async def test_model_router_picks_embedding_model() -> None:
    router = ModelRouter(FakeOllamaClient())
    model = await router.pick("embedding")
    assert "embedding" in model


async def test_model_router_picks_ocr_model() -> None:
    router = ModelRouter(FakeOllamaClient())
    model = await router.pick("ocr")
    assert "ocr" in model
