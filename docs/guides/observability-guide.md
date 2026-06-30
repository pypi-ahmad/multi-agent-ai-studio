# Observability Guide

## What It Does

Provides execution visibility across chat/runs, system telemetry, and evaluation quality.

## Runtime Signals

- Trace records with span timeline (`planner`, `executor`, `reviewer`, `critic`).
- Run linkage (`run_id`, status, output payload, model usage).
- Host telemetry snapshots persisted to `system_metrics`.
- GPU utilization and VRAM usage time-series.
- Evaluation aggregates and history.

## API Endpoints

- `GET /api/v1/traces`
- `GET /api/v1/traces/{trace_id}`
- `GET /api/v1/traces/{trace_id}/timeline`
- `GET /api/v1/system/health`
- `GET /api/v1/system/models`
- `GET /api/v1/system/metrics/timeseries`
- `GET /api/v1/evaluation/summary`

## Dashboards

Frontend pages wired to live API data:

- Dashboard: active runs, average stage latency, GPU/VRAM charts, eval score.
- System Monitoring: health + telemetry table/time-series.
- Evaluation: aggregate metrics + historical runs.
- Traces: trace list + drill-down timeline.

## Best Practices

- Keep `METRICS_SAMPLE_INTERVAL_SECONDS` between 3 and 10 seconds.
- Track rising VRAM + queue latency before increasing parallelism.
- Use trace drill-down to isolate slow stages and routing misses.
