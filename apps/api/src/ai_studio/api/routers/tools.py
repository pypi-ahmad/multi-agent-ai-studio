from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ai_studio.api.deps import (
    append_audit_log,
    get_current_user,
    owner_access_guard,
    rate_limit,
    read_access_guard,
    require_confirmation_token,
    write_access_guard,
)
from ai_studio.db.session import get_db_session
from ai_studio.models.entities import User, UserRole
from ai_studio.state import get_app_state
from ai_studio.tools import filesystem, python_exec, terminal

router = APIRouter(prefix="/tools", tags=["tools"])


class FilesystemReadRequest(BaseModel):
    path: str


class FilesystemWriteRequest(BaseModel):
    path: str
    content: str
    overwrite: bool = True


class FilesystemMoveRequest(BaseModel):
    source: str
    destination: str


class FilesystemCopyRequest(BaseModel):
    source: str
    destination: str
    recursive: bool = False


class FilesystemDeleteRequest(BaseModel):
    path: str
    recursive: bool = False


class FilesystemSearchRequest(BaseModel):
    root: str
    pattern: str
    file_glob: str = "**/*"
    max_results: int = Field(default=200, ge=1, le=1000)


class FilesystemListRequest(BaseModel):
    path: str


class CommandRequest(BaseModel):
    command: str
    cwd: str = "/home/ahmad/AI"
    timeout_seconds: int = Field(default=120, ge=1, le=900)


class PythonRequest(BaseModel):
    code: str
    timeout_seconds: int = Field(default=120, ge=1, le=900)


class ToolExecuteRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    arguments: dict[str, object] = Field(default_factory=dict)


def _schema_type_matches(value: object, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    return True


def _validate_arguments(schema: dict[str, Any], arguments: dict[str, object]) -> None:
    if schema.get("type") == "object" and not isinstance(arguments, dict):
        raise HTTPException(status_code=400, detail="Tool arguments must be an object")

    properties = schema.get("properties")
    if not isinstance(properties, dict):
        properties = {}

    required = schema.get("required")
    required_keys = required if isinstance(required, list) else []
    for key in required_keys:
        if key not in arguments:
            raise HTTPException(status_code=400, detail=f"Missing required argument: {key}")

    for key, value in arguments.items():
        property_schema = properties.get(key)
        if not isinstance(property_schema, dict):
            continue
        expected_type = property_schema.get("type")
        if isinstance(expected_type, str) and not _schema_type_matches(value, expected_type):
            raise HTTPException(
                status_code=400,
                detail=f"Argument '{key}' must be type '{expected_type}'",
            )


def _ensure_tool_role(user: User, tool_name: str) -> None:
    if tool_name in {"filesystem.delete", "terminal.exec", "python.exec"}:
        if user.role != UserRole.OWNER:
            raise HTTPException(status_code=403, detail="Owner role required for this tool")
        return
    if tool_name in {"filesystem.write", "filesystem.move", "filesystem.copy"}:
        if user.role not in {UserRole.OWNER, UserRole.EDITOR}:
            raise HTTPException(status_code=403, detail="Editor or owner role required for this tool")
        return
    if user.role not in {UserRole.OWNER, UserRole.EDITOR, UserRole.VIEWER}:
        raise HTTPException(status_code=403, detail="Invalid user role")


async def _execute_tool(name: str, args: dict[str, object]) -> dict[str, object]:
    if name == "filesystem.read":
        payload = FilesystemReadRequest.model_validate(args)
        return {"content": filesystem.read_text(payload.path)}
    if name == "filesystem.list":
        payload = FilesystemListRequest.model_validate(args)
        return {"items": filesystem.list_directory(payload.path)}
    if name == "filesystem.search":
        payload = FilesystemSearchRequest.model_validate(args)
        return {
            "matches": filesystem.search_text(
                root=payload.root,
                pattern=payload.pattern,
                file_glob=payload.file_glob,
                max_results=payload.max_results,
            )
        }
    if name == "filesystem.write":
        payload = FilesystemWriteRequest.model_validate(args)
        filesystem.write_text(payload.path, payload.content, overwrite=payload.overwrite)
        return {"status": "ok", "target": payload.path}
    if name == "filesystem.move":
        payload = FilesystemMoveRequest.model_validate(args)
        filesystem.move_path(payload.source, payload.destination)
        return {"status": "ok", "target": payload.destination}
    if name == "filesystem.copy":
        payload = FilesystemCopyRequest.model_validate(args)
        filesystem.copy_path(payload.source, payload.destination, recursive=payload.recursive)
        return {"status": "ok", "target": payload.destination}
    if name == "filesystem.delete":
        payload = FilesystemDeleteRequest.model_validate(args)
        filesystem.delete_path(payload.path, recursive=payload.recursive)
        return {"status": "ok", "target": payload.path}
    if name == "terminal.exec":
        payload = CommandRequest.model_validate(args)
        result = await terminal.run_command(payload.command, cwd=payload.cwd, timeout_seconds=payload.timeout_seconds)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    if name == "python.exec":
        payload = PythonRequest.model_validate(args)
        result = await python_exec.run_python(payload.code, timeout_seconds=payload.timeout_seconds)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    raise HTTPException(status_code=404, detail=f"No runtime executor defined for tool '{name}'")


@router.get("", response_model=list[dict[str, object]])
async def list_tools(
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("tools.list")),
) -> list[dict[str, object]]:
    app_state = get_app_state()
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "destructive": tool.destructive,
            "requires_confirmation": tool.requires_confirmation,
            "schema": tool.schema,
        }
        for tool in app_state.tool_registry.list_tools()
    ]


