from __future__ import annotations

import psutil

from ai_studio.services.gpu_monitor import GpuMonitor


class SystemMetricsService:
    """Collect host CPU/RAM/GPU snapshot metrics."""

    def __init__(self, gpu_monitor: GpuMonitor) -> None:
        self._gpu_monitor = gpu_monitor

    async def snapshot(self) -> dict[str, object]:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        gpu = await self._gpu_monitor.detect()
        return {
            "cpu_percent": cpu_percent,
            "cpu_count": psutil.cpu_count(logical=True) or 0,
            "memory_total_mb": int(memory.total / (1024 * 1024)),
            "memory_used_mb": int(memory.used / (1024 * 1024)),
            "memory_percent": memory.percent,
            "gpu": {
                "available": gpu is not None,
                "name": gpu.name if gpu else "",
                "total_mb": gpu.total_mb if gpu else 0,
                "used_mb": gpu.used_mb if gpu else 0,
                "free_mb": gpu.free_mb if gpu else 0,
                "utilization_percent": gpu.utilization_percent if gpu else 0.0,
                "memory_utilization_percent": gpu.memory_utilization_percent if gpu else 0.0,
            },
        }
