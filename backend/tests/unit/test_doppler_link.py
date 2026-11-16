from __future__ import annotations

import numpy as np

from app.physics.doppler import C_KM_S, doppler_drift_hz_s, relativistic_doppler_hz
from app.physics.link_budget import classify_band, fspl_db
from app.physics.refraction import apparent_elevation_deg


def test_classical_doppler_sign():
    # Approaching (negative range-rate) → blueshift (positive Δf classical)
    df = relativistic_doppler_hz(137.1e6, -1.0)  # no speed → classical
    assert df > 0


def test_relativistic_transverse_small_at_lband():
    # Pure transverse: range_rate=0, v=7.5 km/s → tiny redshift from γ
    df = float(relativistic_doppler_hz(1.7e9, 0.0, 7.5))
    # γ≈1+0.5 β² → Δf ≈ -f0 * 0.5 β² ≈ -0.53 Hz
    assert abs(df) < 2.0
    assert df < 0


def test_fspl_increases_with_range():
    a = float(fspl_db(500, 137.1e6))
    b = float(fspl_db(2000, 137.1e6))
    assert b > a
    assert classify_band(137.1e6) == "vhf"


def test_refraction_raises_elevation():
    el = apparent_elevation_deg(5.0)
    assert float(el) > 5.0


def test_drift_from_accel():
    drift = float(doppler_drift_hz_s(137.1e6, 0.0, 0.01))
    assert drift < 0
    assert abs(drift - (-137.1e6 * 0.01 / C_KM_S)) < 1e-6
