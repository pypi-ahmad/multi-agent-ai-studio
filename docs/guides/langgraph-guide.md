# LangGraph Guide

## What It Does

LangGraph runs deterministic orchestration for supervisor-led multi-agent execution.

## Why It Exists

Graph orchestration enables explicit retries, validation checkpoints, and visibility into agent transitions.

## How It Works

`SupervisorRuntime` builds a graph with nodes:

1. Planner
2. Executor
3. Reviewer
4. Critic

Each node selects model dynamically via `ModelRouter`, executes task prompt, and enriches state.

## Best Practices

- Keep state small and explicit.
- Separate planning and critique prompts.
- Log model and latency metadata per node.
