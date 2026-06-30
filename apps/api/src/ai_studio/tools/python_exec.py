from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

from ai_studio.core.config import get_settings
from ai_studio.tools.terminal import ALLOWED_ROOT, CommandResult


async def _run_host_python(script_path: Path, timeout_seconds: int) -> CommandResult:
    process = await asyncio.create_subprocess_exec(
        "python",
        "-I",
        "-B",
        str(script_path),
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
        return CommandResult(
            stdout="",
            stderr=f"Python execution timed out after {timeout_seconds}s",
            returncode=124,
        )


async def _run_container_python(script_path: Path, timeout_seconds: int) -> CommandResult:
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
        "-v",
        f"{script_path.parent}:/sandbox",
        "-w",
        "/workspace",
        settings.tool_sandbox_image,
        "python",
        "-I",
        "-B",
        f"/sandbox/{script_path.name}",
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
        return CommandResult(
            stdout="",
            stderr=f"Python execution timed out after {timeout_seconds}s",
            returncode=124,
        )


async def run_python(code: str, timeout_seconds: int = 120) -> CommandResult:
    """Execute Python code in temporary file using isolated interpreter flags."""
    settings = get_settings()
    use_container = settings.tool_execution_mode == "container_preferred" and shutil.which("docker") is not None

    with tempfile.TemporaryDirectory(prefix="ai_studio_py_") as tmpdir:
        script_path = Path(tmpdir) / "snippet.py"
        script_path.write_text(code, encoding="utf-8")
        if use_container:
            container_result = await _run_container_python(script_path, timeout_seconds)
            if container_result.returncode in {0, 124}:
                return container_result
            host_result = await _run_host_python(script_path, timeout_seconds)
            fallback_stderr = "[sandbox fallback] container execution failed; used host runner."
            merged_stderr = "\n".join(filter(None, [fallback_stderr, container_result.stderr, host_result.stderr]))
            return CommandResult(stdout=host_result.stdout, stderr=merged_stderr, returncode=host_result.returncode)

        return await _run_host_python(script_path, timeout_seconds)
