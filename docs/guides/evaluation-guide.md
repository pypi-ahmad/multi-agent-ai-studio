# Evaluation Guide

## What It Does

Stores evaluation runs and computes local-to-cloud equivalent cost estimates.

## Metrics

- answer quality
- groundedness
- hallucination proxy
- latency
- tool accuracy
- retrieval quality
- reasoning quality
- code quality

## Current Implementation

- `evaluations` API persists metric score maps and dataset references.
- `estimate-cost` endpoint estimates spend from tokens + compute time.
