"""Two-stage TCA conjunction screening."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.optimize import brentq

from app.propagation.sgp4_batch import propagate_batch


def _relative_range_dot(
    sat_a,
    sat_b,
    t0: datetime,
    sec: float,
) -> float:
    dt = t0 + timedelta(seconds=float(sec))
    batch = propagate_batch([sat_a, sat_b], [dt])
    if not (batch.valid[0, 0] and batch.valid[1, 0]):
        return 0.0
    r_rel = batch.r_teme_km[0, 0] - batch.r_teme_km[1, 0]
    v_rel = batch.v_teme_km_s[0, 0] - batch.v_teme_km_s[1, 0]
    return float(np.dot(r_rel, v_rel))


def screen_conjunctions(
    satrecs: list,
    norad_ids: list[int],
    start: datetime,
    hours: float = 24.0,
    coarse_step_s: float = 60.0,
    screening_radius_km: float = 50.0,
) -> list[dict]:
    """Stage1 apogee/perigee filter → Stage2 bounding sphere → Stage3 brentq TCA."""
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    n = len(satrecs)
    if n < 2:
        return []

    # Stage 1: mean-motion derived semi-major axis band overlap
    # a ≈ (μ)^{1/3} / n^{2/3}; use period proxy from satrec.no (rad/min)
    mu = 398600.4418  # km^3/s^2
    a_km = []
    for s in satrecs:
        n_rad_s = s.no / 60.0  # rad/s
        a_km.append((mu / (n_rad_s**2)) ** (1.0 / 3.0) if n_rad_s > 0 else 7000.0)
    a_km = np.asarray(a_km)
    ecc = np.asarray([s.ecco for s in satrecs])
    rp = a_km * (1 - ecc)
    ra = a_km * (1 + ecc)

    pairs: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            # radial bands overlap with margin
            if rp[i] - screening_radius_km <= ra[j] and rp[j] - screening_radius_km <= ra[i]:
                pairs.append((i, j))

    # Stage 2: coarse grid
    n_t = int(hours * 3600 / coarse_step_s) + 1
    times = [start + timedelta(seconds=k * coarse_step_s) for k in range(n_t)]
    batch = propagate_batch(satrecs, times)
    alerts: list[dict] = []

    for i, j in pairs:
        r_i = batch.r_teme_km[i]  # (n_t, 3)
        r_j = batch.r_teme_km[j]
        valid = batch.valid[i] & batch.valid[j]
        sep = np.linalg.norm(r_i - r_j, axis=-1)
        sep = np.where(valid, sep, np.inf)
        close = sep < screening_radius_km
        if not np.any(close):
            continue
        # Find brackets where separation has a local minimum (range-rate sign change)
        r_rel = r_i - r_j
        v_rel = batch.v_teme_km_s[i] - batch.v_teme_km_s[j]
        rd = np.sum(r_rel * v_rel, axis=-1)
        for k in range(n_t - 1):
            if not (valid[k] and valid[k + 1]):
                continue
            if rd[k] * rd[k + 1] > 0:
                continue
            if sep[k] > 2 * screening_radius_km and sep[k + 1] > 2 * screening_radius_km:
                continue
            # Stage 3: brentq on ρ̇ = 0
            t0 = times[k]
            try:
                root = brentq(
                    lambda s, a=satrecs[i], b=satrecs[j], t=t0: _relative_range_dot(a, b, t, s),
                    0.0,
                    coarse_step_s,
                    xtol=0.05,
                )
            except ValueError:
                continue
            tca = t0 + timedelta(seconds=root)
            b2 = propagate_batch([satrecs[i], satrecs[j]], [tca])
            if not (b2.valid[0, 0] and b2.valid[1, 0]):
                continue
            r_rel_t = b2.r_teme_km[0, 0] - b2.r_teme_km[1, 0]
            v_rel_t = b2.v_teme_km_s[0, 0] - b2.v_teme_km_s[1, 0]
            miss = float(np.linalg.norm(r_rel_t))
            if miss > screening_radius_km:
                continue
            alerts.append(
                {
                    "primary_norad": norad_ids[i],
                    "secondary_norad": norad_ids[j],
                    "tca": tca.astimezone(timezone.utc).isoformat(),
                    "miss_distance_km": miss,
                    "relative_speed_km_s": float(np.linalg.norm(v_rel_t)),
                    "screening_radius_km": screening_radius_km,
                }
            )
    # Deduplicate by pair + rounded TCA minute
    seen: set[tuple] = set()
    uniq: list[dict] = []
    for a in alerts:
        key = (a["primary_norad"], a["secondary_norad"], a["tca"][:16])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(a)
    return uniq
