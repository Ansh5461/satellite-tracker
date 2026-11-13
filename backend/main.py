from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import (
    PassEvent,
    PassRequest,
    PassResponse,
    PassCurvePoint,
    SatelliteSummary,
    SatelliteTrackResponse,
    TrackPoint,
    OrbitalElements,
    TelemetryMessage,
)
from services.pass_predictor import predict_passes_with_curve
from services.propagator import (
    elements_from_satrec,
    footprint_radius_km,
    ground_track,
    look_angles,
    orbital_period_min,
    propagate_at,
    range_rate_km_s,
    doppler_hz,
)
from services.tle_fetcher import tle_fetcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    await tle_fetcher.refresh(force=True)

    async def periodic_refresh():
        while True:
            await asyncio.sleep(tle_fetcher.ttl_seconds)
            try:
                await tle_fetcher.refresh(force=True)
            except Exception:
                pass

    task = asyncio.create_task(periodic_refresh())
    yield
    task.cancel()


app = FastAPI(title="LEO GP Visualiser", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "satellites": len(tle_fetcher._cache)}


@app.get("/api/satellites", response_model=list[SatelliteSummary])
async def list_satellites():
    await tle_fetcher.refresh()
    now = datetime.now(timezone.utc)
    out: list[SatelliteSummary] = []
    for entry in tle_fetcher.all():
        state = propagate_at(entry.satrec, now)
        if not state:
            continue
        out.append(
            SatelliteSummary(
                norad_id=entry.norad_id,
                name=entry.name,
                latitude=state.latitude_deg,
                longitude=state.longitude_deg,
                altitude_km=state.altitude_km,
                velocity_kms=state.velocity_kms,
                period_min=orbital_period_min(entry.satrec),
            )
        )
    return out


@app.get("/api/satellite/{norad_id}/track", response_model=SatelliteTrackResponse)
async def satellite_track(norad_id: int):
    await tle_fetcher.refresh()
    entry = tle_fetcher.get(norad_id)
    if not entry:
        raise HTTPException(404, "Satellite not found")
    now = datetime.now(timezone.utc)
    state = propagate_at(entry.satrec, now)
    if not state:
        raise HTTPException(500, "Propagation failed")
    past = ground_track(entry.satrec, now, -15 * 60, 30.0)
    future = ground_track(entry.satrec, now, 95 * 60, 30.0)
    els = elements_from_satrec(entry.satrec)
    fp = footprint_radius_km(state.altitude_km)

    def to_pts(states: list) -> list[TrackPoint]:
        return [
            TrackPoint(
                timestamp=s.timestamp.isoformat(),
                latitude=s.latitude_deg,
                longitude=s.longitude_deg,
                altitude_km=s.altitude_km,
            )
            for s in states
        ]

    return SatelliteTrackResponse(
        norad_id=norad_id,
        name=entry.name,
        elements=OrbitalElements(**els),
        footprint_radius_km=fp,
        past_track=to_pts(past),
        future_track=to_pts(future),
    )


@app.post("/api/passes", response_model=PassResponse)
async def predict_passes(body: PassRequest):
    await tle_fetcher.refresh()
    entry = tle_fetcher.get(body.norad_id)
    if not entry:
        raise HTTPException(404, "Satellite not found")
    events, curve = predict_passes_with_curve(
        entry.satrec,
        body.lat,
        body.lon,
        body.alt_m,
        body.freq_mhz,
    )
    return PassResponse(
        norad_id=body.norad_id,
        passes=[PassEvent(**e) for e in events],
        next_pass_curve=[PassCurvePoint(**c) for c in curve],
    )


@app.websocket("/ws/telemetry/{norad_id}")
async def ws_telemetry(
    websocket: WebSocket,
    norad_id: int,
    lat: float | None = None,
    lon: float | None = None,
    alt_m: float = 0.0,
    freq_mhz: float = 137.1,
):
    await websocket.accept()
    await tle_fetcher.refresh()
    entry = tle_fetcher.get(norad_id)
    if not entry:
        await websocket.close(code=4404)
        return
    try:
        while True:
            now = datetime.now(timezone.utc)
            state = propagate_at(entry.satrec, now)
            if not state:
                await asyncio.sleep(1)
                continue
            msg = TelemetryMessage(
                timestamp=state.timestamp.isoformat(),
                latitude=state.latitude_deg,
                longitude=state.longitude_deg,
                altitude_km=state.altitude_km,
                velocity_kms=state.velocity_kms,
            )
            if lat is not None and lon is not None:
                az, el, slant = look_angles(lat, lon, alt_m, state.ecef_km)
                rr = range_rate_km_s(
                    lat, lon, alt_m, state.ecef_km, state.velocity_ecef_kms
                )
                d_hz = doppler_hz(freq_mhz, rr)
                msg.azimuth_deg = az
                msg.elevation_deg = el
                msg.slant_range_km = slant
                msg.range_rate_km_s = rr
                msg.doppler_hz = d_hz
                msg.rx_freq_mhz = freq_mhz + d_hz / 1e6
            await websocket.send_text(msg.model_dump_json())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
