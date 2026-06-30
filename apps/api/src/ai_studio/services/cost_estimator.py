from __future__ import annotations

from ai_studio.schemas.evaluation import CostEstimate


class CostEstimator:
    """Approximate local workload cost using cloud-equivalent normalized rates."""

    PROMPT_TOKEN_RATE = 0.0005 / 1000
    COMPLETION_TOKEN_RATE = 0.0015 / 1000
    GPU_SECOND_RATE = 0.00035
    CPU_SECOND_RATE = 0.00004

    def estimate(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        gpu_seconds: float,
        cpu_seconds: float,
    ) -> CostEstimate:
        cloud_equivalent = (
            prompt_tokens * self.PROMPT_TOKEN_RATE
            + completion_tokens * self.COMPLETION_TOKEN_RATE
            + gpu_seconds * self.GPU_SECOND_RATE
            + cpu_seconds * self.CPU_SECOND_RATE
        )
        return CostEstimate(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            gpu_seconds=gpu_seconds,
            cpu_seconds=cpu_seconds,
            cloud_equivalent_usd=round(cloud_equivalent, 6),
        )
