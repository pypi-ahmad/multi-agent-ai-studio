# Agent Development Guide

## What It Does

Defines role-specific agent behavior, tools, memory scopes, and model policies.

## Why It Exists

Specialized agents improve reliability by narrowing scope and permissions.

## How It Works

- Agent definitions persisted in `agents` table.
- Workflow compiler binds agents to orchestration graph.
- Supervisor dispatches based on workflow + task context.

## Best Practices

- Use least-privilege tool access.
- Pair each agent with explicit reviewer criteria.
- Track eval performance by agent role.
