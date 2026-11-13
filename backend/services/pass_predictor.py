from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from sgp4.api import Satrec

from services.propagator import (
    C_KM_S,
    doppler_hz,
    look_angles,
    propagate_at,
    range_rate_km_s,
)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def sample_pass_geometry(
    satrec: Satrec,
    obs_lat: float,
    obs_lon: float,
    obs_alt_m: float,
    start: datetime,
    end: datetime,
    step_sec: float = 5.0,
) -> list[dict]:
    """Vectorized-style loop sampling az/el/slant/range-rate."""
    points: list[dict] = []
    t = start
    delta = timedelta(seconds=step_sec)
    while t <= end:
        state = propagate_at(satrec, t)
        if state is None:
            t += delta
            continue
        az, el, slant = look_angles(
            obs_lat, obs_lon, obs_alt_m, state.ecef_km
        )
        rr = range_rate_km_s(
            obs_lat,
            obs_lon,
            obs_alt_m,
            state.ecef_km,
            state.velocity_ecef_kms,
        )
        points.append(
            {
                "timestamp": t,
                "azimuth_deg": az,
                "elevation_deg": el,
                "slant_range_km": slant,
                "range_rate_km_s": rr,
            }
        )
        t += delta
    return points


def find_passes(
    satrec: Satrec,
    obs_lat: float,
    obs_lon: float,
    obs_alt_m: float,
    start: datetime,
    hours: float = 24.0,
    min_elevation_deg: float = 10.0,
    coarse_step_sec: float = 30.0,
) -> list[dict]:
    end = start + timedelta(hours=hours)
    samples = sample_pass_geometry(
        satrec, obs_lat, obs_lon, obs_alt_m, start, end, coarse_step_sec
    )
    passes: list[dict] = []
    in_pass = False
    aos = tca = los = None
    max_el = -90.0
    aos_az = tca_az = los_az = 0.0

    for i, pt in enumerate(samples):
        el = pt["elevation_deg"]
        if not in_pass and el >= min_elevation_deg:
            in_pass = True
            aos = pt["timestamp"]
            aos_az = pt["azimuth_deg"]
            max_el = el
            tca = pt["timestamp"]
            tca_az = pt["azimuth_deg"]
        elif in_pass:
            if el > max_el:
                max_el = el
                tca = pt["timestamp"]
                tca_az = pt["azimuth_deg"]
            if el < min_elevation_deg:
                los = samples[i - 1]["timestamp"] if i > 0 else pt["timestamp"]
                los_az = samples[i - 1]["azimuth_deg"] if i > 0 else pt["azimuth_deg"]
                passes.append(
                    {
                        "aos": aos,
                        "tca": tca,
                        "los": los,
                        "max_elevation_deg": max_el,
                        "aos_azimuth_deg": aos_az,
                        "los_azimuth_deg": los_az,
                        "tca_azimuth_deg": tca_az,
                    }
                )
                in_pass = False
                max_el = -90.0

    if in_pass and aos and tca:
        los = samples[-1]["timestamp"]
        los_az = samples[-1]["azimuth_deg"]
        passes.append(
            {
                "aos": aos,
                "tca": tca,
                "los": los,
                "max_elevation_deg": max_el,
                "aos_azimuth_deg": aos_az,
                "los_azimuth_deg": los_az,
                "tca_azimuth_deg": tca_az,
            }
        )

    return passes


def high_res_pass_curve(
    satrec: Satrec,
    obs_lat: float,
    obs_lon: float,
    obs_alt_m: float,
    aos: datetime,
    los: datetime,
    freq_mhz: float,
    step_sec: float = 2.0,
) -> list[dict]:
    samples = sample_pass_geometry(
        satrec, obs_lat, obs_lon, obs_alt_m, aos, los, step_sec
    )
    curve: list[dict] = []
    for pt in samples:
        if pt["elevation_deg"] < 0:
            continue
        d_hz = doppler_hz(freq_mhz, pt["range_rate_km_s"])
        rx = freq_mhz + d_hz / 1e6
        curve.append(
            {
                "timestamp": _iso(pt["timestamp"]),
                "azimuth_deg": pt["azimuth_deg"],
                "elevation_deg": pt["elevation_deg"],
                "slant_range_km": pt["slant_range_km"],
                "range_rate_km_s": pt["range_rate_km_s"],
                "doppler_hz": d_hz,
                "rx_freq_mhz": rx,
            }
        )
    return curve


def predict_passes_with_curve(
    satrec: Satrec,
    obs_lat: float,
    obs_lon: float,
    obs_alt_m: float,
    freq_mhz: float,
    now: datetime | None = None,
) -> tuple[list[dict], list[dict]]:
    now = now or datetime.now(timezone.utc)
    raw = find_passes(satrec, obs_lat, obs_lon, obs_alt_m, now)
    events = [
        {
            "aos": _iso(p["aos"]),
            "tca": _iso(p["tca"]),
            "los": _iso(p["los"]),
            "max_elevation_deg": p["max_elevation_deg"],
            "aos_azimuth_deg": p["aos_azimuth_deg"],
            "los_azimuth_deg": p["los_azimuth_deg"],
            "tca_azimuth_deg": p["tca_azimuth_deg"],
        }
        for p in raw
    ]
    next_curve: list[dict] = []
    if raw:
        p0 = raw[0]
        next_curve = high_res_pass_curve(
            satrec,
            obs_lat,
            obs_lon,
            obs_alt_m,
            p0["aos"],
            p0["los"],
            freq_mhz,
        )
    return events, next_curve
