"""WebSocket telemetry — fan-out pre-serialized Redis frames."""

from __future__ import annotations

import asyncio
import logging

import orjson
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.streaming.hub import observer_key
from app.streaming.serialization import loads

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/v1/telemetry")
async def ws_telemetry(
    websocket: WebSocket,
    norad: int,
    lat: float = 0.0,
    lon: float = 0.0,
    alt_m: float = 0.0,
    freq_hz: float = 137.1e6,
):
    await websocket.accept()
    hub = websocket.app.state.hub
    redis = websocket.app.state.redis
    okey = observer_key(lat, lon, alt_m, freq_hz)
    await hub.register_observer(okey)

    channel_obs = f"frames:obs:{okey}:{norad}"
    channel_global = "frames:global"
    q_obs = hub.subscribe(channel_obs)
    q_global = hub.subscribe(channel_global)

    # Catch-up: push last global frame immediately so UI isn't empty on connect.
    try:
        latest = await redis.get("frames:global:latest")
        if latest:
            await q_global.put(bytes(latest) if isinstance(latest, (bytes, bytearray)) else latest)
    except Exception:
        pass

    last_obs_mono = 0.0

    async def _next_bytes() -> tuple[bytes, str]:
        nonlocal last_obs_mono
        while True:
            get_obs = asyncio.create_task(q_obs.get())
            get_glb = asyncio.create_task(q_global.get())
            done, pending = await asyncio.wait(
                {get_obs, get_glb},
                return_when=asyncio.FIRST_COMPLETED,
                timeout=5.0,
            )
            for t in pending:
                t.cancel()
            if not done:
                return b'{"type":"ping"}', "ping"
            task = next(iter(done))
            raw = task.result()
            # Prefer observer-specific frames (include az/el/doppler).
            if task is get_obs:
                last_obs_mono = asyncio.get_running_loop().time()
                return raw, "obs"
            # Drop global ticks while observer frames are fresh (< 2.5s).
            if asyncio.get_running_loop().time() - last_obs_mono < 2.5:
                continue
            return raw, "global"

    try:
        while True:
            data, source = await _next_bytes()
            try:
                obj = loads(data)
            except Exception:
                await websocket.send_bytes(data)
                continue
            if isinstance(obj, dict) and obj.get("type") == "ping":
                await websocket.send_text('{"type":"ping"}')
                continue
            if source == "global" and isinstance(obj, dict) and "satellites" in obj:
                match = [s for s in obj["satellites"] if s.get("norad_id") == norad]
                if not match:
                    continue
                payload = {
                    "timestamp": obj["timestamp"],
                    "tick_id": obj["tick_id"],
                    "satellite": match[0],
                    "observer": None,
                    "degraded_iers": obj.get("degraded_iers", False),
                }
                await websocket.send_bytes(orjson.dumps(payload))
            else:
                await websocket.send_bytes(data if isinstance(data, (bytes, bytearray)) else orjson.dumps(obj))
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("ws closed: %s", exc)
    finally:
        hub.unsubscribe(channel_obs, q_obs)
        hub.unsubscribe(channel_global, q_global)


@router.websocket("/ws/telemetry/{norad_id}")
async def ws_telemetry_legacy(
    websocket: WebSocket,
    norad_id: int,
    lat: float | None = None,
    lon: float | None = None,
    alt_m: float = 0.0,
    freq_mhz: float = 137.1,
):
    await ws_telemetry(
        websocket,
        norad=norad_id,
        lat=lat or 0.0,
        lon=lon or 0.0,
        alt_m=alt_m,
        freq_hz=freq_mhz * 1e6,
    )
