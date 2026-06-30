from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ToolManifest:
    name: str
    description: str
    destructive: bool
    requires_confirmation: bool
    schema: dict[str, Any]


class ToolRegistry:
    """In-memory plugin registry for built-in and custom tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolManifest] = {}

    def register(self, manifest: ToolManifest) -> None:
        self._tools[manifest.name] = manifest

    def list_tools(self) -> list[ToolManifest]:
        return sorted(self._tools.values(), key=lambda t: t.name)

    def get(self, name: str) -> ToolManifest:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found")
        return self._tools[name]
