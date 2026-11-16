# ADR-001: Dedicated ticker process + Redis pub/sub

## Status
Accepted

## Context
Live LEO telemetry requires 1–2 Hz state vectors for multiple satellites and observers. Running SGP4 inside each FastAPI WebSocket handler blocks the event loop (GIL) and duplicates work per subscriber.

## Decision
Run a separate `ticker` process that vectorizes propagation once per tick via `SatrecArray`, serializes with orjson once, and publishes to Redis channels (`frames:global`, `frames:obs:{key}:{norad}`). API workers subscribe and fan out pre-serialized bytes through bounded queues (drop-oldest).

## Consequences
- Horizontal scale of API replicas without multiplying CPU for propagation
- Extra operational dependency on Redis
- ~1 tick of latency before clients see updates (mitigated by Hermite dead-reckoning)
