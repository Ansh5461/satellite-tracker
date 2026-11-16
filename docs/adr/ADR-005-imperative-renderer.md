# ADR-005: Imperative SceneController outside Svelte reactivity

## Status
Accepted

## Context
Storing Three.js meshes or per-frame buffers in Svelte stores/runes couples the 60 FPS loop to the reactive graph and causes GC/layout thrash.

## Decision
`SceneController` owns the WebGL renderer and rAF loop. Svelte only mounts/disposes and pushes keyframes. Geometry (anti-meridian split, footprints) runs in a Web Worker with transferable `Float32Array`s. Dashboard stores update at ≤2 Hz.

## Consequences
- Stable frame times; clearer ownership
- Slightly more boilerplate wiring
