"""Vectorized SGP4 via SatrecArray — no per-timestamp Python loops."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sgp4.api import Satrec, SatrecArray

from app.propagation.frames import teme_to_itrs
from app.propagation.geodesy import itrs_to_geodetic
from app.propagation.timescales import TimeScales, utc_to_timescales


@dataclass
class BatchState:
    """Batch propagation results. Leading dims: (n_sat, n_t)."""

    r_teme_km: np.ndarray
    v_teme_km_s: np.ndarray
    r_itrs_km: np.ndarray
    v_itrs_km_s: np.ndarray
    latitude_deg: np.ndarray
    longitude_deg: np.ndarray
    altitude_km: np.ndarray
    error: np.ndarray
    timescales: TimeScales
    valid: np.ndarray


def satrecs_from_tles(lines: list[tuple[str, str]]) -> list[Satrec]:
    return [Satrec.twoline2rv(l1, l2) for l1, l2 in lines]


def propagate_batch(
    satrecs: list[Satrec],
    times_utc: list[datetime],
    *,
    auto_download: bool = False,
) -> BatchState:
    """Propagate n satellites at m timestamps with SatrecArray.

    Returns arrays shaped (n_sat, n_t, 3) for vectors and (n_sat, n_t) for scalars.
    """
    if not satrecs:
        raise ValueError("satrecs must be non-empty")
    if not times_utc:
        raise ValueError("times_utc must be non-empty")

    ts = utc_to_timescales(times_utc, auto_download=auto_download)
    arr = SatrecArray(satrecs)
    # sgp4 expects jd, fr arrays of length n_t
    err, r_teme, v_teme = arr.sgp4(ts.jd_ut1, ts.fr_ut1)
    # shapes: err (n,m), r/v (n,m,3)
    r_teme = np.asarray(r_teme, dtype=np.float64)
    v_teme = np.asarray(v_teme, dtype=np.float64)
    err = np.asarray(err, dtype=np.int32)
    valid = err == 0

    n_sat, n_t = err.shape
    # Broadcast EOP across satellites
    jd = np.broadcast_to(ts.jd_ut1, (n_sat, n_t))
    fr = np.broadcast_to(ts.fr_ut1, (n_sat, n_t))
    xp = np.broadcast_to(ts.xp_rad, (n_sat, n_t))
    yp = np.broadcast_to(ts.yp_rad, (n_sat, n_t))

    r_itrs, v_itrs = teme_to_itrs(r_teme, v_teme, jd, fr, xp, yp)
    # Mask invalid
    r_itrs = np.where(valid[..., None], r_itrs, np.nan)
    v_itrs = np.where(valid[..., None], v_itrs, np.nan)
    lat, lon, alt = itrs_to_geodetic(r_itrs)

    return BatchState(
        r_teme_km=r_teme,
        v_teme_km_s=v_teme,
        r_itrs_km=r_itrs,
        v_itrs_km_s=v_itrs,
        latitude_deg=lat,
        longitude_deg=lon,
        altitude_km=alt,
        error=err,
        timescales=ts,
        valid=valid,
    )


def propagate_single(
    satrec: Satrec,
    times_utc: list[datetime],
    *,
    auto_download: bool = False,
) -> BatchState:
    return propagate_batch([satrec], times_utc, auto_download=auto_download)
