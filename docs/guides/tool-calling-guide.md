# Tool Calling Guide

## What It Does

Provides plugin-style tool execution for filesystem, terminal, and Python operations with confirmation, RBAC, audit logs, and rate limiting.

## Safety Model

- Tool manifests define destructive and confirmation requirements.
- Destructive tools require `X-Confirm-Token`.
- Filesystem operations constrained to `/home/ahmad/AI`.
- Unsafe shell patterns blocked.
- Terminal/Python execution has timeout guards.
- Terminal/Python prefer container-isolated execution (`TOOL_EXECUTION_MODE=container_preferred`) and fall back to host with audit-visible stderr marker.
- Destructive tool invocations are written to `audit_logs`.
- Tool endpoints are scope rate-limited through Redis.

## Built-in Tool Endpoints

- `POST /api/v1/tools/execute` (manifest-based unified executor)
- `filesystem.read`
- `filesystem.list`
- `filesystem.search`
- `filesystem.write`
- `filesystem.move`
- `filesystem.copy`
- `filesystem.delete`
- `terminal.exec`
- `python.exec`

## How To Add Custom Tool

1. Create a manifest with schema and safety flags.
2. Register manifest in `state._register_builtin_tools` or plugin loader.
3. Implement execution handler in router/service layer.
