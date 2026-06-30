# FAQ

## Is this cloud-dependent?
No. Primary runtime is local Ollama.

## Can I add external providers later?
Yes. Runtime uses adapter-friendly service boundaries.

## Why ARQ over Celery?
Async-native integration with FastAPI and lighter local operations.

## Does it support multi-user?
Schema and RBAC model are ready; current release is single-owner local-first.
