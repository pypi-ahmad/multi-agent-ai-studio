from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass


@dataclass(slots=True)
class GpuStats:
    name: str
    total_mb: int
    free_mb: int
    used_mb: int
    utilization_percent: float
    memory_utilization_percent: float


class GpuMonitor:
    """GPU monitor with graceful CPU fallback when NVIDIA runtime unavailable."""

    async def detect(self) -> GpuStats | None:
        try:
            process = await asyncio.create_subprocess_exec(
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free,utilization.gpu,utilization.memory",
                "--format=csv,noheader,nounits",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            return None
        stdout, _ = await process.communicate()
        if process.returncode != 0:
            return None

        lines = stdout.decode().strip().splitlines()
        if not lines:
            return None

        parts = [part.strip() for part in lines[0].split(",")]
        if len(parts) != 5:
            return None

        name = parts[0]
        total_mb = int(re.sub(r"\D", "", parts[1]))
        free_mb = int(re.sub(r"\D", "", parts[2]))
        utilization_percent = float(re.sub(r"[^\d.]", "", parts[3]) or 0)
        memory_utilization_percent = float(re.sub(r"[^\d.]", "", parts[4]) or 0)
        return GpuStats(
            name=name,
            total_mb=total_mb,
            free_mb=free_mb,
            used_mb=total_mb - free_mb,
            utilization_percent=utilization_percent,
            memory_utilization_percent=memory_utilization_percent,
        )