@router.post("/execute", response_model=dict[str, object])
async def execute_tool(
    payload: ToolExecuteRequest,
    x_confirm_token: str | None = Header(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    _limit: None = Depends(rate_limit("tools.execute", rpm=60)),
) -> dict[str, object]:
    app_state = get_app_state()
    try:
        manifest = app_state.tool_registry.get(payload.name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    _ensure_tool_role(user, manifest.name)
    _validate_arguments(manifest.schema, payload.arguments)
    if manifest.requires_confirmation:
        require_confirmation_token(x_confirm_token)

    try:
        result = await _execute_tool(manifest.name, payload.arguments)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="tools.execute",
        target_type="tool",
        target_id=manifest.name,
        details={
            "destructive": manifest.destructive,
            "requires_confirmation": manifest.requires_confirmation,
            "argument_keys": sorted(payload.arguments.keys()),
        },
        commit=True,
    )
    return {
        "name": manifest.name,
        "destructive": manifest.destructive,
        "result": result,
    }


@router.post("/filesystem/read")
async def fs_read(
    payload: FilesystemReadRequest,
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("tools.fs.read")),
) -> dict[str, str]:
    return {"content": filesystem.read_text(payload.path)}


@router.post("/filesystem/list")
async def fs_list(
    payload: FilesystemListRequest,
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("tools.fs.list")),
) -> dict[str, object]:
    return {"items": filesystem.list_directory(payload.path)}


@router.post("/filesystem/search")
async def fs_search(
    payload: FilesystemSearchRequest,
    _user: User = Depends(read_access_guard()),
    _limit: None = Depends(rate_limit("tools.fs.search")),
) -> dict[str, object]:
    return {
        "matches": filesystem.search_text(
            root=payload.root,
            pattern=payload.pattern,
            file_glob=payload.file_glob,
            max_results=payload.max_results,
        )
    }


@router.post("/filesystem/write")
async def fs_write(
    payload: FilesystemWriteRequest,
    _confirm: None = Depends(require_confirmation_token),
    user: User = Depends(write_access_guard()),
    session: AsyncSession = Depends(get_db_session),
    _limit: None = Depends(rate_limit("tools.fs.write")),
) -> dict[str, str]:
    filesystem.write_text(payload.path, payload.content, overwrite=payload.overwrite)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="tools.filesystem.write",
        target_type="path",
        target_id=payload.path,
        details={"overwrite": payload.overwrite},
        commit=True,
    )
    return {"status": "ok"}


@router.post("/filesystem/move")
async def fs_move(
    payload: FilesystemMoveRequest,
    _confirm: None = Depends(require_confirmation_token),
    user: User = Depends(write_access_guard()),
    session: AsyncSession = Depends(get_db_session),
    _limit: None = Depends(rate_limit("tools.fs.move")),
) -> dict[str, str]:
    filesystem.move_path(payload.source, payload.destination)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="tools.filesystem.move",
        target_type="path",
        target_id=payload.source,
        details={"destination": payload.destination},
        commit=True,
    )
    return {"status": "ok"}


@router.post("/filesystem/copy")
async def fs_copy(
    payload: FilesystemCopyRequest,
    _confirm: None = Depends(require_confirmation_token),
    user: User = Depends(write_access_guard()),
    session: AsyncSession = Depends(get_db_session),
    _limit: None = Depends(rate_limit("tools.fs.copy")),
) -> dict[str, str]:
    filesystem.copy_path(payload.source, payload.destination, recursive=payload.recursive)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="tools.filesystem.copy",
        target_type="path",
        target_id=payload.source,
        details={"destination": payload.destination, "recursive": payload.recursive},
        commit=True,
    )
    return {"status": "ok"}


@router.post("/filesystem/delete")
async def fs_delete(
    payload: FilesystemDeleteRequest,
    _confirm: None = Depends(require_confirmation_token),
    user: User = Depends(owner_access_guard()),
    session: AsyncSession = Depends(get_db_session),
    _limit: None = Depends(rate_limit("tools.fs.delete")),
) -> dict[str, str]:
    filesystem.delete_path(payload.path, recursive=payload.recursive)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="tools.filesystem.delete",
        target_type="path",
        target_id=payload.path,
        details={"recursive": payload.recursive},
        commit=True,
    )
    return {"status": "ok"}


@router.post("/terminal/exec")
async def terminal_exec(
    payload: CommandRequest,
    _confirm: None = Depends(require_confirmation_token),
    user: User = Depends(owner_access_guard()),
    session: AsyncSession = Depends(get_db_session),
    _limit: None = Depends(rate_limit("tools.terminal.exec", rpm=40)),
) -> dict[str, object]:
    try:
        result = await terminal.run_command(
            payload.command,
            cwd=payload.cwd,
            timeout_seconds=payload.timeout_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="tools.terminal.exec",
        target_type="command",
        target_id=payload.command[:120],
        details={"cwd": payload.cwd, "returncode": result.returncode},
        commit=True,
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


@router.post("/python/exec")
async def python_run(
    payload: PythonRequest,
    _confirm: None = Depends(require_confirmation_token),
    user: User = Depends(owner_access_guard()),
    session: AsyncSession = Depends(get_db_session),
    _limit: None = Depends(rate_limit("tools.python.exec", rpm=40)),
) -> dict[str, object]:
    result = await python_exec.run_python(payload.code, timeout_seconds=payload.timeout_seconds)
    await append_audit_log(
        session,
        actor_user_id=user.id,
        action="tools.python.exec",
        target_type="snippet",
        target_id="python-snippet",
        details={"returncode": result.returncode},
        commit=True,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }
