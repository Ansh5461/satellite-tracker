"""REST API v1 — CPU work offloaded to ProcessPoolExecutor."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request

from app.propagation.geodesy import footprint_radius_km
from app.propagation.sgp4_batch import propagate_single
from app.schemas.attitude import AttitudeSimRequest, AttitudeSimResponse, AttitudeSample
from app.schemas.conjunction import ConjunctionAlert, ConjunctionResponse
from app.schemas.eclipse import EclipseEvent, EclipseResponse
from app.schemas.ephemeris import CatalogResponse
from app.schemas.passes import (
    PassCurvePoint,
    PassEvent,
    PassRequest,
    PassResponse,
    SatelliteTrackResponse,
    TrackPoint,
)
from app.schemas.telemetry import HealthResponse
from app.streaming.executor import JOBS, get_pool

router = APIRouter(prefix="/api/v1")


def _catalog(request: Request):
    return request.app.state.catalog


def _hub(request: Request):
    return request.app.state.hub


def _redis(request: Request):
    return request.app.state.redis


@router.get("/health", response_model=HealthResponse)
async def health(request: Request):
    redis_ok = False
    try:
        redis_ok = bool(await _redis(request).ping())
    except Exception:
        redis_ok = False
    age = await _hub(request).heartbeat_age()
    ticker_ok = age is not None and age < 5.0
    sat_count = 0
    try:
        # Count cached catalog keys only — never block health on CelesTrak.
        settings = request.app.state.settings
        for nid in settings.norad_ids:
            if await request.app.state.catalog.cache.get(nid):
                sat_count += 1
    except Exception:
        sat_count = 0
    from app.propagation.timescales import is_iers_degraded

    return HealthResponse(
        status="ok" if redis_ok else "degraded",
        redis_ok=redis_ok,
        ticker_ok=ticker_ok,
        ticker_age_s=age,
        satellite_count=sat_count,
        degraded_iers=is_iers_degraded(),
    )


@router.get("/catalog", response_model=CatalogResponse)
async def catalog(request: Request):
    return await _catalog(request).list_catalog()


@router.get("/satellites/{norad_id}/track", response_model=SatelliteTrackResponse)
async def satellite_track(norad_id: int, request: Request):
    pair = await _catalog(request).satrec_for(norad_id)
    if not pair:
        raise HTTPException(404, "Satellite not found")
    sat, rec = pair
    now = datetime.now(timezone.utc)
    past_times = [now - timedelta(seconds=i * 30) for i in range(30, -1, -1)]
    future_times = [now + timedelta(seconds=i * 30) for i in range(0, 191)]
    past = propagate_single(sat, past_times)
    fut = propagate_single(sat, future_times)
    alt = float(fut.altitude_km[0, 0]) if fut.valid[0, 0] else 500.0

    def to_pts(batch, times):
        pts = []
        for i, t in enumerate(times):
            if not batch.valid[0, i]:
                continue
            pts.append(
                TrackPoint(
                    timestamp=t.isoformat(),
                    latitude_deg=float(batch.latitude_deg[0, i]),
                    longitude_deg=float(batch.longitude_deg[0, i]),
                    altitude_km=float(batch.altitude_km[0, i]),
                    r_itrs_km=tuple(float(x) for x in batch.r_itrs_km[0, i]),
                    v_itrs_km_s=tuple(float(x) for x in batch.v_itrs_km_s[0, i]),
                )
            )
        return pts

    return SatelliteTrackResponse(
        norad_id=norad_id,
        name=rec.name,
        footprint_radius_km=footprint_radius_km(alt),
        past_track=to_pts(past, past_times),
        future_track=to_pts(fut, future_times),
        epoch_iso=rec.epoch_iso,
        epoch_age_h=rec.epoch_age_h,
        stale_warning=rec.stale_warning,
    )


@router.post("/passes", response_model=PassResponse)
async def predict_passes_endpoint(body: PassRequest, request: Request):
    pair = await _catalog(request).satrec_for(body.norad_id)
    if not pair:
        raise HTTPException(404, "Satellite not found")
    _, rec = pair
    payload = {
        "line1": rec.line1,
        "line2": rec.line2,
        "lat_deg": body.lat_deg,
        "lon_deg": body.lon_deg,
        "alt_m": body.alt_m,
        "freq_hz": body.freq_hz,
        "hours": body.hours,
        "min_elevation_deg": body.min_elevation_deg,
    }
    loop = asyncio.get_running_loop()
    events, curve = await loop.run_in_executor(get_pool(), JOBS["passes"], payload)
    return PassResponse(
        norad_id=body.norad_id,
        passes=[PassEvent(**e) for e in events],
        next_pass_curve=[PassCurvePoint(**c) for c in curve],
    )


@router.get("/satellites/{norad_id}/eclipses", response_model=EclipseResponse)
async def eclipses(norad_id: int, request: Request, hours: float = 24.0):
    pair = await _catalog(request).satrec_for(norad_id)
    if not pair:
        raise HTTPException(404, "Satellite not found")
    _, rec = pair
    start = datetime.now(timezone.utc)
    payload = {"line1": rec.line1, "line2": rec.line2, "start": start.isoformat(), "hours": hours}
    loop = asyncio.get_running_loop()
    events = await loop.run_in_executor(get_pool(), JOBS["eclipses"], payload)
    return EclipseResponse(
        norad_id=norad_id,
        window_start=start.isoformat(),
        window_end=(start + timedelta(hours=hours)).isoformat(),
        events=[EclipseEvent(**e) for e in events],
    )


@router.get("/conjunctions", response_model=ConjunctionResponse)
async def conjunctions(request: Request, hours: float = 24.0, radius_km: float = 50.0):
    sats = []
    for nid in request.app.state.settings.norad_ids:
        pair = await _catalog(request).satrec_for(nid)
        if pair:
            _, rec = pair
            sats.append({"norad_id": nid, "line1": rec.line1, "line2": rec.line2})
    start = datetime.now(timezone.utc)
    payload = {
        "sats": sats,
        "start": start.isoformat(),
        "hours": hours,
        "screening_radius_km": radius_km,
    }
    loop = asyncio.get_running_loop()
    alerts = await loop.run_in_executor(get_pool(), JOBS["conjunctions"], payload)
    return ConjunctionResponse(
        window_start=start.isoformat(),
        window_end=(start + timedelta(hours=hours)).isoformat(),
        alerts=[ConjunctionAlert(**a) for a in alerts],
    )


@router.post("/attitude/simulate", response_model=AttitudeSimResponse)
async def attitude_simulate(body: AttitudeSimRequest):
    payload = body.model_dump()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(get_pool(), JOBS["attitude"], payload)
    return AttitudeSimResponse(
        samples=[AttitudeSample(**s) for s in result["samples"]],
        conserved_angular_momentum_err=result["conserved_angular_momentum_err"],
    )


# Back-compat aliases used by legacy frontend during migration
@router.get("/satellites")
async def list_satellites_compat(request: Request):
    cat = await _catalog(request).list_catalog()
    now = datetime.now(timezone.utc)
    out = []
    for item in cat.satellites:
        pair = await _catalog(request).satrec_for(item.norad_id)
        if not pair:
            continue
        sat, _ = pair
        b = propagate_single(sat, [now])
        if not b.valid[0, 0]:
            continue
        out.append(
            {
                "norad_id": item.norad_id,
                "name": item.name,
                "latitude": float(b.latitude_deg[0, 0]),
                "longitude": float(b.longitude_deg[0, 0]),
                "altitude_km": float(b.altitude_km[0, 0]),
                "velocity_kms": float(__import__("numpy").linalg.norm(b.v_itrs_km_s[0, 0])),
                "period_min": float((2 * 3.141592653589793) / sat.no) if sat.no > 0 else 90.0,
                "epoch_age_h": item.epoch_age_h,
                "stale_warning": item.stale_warning,
                "bstar": item.bstar,
            }
        )
    return out
