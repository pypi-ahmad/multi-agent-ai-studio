from __future__ import annotations

from pathlib import Path

import pytest
from ai_studio.tools.filesystem import read_text, write_text
from fastapi import HTTPException


def test_filesystem_write_and_read(tmp_path: Path) -> None:
    target = Path("/home/ahmad/AI/multi-agent-ai-studio/.data/test-file.txt")
    write_text(str(target), "hello")
    assert read_text(str(target)) == "hello"


def test_filesystem_rejects_outside_root() -> None:
    with pytest.raises(HTTPException):
        write_text("/etc/passwd", "blocked")
