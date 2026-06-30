from __future__ import annotations

import sys

from loguru import logger


def configure_logging() -> None:
    """Configure structured JSON logging suitable for local observability ingestion."""
    logger.remove()
    logger.add(
        sys.stdout,
        serialize=True,
        level="INFO",
        backtrace=False,
        diagnose=False,
    )
