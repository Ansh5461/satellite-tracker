# ADR-003: Stale-while-revalidate OMM caching

## Status
Accepted

## Context
CelesTrak rate-limits (429) and occasional 5xx. Fresh TLEs every few hours are sufficient for LEO visualization; blocking on upstream is unacceptable.

## Decision
Redis keys `omm:{norad}` with `fresh_until` / `stale_until`. Readers serve stale immediately; a single-flight `SET NX` lock triggers background revalidation with exponential backoff + jitter. B* history stored in sorted sets for decay trends. Epoch age > 48 h raises `stale_warning`.

## Consequences
- High availability under upstream pressure
- Possible use of aged elements (surfaced via UI badges)
