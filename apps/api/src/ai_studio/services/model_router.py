from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import mean
from typing import Literal

from ai_studio.core.config import get_settings
from ai_studio.services.ollama_client import OllamaClient, OllamaModel

TaskType = Literal[
    "reasoning",
    "coding",
    "ocr",
    "embedding",
    "translation",
    "summarization",
    "vision",
    "chat",
]


@dataclass(slots=True)
class ModelCapabilityProfile:
    model_name: str
    capabilities: set[str]
    context_length: int
    score: float


class ModelRouter:
    """Capability-based router with refresh TTL and safe fallbacks."""

    def __init__(self, ollama_client: OllamaClient) -> None:
        self._settings = get_settings()
        self._ollama_client = ollama_client
        self._profiles: dict[str, ModelCapabilityProfile] = {}
        self._custom_rules: dict[str, str] = {}
        self._last_refresh: datetime | None = None
        self._last_error: str | None = None

    @staticmethod
    def _infer_capabilities(model: OllamaModel) -> set[str]:
        name = model.name.lower()
        capabilities = set(model.capabilities)
        families = {family.lower() for family in model.families}

        if "embedding" in capabilities or "embed" in name or model.embedding_length:
            capabilities.add("embedding")
        if "ocr" in name:
            capabilities.add("ocr")
        if "vision" in name or "multimodal" in families:
            capabilities.add("vision")
        if "translate" in name:
            capabilities.add("translation")
        if "code" in name or "coder" in name:
            capabilities.add("coding")

        capabilities.update({"chat", "reasoning", "summarization"})
        return capabilities

    @staticmethod
    def _base_score(model: OllamaModel, caps: set[str]) -> float:
        size_text = model.parameter_size.lower()
        size_value = 0.0
        if "b" in size_text:
            try:
                size_value = float(size_text.replace("b", "").strip())
            except ValueError:
                size_value = 1.0
        context_score = min(model.context_length / 8192.0, 2.0)
        modality_bonus = 0.2 * len(caps)
        return 0.6 * size_value + 0.3 * context_score + 0.1 * modality_bonus

    def _refresh_due(self) -> bool:
        if not self._last_refresh:
            return True
        return datetime.now(tz=UTC) - self._last_refresh > timedelta(
            seconds=self._settings.model_router_refresh_seconds
        )

    async def refresh(self) -> None:
        try:
            models = await self._ollama_client.list_models()
            profiles: dict[str, ModelCapabilityProfile] = {}
            for model in models:
                caps = self._infer_capabilities(model)
                score = self._base_score(model, caps)
                profiles[model.name] = ModelCapabilityProfile(
                    model_name=model.name,
                    capabilities=caps,
                    context_length=model.context_length,
                    score=score,
                )
            self._profiles = profiles
            self._last_refresh = datetime.now(tz=UTC)
            self._last_error = None
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            raise

    async def ensure_fresh(self) -> None:
        if self._refresh_due():
            await self.refresh()

    def _preferred_model_for_task(self, task: TaskType) -> str | None:
        if task in {"chat", "reasoning", "summarization", "coding", "translation"} and self._settings.ollama_preferred_chat_model:
            return self._settings.ollama_preferred_chat_model
        if task == "embedding" and self._settings.ollama_preferred_embedding_model:
            return self._settings.ollama_preferred_embedding_model
        return None

    async def pick(self, task: TaskType) -> str:
        await self.ensure_fresh()

        custom = self._custom_rules.get(task)
        if custom and custom in self._profiles:
            return custom

        preferred = self._preferred_model_for_task(task)
        if preferred and preferred in self._profiles:
            return preferred

        candidates = [profile for profile in self._profiles.values() if task in profile.capabilities]
        if not candidates:
            candidates = list(self._profiles.values())
        if not candidates:
            raise RuntimeError("No Ollama models discovered for routing")

        candidates.sort(key=lambda profile: profile.score, reverse=True)
        return candidates[0].model_name

    def set_custom_rule(self, task: TaskType, model_name: str) -> None:
        self._custom_rules[task] = model_name

    def clear_custom_rule(self, task: TaskType) -> None:
        self._custom_rules.pop(task, None)

    def snapshot(self) -> dict[str, object]:
        models = [
            {
                "model_name": profile.model_name,
                "capabilities": sorted(profile.capabilities),
                "context_length": profile.context_length,
                "score": round(profile.score, 3),
            }
            for profile in sorted(self._profiles.values(), key=lambda x: x.score, reverse=True)
        ]
        return {
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "last_error": self._last_error,
            "count": len(models),
            "models": models,
            "avg_score": round(mean([p.score for p in self._profiles.values()]), 3)
            if self._profiles
            else 0.0,
            "custom_rules": dict(sorted(self._custom_rules.items())),
        }
