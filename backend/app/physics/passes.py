"""Vectorized pass finder with brentq AOS/LOS and TCA refinement."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.optimize import brentq, minimize_scalar

from app.physics.doppler import (
    doppler_drift_hz_s,
    range_accel_from_state,
    relativistic_doppler_hz,
)
from app.physics.link_budget import fspl_db
from app.physics.refraction import apparent_elevation_deg
from app.propagation.geodesy import observer_ecef
from app.propagation.sgp4_batch import propagate_single
from app.propagation.topocentric import look_angles, range_rate_km_s


def _elevation_at(satrec, obs_lat, obs_lon, obs_alt_m, t0: datetime, sec: float) -> float:
    dt = t0 + timedelta(seconds=float(sec))
    b = propagate_single(satrec, [dt])
    if not b.valid[0, 0]:
        return -90.0
    _, el, _ = look_angles(obs_lat, obs_lon, obs_alt_m, b.r_itrs_km[0, 0])
    return float(el)


def predict_passes(
    satrec,
    obs_lat_deg: float,
    obs_lon_deg: float,
    obs_alt_m: float,
    freq_hz: float,
    start: datetime | None = None,
    hours: float = 24.0,
    min_elevation_deg: float = 10.0,
    coarse_step_s: float = 30.0,
    curve_step_s: float = 2.0,
) -> tuple[list[dict], list[dict]]:
    start = start or datetime.now(timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    n = int(hours * 3600 / coarse_step_s) + 1
    times = [start + timedelta(seconds=i * coarse_step_s) for i in range(n)]
    batch = propagate_single(satrec, times)
    az, el, slant = look_angles(
        obs_lat_deg, obs_lon_deg, obs_alt_m, batch.r_itrs_km[0]
    )
    el = np.where(batch.valid[0], el, -90.0)
    above = el >= min_elevation_deg

    events: list[dict] = []
    i = 0
    while i < n - 1:
        if not above[i] and above[i + 1]:
            # AOS bracket
            t_aos0 = times[i]
            try:
                aos_sec = brentq(
                    lambda s: _elevation_at(
                        satrec, obs_lat_deg, obs_lon_deg, obs_alt_m, t_aos0, s
                    )
                    - min_elevation_deg,
                    0.0,
                    coarse_step_s,
                    xtol=0.05,
                )
            except ValueError:
                aos_sec = coarse_step_s / 2
            aos = t_aos0 + timedelta(seconds=aos_sec)

            # find LOS
            j = i + 1
            while j < n - 1 and above[j]:
                j += 1
            if j >= n - 1 and above[-1]:
                los = times[-1]
                j = n - 1
            else:
                t_los0 = times[j]
                try:
                    los_sec = brentq(
                        lambda s: _elevation_at(
                            satrec, obs_lat_deg, obs_lon_deg, obs_alt_m, t_los0, s
                        )
                        - min_elevation_deg,
                        0.0,
                        coarse_step_s,
                        xtol=0.05,
                    )
                except ValueError:
                    los_sec = 0.0
                los = t_los0 + timedelta(seconds=los_sec)

            # TCA = max elevation via minimize_scalar on -el
            span = (los - aos).total_seconds()
            if span <= 1:
                i = j + 1
                continue

            def neg_el(s: float) -> float:
                return -_elevation_at(
                    satrec, obs_lat_deg, obs_lon_deg, obs_alt_m, aos, s
                )

            res = minimize_scalar(neg_el, bounds=(0.0, span), method="bounded", options={"xatol": 0.1})
            tca = aos + timedelta(seconds=float(res.x))
            max_el = -float(res.fun)

            # Azimuths at AOS/TCA/LOS
            def az_at(dt: datetime) -> float:
                b = propagate_single(satrec, [dt])
                a, _, _ = look_angles(obs_lat_deg, obs_lon_deg, obs_alt_m, b.r_itrs_km[0, 0])
                return float(a)

            events.append(
                {
                    "aos": aos.astimezone(timezone.utc).isoformat(),
                    "tca": tca.astimezone(timezone.utc).isoformat(),
                    "los": los.astimezone(timezone.utc).isoformat(),
                    "max_elevation_deg": max_el,
                    "aos_azimuth_deg": az_at(aos),
                    "los_azimuth_deg": az_at(los),
                    "tca_azimuth_deg": az_at(tca),
                    "max_doppler_hz": None,
                    "min_fspl_db": None,
                }
            )
            i = j + 1
        else:
            i += 1

    # High-res curve for next pass
    curve: list[dict] = []
    if events:
        e0 = events[0]
        aos = datetime.fromisoformat(e0["aos"])
        los = datetime.fromisoformat(e0["los"])
        n_c = int((los - aos).total_seconds() / curve_step_s) + 1
        cts = [aos + timedelta(seconds=k * curve_step_s) for k in range(n_c)]
        if not cts:
            return events, curve
        cb = propagate_single(satrec, cts)
        caz, cel, cslant = look_angles(
            obs_lat_deg, obs_lon_deg, obs_alt_m, cb.r_itrs_km[0]
        )
        crr = range_rate_km_s(
            obs_lat_deg, obs_lon_deg, obs_alt_m, cb.r_itrs_km[0], cb.v_itrs_km_s[0]
        )
        speed = np.linalg.norm(cb.v_itrs_km_s[0], axis=-1)
        doppler = relativistic_doppler_hz(freq_hz, crr, speed)
        r_obs = observer_ecef(obs_lat_deg, obs_lon_deg, obs_alt_m)
        rho = cb.r_itrs_km[0] - r_obs
        accel = range_accel_from_state(rho, cb.v_itrs_km_s[0])
        drift = doppler_drift_hz_s(freq_hz, crr, accel)
        fspl = fspl_db(cslant, freq_hz)
        el_app = apparent_elevation_deg(cel)

        max_d = None
        min_f = None
        for k, t in enumerate(cts):
            if not cb.valid[0, k] or cel[k] < 0:
                continue
            d_hz = float(doppler[k])
            f_db = float(fspl[k])
            max_d = d_hz if max_d is None else max(max_d, abs(d_hz))
            min_f = f_db if min_f is None else min(min_f, f_db)
            curve.append(
                {
                    "timestamp": t.astimezone(timezone.utc).isoformat(),
                    "azimuth_deg": float(caz[k]),
                    "elevation_deg": float(cel[k]),
                    "elevation_apparent_deg": float(el_app[k]),
                    "slant_range_km": float(cslant[k]),
                    "range_rate_km_s": float(crr[k]),
                    "doppler_hz": d_hz,
                    "doppler_drift_hz_s": float(drift[k]),
                    "fspl_db": f_db,
                    "rx_freq_hz": float(freq_hz + d_hz),
                }
            )
        events[0]["max_doppler_hz"] = max_d
        events[0]["min_fspl_db"] = min_f

    return events, curve
