# Performance Guide

## Optimization Levers

- Tune model-router scoring weights by latency and quality telemetry.
- Limit concurrent heavy runs through queue backpressure.
- Use chunk size/overlap tuned for retrieval quality vs throughput.
- Keep database indices current for run/memory/document lookups.

## Monitoring

- API latency percentiles.
- Queue depth and processing rate.
- GPU VRAM usage and OOM events.
- Retrieval latency and hit quality.
