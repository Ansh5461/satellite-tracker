from __future__ import annotations

import numpy as np

from app.propagation.frames import teme_to_itrs
from app.propagation.geodesy import itrs_to_geodetic, observer_ecef


def test_observer_ecef_equator():
    r = observer_ecef(0.0, 0.0, 0.0)
    assert abs(r[0] - 6378.137) < 1e-3
    assert abs(r[1]) < 1e-6
    assert abs(r[2]) < 1e-3


def test_geodetic_roundtrip():
    r = observer_ecef(28.6139, 77.209, 216.0)
    lat, lon, alt = itrs_to_geodetic(r)
    assert abs(float(lat) - 28.6139) < 1e-4
    assert abs(float(lon) - 77.209) < 1e-4
    assert abs(float(alt) - 0.216) < 1e-3


def test_teme_to_itrs_rotation_preserves_norm():
    r = np.array([[[7000.0, 0.0, 0.0]]])
    v = np.array([[[0.0, 7.5, 0.0]]])
    jd = np.array([[2451545.0]])
    fr = np.array([[0.0]])
    xp = yp = np.zeros((1, 1))
    ri, vi = teme_to_itrs(r, v, jd, fr, xp, yp)
    assert abs(np.linalg.norm(ri) - 7000.0) < 1e-6
