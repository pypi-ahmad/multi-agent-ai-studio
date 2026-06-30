from __future__ import annotations

from ai_studio.services.cost_estimator import CostEstimator


def test_cost_estimator_computes_positive_cost() -> None:
    estimator = CostEstimator()
    estimate = estimator.estimate(
        prompt_tokens=1000,
        completion_tokens=500,
        latency_ms=800,
        gpu_seconds=0.5,
        cpu_seconds=1.2,
    )

    assert estimate.prompt_tokens == 1000
    assert estimate.completion_tokens == 500
    assert estimate.cloud_equivalent_usd > 0
