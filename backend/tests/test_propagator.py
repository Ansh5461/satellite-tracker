"""Legacy-compatible smoke tests redirected to the new propagation stack."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from sgp4.api import Satrec

from app.propagation.geodesy import observer_ecef
from app.propagation.sgp4_batch import propagate_single
from app.propagation.topocentric import look_angles


def test_observer_ecef_norm():
    r = observer_ecef(0.0, 0.0, 0.0)
    assert abs(np.linalg.norm(r) - 6378.137) < 1e-3


def test_propagate_iss_sample(iss_tle):
    l1, l2 = iss_tle
    sat = Satrec.twoline2rv(l1, l2)
    # Propagate near TLE epoch year
    t = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    b = propagate_single(sat, [t])
    # May be invalid far from epoch depending on TLE; just ensure call works
    assert b.r_teme_km.shape == (1, 1, 3)


def test_look_angles_zenith_ish():
    # At (lat=0, lon=0) local up is +X in ECEF
    r_obs = observer_ecef(0.0, 0.0, 0.0)
    r_sat = r_obs + np.array([500.0, 0.0, 0.0])
    az, el, slant = look_angles(0.0, 0.0, 0.0, r_sat)
    assert float(el) > 80.0
    assert float(slant) > 400.0
