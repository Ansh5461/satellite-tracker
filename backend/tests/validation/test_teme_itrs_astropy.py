"""
TEME → ITRS fidelity vs astropy (same IERS table when available).

Tolerances (<10 m position, <0.01 m/s velocity) measure implementation fidelity
against the reference transform, not absolute orbit determination accuracy.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from app.propagation.frames import teme_to_itrs
from app.propagation.timescales import utc_to_timescales


@pytest.mark.validation
def test_teme_itrs_vs_astropy():
    pytest.importorskip("astropy")
    from astropy import units as u
    from astropy.coordinates import ITRS, TEME, CartesianDifferential, CartesianRepresentation
    from astropy.time import Time

    t = Time("2020-01-01T12:00:00", scale="utc")
    r_teme = np.array([7000.0, 1000.0, 500.0])  # km
    v_teme = np.array([-1.0, 7.0, 0.5])  # km/s

    teme = TEME(
        CartesianRepresentation(r_teme * u.km).with_differentials(
            CartesianDifferential(v_teme * u.km / u.s)
        ),
        obstime=t,
    )
    itrs_ref = teme.transform_to(ITRS(obstime=t))
    r_ref = np.array(
        [
            itrs_ref.cartesian.x.to_value(u.km),
            itrs_ref.cartesian.y.to_value(u.km),
            itrs_ref.cartesian.z.to_value(u.km),
        ]
    )
    v_ref = np.array(
        [
            itrs_ref.cartesian.differentials["s"].d_x.to_value(u.km / u.s),
            itrs_ref.cartesian.differentials["s"].d_y.to_value(u.km / u.s),
            itrs_ref.cartesian.differentials["s"].d_z.to_value(u.km / u.s),
        ]
    )

    dt = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ts = utc_to_timescales([dt], auto_download=False)
    r_out, v_out = teme_to_itrs(
        r_teme.reshape(1, 1, 3),
        v_teme.reshape(1, 1, 3),
        ts.jd_ut1.reshape(1, 1),
        ts.fr_ut1.reshape(1, 1),
        ts.xp_rad.reshape(1, 1),
        ts.yp_rad.reshape(1, 1),
    )
    r_out = r_out[0, 0]
    v_out = v_out[0, 0]

    dr_m = np.linalg.norm(r_out - r_ref) * 1000.0
    dv = np.linalg.norm(v_out - v_ref)

    if ts.degraded:
        # Without polar motion / DUT1, PEF-only should still be within ~100 m typically
        assert dr_m < 500.0
        pytest.skip("IERS degraded — relaxed PEF-only check passed (<500 m)")
    assert dr_m < 10.0, f"position error {dr_m:.3f} m"
    assert dv < 0.01, f"velocity error {dv:.6f} km/s"


@pytest.mark.validation
def test_vallado_gmst_example_3_15_range():
    """GMST at J2000 epoch is near 280.46° (Vallado Ex. 3-5/3-15 family)."""
    from app.propagation.timescales import gmst82_rad

    # 2000-01-01 12:00 TT ≈ JD 2451545.0
    theta = float(gmst82_rad(np.array([2451545.0]), np.array([0.0]))[0])
    deg = np.rad2deg(theta) % 360
    assert 280.0 < deg < 281.5
