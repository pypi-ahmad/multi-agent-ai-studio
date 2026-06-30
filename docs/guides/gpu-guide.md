# GPU Guide

## What It Does

Detects GPU availability and reports VRAM utilization for model scheduling.

## Detection

`GpuMonitor` uses `nvidia-smi --query-gpu` and returns `None` on failure for graceful CPU fallback.

## 8GB VRAM Strategy

- Avoid loading many >6B models concurrently.
- Prioritize smaller route-appropriate models.
- Monitor free VRAM before spawning parallel heavy jobs.
