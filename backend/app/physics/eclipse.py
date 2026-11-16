"""Cylindrical / conical Earth shadow (umbra & penumbra)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
from scipy.optimize import brentq

from app.physics.sun import AU_KM, sun_unit_teme
from app.propagation.geodesy import WGS84_A_KM

R_SUN_KM = 695_700.0
R_EARTH_KM = WGS84_A_KM


def shadow_function(
    r_teme_km: np.ndarray,
    sun_hat_teme: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Conical shadow function ν ∈ [0,1] and discrete state labels.

    Returns
    -------
    nu : ndarray — 1 sunlit, (0,1) penumbra, 0 umbra
    state : ndarray[str] — 'sunlit' | 'penumbra' | 'umbra'
    """
    r = np.asarray(r_teme_km, dtype=np.float64)
    s = np.asarray(sun_hat_teme, dtype=np.float64)
    # Project sat onto plane perpendicular to Sun
    r_dot_s = np.sum(r * s, axis=-1)
    # Satellite is sunlit if on sunward side with no Earth occultation
    r_perp = r - r_dot_s[..., None] * s
    sep = np.linalg.norm(r_perp, axis=-1)
    r_mag = np.linalg.norm(r, axis=-1)

    # Apparent angular radii from satellite
    # Distance sat→sun ≈ AU (LEO correction negligible for geometry)
    a_sun = np.arctan(R_SUN_KM / AU_KM)
    a_earth = np.arcsin(np.clip(R_EARTH_KM / np.maximum(r_mag, R_EARTH_KM + 1), 0, 1))
    # Angle between -r and sun (satellite looking at Earth vs Sun)
    # Vertical angle between satellite-Earth and satellite-Sun directions
    # Using cylindrical prefilter: nightside if r·s < 0 and sep < R_E
    nightside = r_dot_s < 0.0

    # Angle between sun and satellite position vectors from Earth centre
    cos_psi = np.clip(r_dot_s / np.maximum(r_mag, 1e-12), -1.0, 1.0)
    psi = np.arccos(cos_psi)  # 0 = sunward

    # Penumbra / umbra cone half-angles from Earth centre
    # Simplified Vallado conical model
    x = r_mag * np.sin(psi)
    # Horizontal distance from shadow axis (anti-sun)
    # Umbra radius at satellite distance along anti-sun axis:
    sat_along = -r_dot_s  # positive when on night side
    # Cone geometry
    penumbra_angle = np.arctan((R_SUN_KM + R_EARTH_KM) / AU_KM)
    umbra_angle = np.arctan((R_SUN_KM - R_EARTH_KM) / AU_KM)
    # Radius of penumbra/umbra cylinders/cones at distance sat_along
    # Using similar triangles from Sun-Earth
    pen_r = R_EARTH_KM + sat_along * np.tan(penumbra_angle)
    umb_r = R_EARTH_KM - sat_along * np.tan(np.abs(umbra_angle))

    nu = np.ones(r.shape[:-1], dtype=np.float64)
    state = np.full(r.shape[:-1], "sunlit", dtype=object)

    in_pen = nightside & (sep < pen_r) & (sep >= np.maximum(umb_r, 0))
    in_umb = nightside & (sep < np.maximum(umb_r, 0))

    # Smooth penumbra fraction
    width = np.maximum(pen_r - np.maximum(umb_r, 0), 1e-6)
    frac = np.clip((pen_r - sep) / width, 0.0, 1.0)
    nu = np.where(in_umb, 0.0, np.where(in_pen, 1.0 - frac, 1.0))
    state = np.where(in_umb, "umbra", np.where(in_pen, "penumbra", "sunlit"))
    return nu, state


def classify_eclipse(
    r_teme_km: np.ndarray,
    jd_tt: np.ndarray,
    fr_tt: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    sun = sun_unit_teme(jd_tt, fr_tt)
    # Broadcast sun to match r if needed
    if sun.ndim < r_teme_km.ndim:
        sun = np.broadcast_to(sun, r_teme_km.shape)
    return shadow_function(r_teme_km, sun)


def find_eclipse_events(
    satrec,
    start: datetime,
    hours: float = 24.0,
    step_s: float = 30.0,
) -> list[dict]:
    """Coarse sample + brentq boundaries for penumbra/umbra entry/exit."""
    from app.propagation.sgp4_batch import propagate_single

    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    n = int(hours * 3600 / step_s) + 1
    times = [start + timedelta(seconds=i * step_s) for i in range(n)]
    batch = propagate_single(satrec, times)
    # Use TT approx = UT1 for sun
    nu, state = classify_eclipse(
        batch.r_teme_km[0],
        batch.timescales.jd_tt,
        batch.timescales.fr_tt,
    )
    events: list[dict] = []
    for kind, target in (("penumbra", "penumbra"), ("umbra", "umbra")):
        in_shadow = state == target
        # Also treat umbra as inside penumbra for penumbra events
        if kind == "penumbra":
            in_shadow = (state == "penumbra") | (state == "umbra")
        flips = np.where(np.diff(in_shadow.astype(int)) != 0)[0]
        i = 0
        while i < len(flips):
            idx = int(flips[i])
            entering = bool(in_shadow[idx + 1])
            t0, t1 = times[idx], times[idx + 1]

            def f(sec: float, tgt=target, enter=entering) -> float:
                dt = t0 + timedelta(seconds=float(sec))
                b = propagate_single(satrec, [dt])
                _, st = classify_eclipse(
                    b.r_teme_km[0], b.timescales.jd_tt, b.timescales.fr_tt
                )
                val = 1.0 if st[0] == tgt or (tgt == "penumbra" and st[0] == "umbra") else -1.0
                return val if enter else -val

            try:
                root = brentq(lambda s: f(s), 0.0, step_s, xtol=0.05)
            except ValueError:
                root = step_s / 2
            boundary = t0 + timedelta(seconds=root)
            if entering:
                # look for exit
                if i + 1 < len(flips):
                    idx2 = int(flips[i + 1])
                    t2, t3 = times[idx2], times[idx2 + 1]

                    def f2(sec: float, tgt=target) -> float:
                        dt = t2 + timedelta(seconds=float(sec))
                        b = propagate_single(satrec, [dt])
                        _, st = classify_eclipse(
                            b.r_teme_km[0], b.timescales.jd_tt, b.timescales.fr_tt
                        )
                        inside = st[0] == tgt or (tgt == "penumbra" and st[0] == "umbra")
                        return 1.0 if not inside else -1.0

                    try:
                        root2 = brentq(f2, 0.0, step_s, xtol=0.05)
                    except ValueError:
                        root2 = step_s / 2
                    exit_t = t2 + timedelta(seconds=root2)
                    events.append(
                        {
                            "entry": boundary.astimezone(timezone.utc).isoformat(),
                            "exit": exit_t.astimezone(timezone.utc).isoformat(),
                            "kind": kind,
                            "duration_s": (exit_t - boundary).total_seconds(),
                        }
                    )
                    i += 2
                    continue
            i += 1
    return events
