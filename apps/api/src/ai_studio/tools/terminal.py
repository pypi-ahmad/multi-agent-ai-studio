from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass
from os import getenv
from pathlib import Path

from ai_studio.core.config import get_settings


def _allowed_root() -> Path:
    configured = Path(getenv("AI_STUDIO_ALLOWED_ROOT", "/home/ahmad/AI")).expanduser().resolve()
    if configured.exists():
        return configured
    fallback = Path("/app").resolve()
    if fallback.exists():
        return fallback
    return configured


ALLOWED_ROOT = _allowed_root()
_BLOCKED_PATTERNS = {
    "rm -rf /",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",
    "shutdown",
    "reboot",
}


@dataclass(slots=True)
class CommandResult:
    stdout: str
    stderr: str
    returncode: int


def _assert_cwd_allowed(cwd: str) -> Path:
    resolved = Path(cwd).expanduser().resolve()
    if not str(resolved).startswith(str(ALLOWED_ROOT)):
        raise ValueError("cwd outside allowed root")
    return resolved


def _assert_command_safe(command: str) -> None:
    lowered = command.lower()
    if any(pattern in lowered for pattern in _BLOCKED_PATTERNS):
        raise ValueError("Command blocked by safety policy")


async def _run_host_command(command: str, safe_cwd: Path, timeout_seconds: int) -> CommandResult:
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=str(safe_cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=max(timeout_seconds, 1))
        return CommandResult(
            stdout=stdout.decode("utf-8", errors="ignore"),
            stderr=stderr.decode("utf-8", errors="ignore"),
            returncode=process.returncode if process.returncode is not None else 1,
        )
    except TimeoutError:
        process.kill()
        await process.communicate()
        return CommandResult(stdout="", stderr=f"Command timed out after {timeout_seconds}s", returncode=124)


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _container_cwd(safe_cwd: Path) -> str:
    try:
        relative = safe_cwd.relative_to(ALLOWED_ROOT)
    except ValueError:
        return "/workspace"
    if str(relative) in {"", "."}:
        return "/workspace"
    return f"/workspace/{relative.as_posix()}"


async def _run_container_command(command: str, safe_cwd: Path, timeout_seconds: int) -> CommandResult:
    settings = get_settings()
    process = await asyncio.create_subprocess_exec(
        "docker",
        "run",
        "--rm",
        "--network",
        settings.tool_container_network,
        "--cpus",
        str(settings.tool_container_cpus),
        "--memory",
        settings.tool_container_memory,
        "-v",
        f"{ALLOWED_ROOT}:/workspace",
        "-w",
        _container_cwd(safe_cwd),
        settings.tool_sandbox_image,
        "sh",
        "-lc",
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=max(timeout_seconds, 1))
        return CommandResult(
            stdout=stdout.decode("utf-8", errors="ignore"),
            stderr=stderr.decode("utf-8", errors="ignore"),
            returncode=process.returncode if process.returncode is not None else 1,
        )
    except TimeoutError:
        process.kill()
        await process.communicate()
        return CommandResult(stdout="", stderr=f"Command timed out after {timeout_seconds}s", returncode=124)


async def run_command(command: str, cwd: str = "/home/ahmad/AI", timeout_seconds: int = 120) -> CommandResult:
    _assert_command_safe(command)
    safe_cwd = _assert_cwd_allowed(cwd if cwd else str(ALLOWED_ROOT))
    settings = get_settings()

    use_container = settings.tool_execution_mode == "container_preferred" and _docker_available()
    if use_container:
        container_result = await _run_container_command(command, safe_cwd, timeout_seconds)
        if container_result.returncode in {0, 124}:
            return container_result
        host_result = await _run_host_command(command, safe_cwd, timeout_seconds)
        fallback_stderr = "[sandbox fallback] container execution failed; used host runner."
        merged_stderr = "\n".join(filter(None, [fallback_stderr, container_result.stderr, host_result.stderr]))
        return CommandResult(stdout=host_result.stdout, stderr=merged_stderr, returncode=host_result.returncode)

    return await _run_host_command(command, safe_cwd, timeout_seconds)
