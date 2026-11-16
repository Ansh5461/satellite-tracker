# ADR-002: Server SGP4 + WebSocket + Hermite vs client SGP4 WASM

## Status
Accepted

## Context
Client-side SGP4 (WASM) would reduce server load but duplicates physics, complicates IERS/time-scale hygiene, and makes RF/eclipse/conjunction features harder to keep consistent.

## Decision
Keep authoritative propagation on the server. Stream 1 Hz keyframes \(\vec r, \vec v\) over WebSockets; interpolate on the client with cubic Hermite splines for 60 FPS motion.

## Consequences
- Single source of truth for frames, Doppler, eclipse
- Network dependency for smooth motion (render delay ~1.5 ticks)
- WASM SGP4 remains a future offline option
