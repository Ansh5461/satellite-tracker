# ADR-006: ProcessPoolExecutor for batch physics

## Status
Accepted

## Context
Multi-day pass prediction, conjunction screening, and attitude ODEs are CPU-bound and would stall asyncio if run inline.

## Decision
Offload jobs (`passes`, `eclipses`, `conjunctions`, `attitude`) to a `ProcessPoolExecutor`. REST handlers `await loop.run_in_executor(...)`. Live ticks stay in the ticker process.

## Consequences
- Predictable API latency under load
- Pickling overhead for job payloads (TLE lines, not Satrec objects)
