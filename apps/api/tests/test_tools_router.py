from __future__ import annotations

from types import SimpleNamespace

import pytest
from ai_studio.api.routers.tools import _ensure_tool_role, _validate_arguments
from ai_studio.models.entities import UserRole
from fastapi import HTTPException


def test_validate_arguments_missing_required_key() -> None:
    schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}, "recursive": {"type": "boolean"}},
        "required": ["path"],
    }
    with pytest.raises(HTTPException):
        _validate_arguments(schema, {"recursive": True})


def test_validate_arguments_rejects_wrong_type() -> None:
    schema = {
        "type": "object",
        "properties": {"max_results": {"type": "integer"}},
        "required": ["max_results"],
    }
    with pytest.raises(HTTPException):
        _validate_arguments(schema, {"max_results": "100"})


def test_ensure_tool_role_owner_only_tool() -> None:
    viewer = SimpleNamespace(role=UserRole.VIEWER)
    with pytest.raises(HTTPException):
        _ensure_tool_role(viewer, "terminal.exec")


def test_ensure_tool_role_editor_allowed_for_write() -> None:
    editor = SimpleNamespace(role=UserRole.EDITOR)
    _ensure_tool_role(editor, "filesystem.write")
