# Memory Guide

## What It Does

Stores multi-layer memory records for continuity and context reuse.

## Memory Types

- `short_term`
- `long_term`
- `semantic`
- `episodic`
- `conversation`
- `project`
- `agent`

## Operations

- Create memory entry with salience + TTL.
- Query by owner with optional `scope` + `memory_type`.
- Get/update/delete specific records.
- Summarize memory slices via `POST /api/v1/memory/summary`.
- Forget by policy via `POST /api/v1/memory/forget`.
- Periodic TTL pruning for expired records.

## Best Practices

- Keep high salience for durable preferences/facts.
- Apply short TTLs to volatile run details.
- Review memory drift periodically.
