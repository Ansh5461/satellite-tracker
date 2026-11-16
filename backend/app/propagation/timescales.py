"""UTC → UT1 / TT Julian Date hygiene with IERS polar motion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache

import numpy as np

_DEGRADED = False


@dataclass(frozen=True)
class TimeScales:
    """Julian date pairs and Earth orientation parameters."""

    jd_ut1: np.ndarray  # shape (n,) whole+frac as float64 days
    fr_ut1: np.ndarray  # fractional day for SGP4 (0..1)
    jd_tt: np.ndarray
    fr_tt: np.ndarray
    xp_rad: np.ndarray  # polar motion [rad]
    yp_rad: np.ndarray
    dut1_s: np.ndarray
    degraded: bool


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("timezone-aware UTC datetime required at API boundary")
    return dt.astimezone(timezone.utc)


@lru_cache(maxsize=1)
def _configure_iers(auto_download: bool) -> None:
    global _DEGRADED
    try:
        from astropy.utils import iers

        if not auto_download:
            iers.conf.auto_download = False
            iers.conf.auto_max_age = None
        # Prefer bundled IERS_B; fall back to degraded DUT1=0 if unavailable.
        try:
            iers.IERS_Auto.open()
            _DEGRADED = False
        except Exception:
            _DEGRADED = True
    except Exception:
        _DEGRADED = True


def is_iers_degraded() -> bool:
    return _DEGRADED


def julian_date_utc(dt: datetime) -> tuple[float, float]:
    """Return (jd_whole, jd_frac) for UTC using sgp4.jday convention."""
    from sgp4.api import jday

    dt = _ensure_utc(dt)
    return jday(
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second + dt.microsecond / 1e6,
    )


def utc_to_timescales(
    times: list[datetime] | np.ndarray,
    *,
    auto_download: bool = False,
) -> TimeScales:
    """Convert a batch of timezone-aware UTC datetimes to UT1/TT JD + EOP.

    When IERS tables are unavailable, DUT1=0 and xp=yp=0 with degraded=True.
    """
    _configure_iers(auto_download)
    dts = [_ensure_utc(t) for t in list(times)]
    n = len(dts)
    jd_ut1 = np.empty(n, dtype=np.float64)
    fr_ut1 = np.empty(n, dtype=np.float64)
    jd_tt = np.empty(n, dtype=np.float64)
    fr_tt = np.empty(n, dtype=np.float64)
    xp = np.zeros(n, dtype=np.float64)
    yp = np.zeros(n, dtype=np.float64)
    dut1 = np.zeros(n, dtype=np.float64)
    degraded = _DEGRADED

    try:
        from astropy.time import Time

        t = Time([d.isoformat() for d in dts], format="isot", scale="utc")
        # UT1
        t_ut1 = t.ut1
        jd1, jd2 = t_ut1.jd1, t_ut1.jd2
        # Split into whole + fraction matching sgp4 convention (frac in [0,1))
        total = jd1 + jd2
        whole = np.floor(total)
        frac = total - whole
        jd_ut1[:] = whole
        fr_ut1[:] = frac

        t_tt = t.tt
        total_tt = t_tt.jd1 + t_tt.jd2
        whole_tt = np.floor(total_tt)
        frac_tt = total_tt - whole_tt
        jd_tt[:] = whole_tt
        fr_tt[:] = frac_tt

        # Polar motion / DUT1 from IERS
        try:
            dut1[:] = np.asarray(t.delta_ut1_utc, dtype=np.float64)
            from astropy.utils import iers as iers_mod

            iers_table = iers_mod.earth_orientation_table.get()
            pm = iers_table.pm_xy(t)
            arcsec_to_rad = np.pi / (180.0 * 3600.0)
            xp[:] = np.asarray(pm.x.value if hasattr(pm.x, "value") else pm.x, dtype=np.float64) * arcsec_to_rad
            yp[:] = np.asarray(pm.y.value if hasattr(pm.y, "value") else pm.y, dtype=np.float64) * arcsec_to_rad
            degraded = False
        except Exception:
            degraded = True
    except Exception:
        # Fully offline fallback: treat UTC ≈ UT1, TT ≈ UTC + 69.184 s
        degraded = True
        for i, dt in enumerate(dts):
            jdw, jdf = julian_date_utc(dt)
            jd_ut1[i] = jdw
            fr_ut1[i] = jdf
            # Approximate TT = UTC + 69.184 s (2024-era leap seconds)
            tt_offset_days = 69.184 / 86400.0
            total = jdw + jdf + tt_offset_days
            jd_tt[i] = np.floor(total)
            fr_tt[i] = total - jd_tt[i]

    return TimeScales(
        jd_ut1=jd_ut1,
        fr_ut1=fr_ut1,
        jd_tt=jd_tt,
        fr_tt=fr_tt,
        xp_rad=xp,
        yp_rad=yp,
        dut1_s=dut1,
        degraded=degraded,
    )


def gmst82_rad(jd_ut1: np.ndarray, fr_ut1: np.ndarray) -> np.ndarray:
    """Greenwich Mean Sidereal Time (GMST82) [rad], Vallado / IAU-82.

    Compatible with SGP4 TEME definition (see Vallado et al. 2006).
    """
    jd = jd_ut1 + fr_ut1
    t_ut1 = (jd - 2451545.0) / 36525.0
    # seconds
    gmst_sec = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * t_ut1
        + 0.093104 * t_ut1**2
        - 6.2e-6 * t_ut1**3
    )
    # convert seconds of angle → degrees → radians, wrap
    gmst_deg = np.mod(gmst_sec / 240.0, 360.0)
    return np.deg2rad(gmst_deg)
