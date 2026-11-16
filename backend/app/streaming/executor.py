"""ProcessPoolExecutor for CPU-bound batch physics."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from typing import Any, Callable

from app.config import get_settings

_pool: ProcessPoolExecutor | None = None


def get_pool() -> ProcessPoolExecutor:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = ProcessPoolExecutor(max_workers=settings.process_pool_workers)
    return _pool


def shutdown_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.shutdown(wait=False, cancel_futures=True)
        _pool = None


def _predict_passes_job(payload: dict) -> tuple[list[dict], list[dict]]:
    from sgp4.api import Satrec

    from app.physics.passes import predict_passes

    sat = Satrec.twoline2rv(payload["line1"], payload["line2"])
    return predict_passes(
        sat,
        payload["lat_deg"],
        payload["lon_deg"],
        payload["alt_m"],
        payload["freq_hz"],
        hours=payload.get("hours", 24.0),
        min_elevation_deg=payload.get("min_elevation_deg", 10.0),
    )


def _eclipse_job(payload: dict) -> list[dict]:
    from datetime import datetime, timezone

    from sgp4.api import Satrec

    from app.physics.eclipse import find_eclipse_events

    sat = Satrec.twoline2rv(payload["line1"], payload["line2"])
    start = datetime.fromisoformat(payload["start"]).astimezone(timezone.utc)
    return find_eclipse_events(sat, start, hours=payload.get("hours", 24.0))


def _conjunction_job(payload: dict) -> list[dict]:
    from datetime import datetime, timezone

    from sgp4.api import Satrec

    from app.physics.conjunction import screen_conjunctions

    satrecs = [Satrec.twoline2rv(a["line1"], a["line2"]) for a in payload["sats"]]
    norads = [a["norad_id"] for a in payload["sats"]]
    start = datetime.fromisoformat(payload["start"]).astimezone(timezone.utc)
    return screen_conjunctions(
        satrecs,
        norads,
        start,
        hours=payload.get("hours", 24.0),
        screening_radius_km=payload.get("screening_radius_km", 50.0),
    )


def _attitude_job(payload: dict) -> dict:
    from app.physics.attitude import simulate_attitude

    return simulate_attitude(
        inertia_kg_m2=tuple(payload["inertia_kg_m2"]),
        omega0_rad_s=tuple(payload["omega0_rad_s"]),
        duration_s=payload["duration_s"],
        dt_s=payload["dt_s"],
    )


JOBS: dict[str, Callable[..., Any]] = {
    "passes": _predict_passes_job,
    "eclipses": _eclipse_job,
    "conjunctions": _conjunction_job,
    "attitude": _attitude_job,
}
