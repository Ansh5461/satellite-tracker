"""
SGP4 fidelity checks.

NOTE: These tolerances measure *implementation fidelity* against the reference
SGP4 propagator / published verification cases, NOT absolute ephemeris truth
(SGP4 itself is ~1 km at epoch and grows with age).
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest
from sgp4.api import Satrec, jday

from app.propagation.sgp4_batch import propagate_batch

# Vallado SGP4-VER.TLE first verification satellite (published)
# From Vallado et al. / AIAA 2006-6753 verification suite (public domain test vectors)
VER_LINE1 = "1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753"
VER_LINE2 = "2 00005  34.2682 348.7242 1859667 331.7664  19.3268 10.82419157413667"


@pytest.mark.validation
def test_satrecarray_matches_scalar_sgp4():
    sat = Satrec.twoline2rv(VER_LINE1, VER_LINE2)
    # Propagate at epoch + 360 min (canonical sample)
    jd, fr = jday(2000, 6, 27, 6, 0, 0.0)  # near verification epoch window
    err_s, r_s, v_s = sat.sgp4(jd, fr)
    assert err_s == 0

    times = [datetime(2000, 6, 27, 6, 0, 0, tzinfo=timezone.utc)]
    batch = propagate_batch([sat], times)
    assert batch.valid[0, 0]
    # TEME positions should match scalar SGP4 to << 1 m (same library call)
    dr = np.linalg.norm(batch.r_teme_km[0, 0] - np.asarray(r_s)) * 1000.0  # m
    dv = np.linalg.norm(batch.v_teme_km_s[0, 0] - np.asarray(v_s))  # km/s
    assert dr < 1.0  # 1 metre
    assert dv < 1e-9


@pytest.mark.validation
def test_vallado_position_order_of_magnitude():
    sat = Satrec.twoline2rv(VER_LINE1, VER_LINE2)
    times = [datetime(2000, 6, 27, 6, 0, 0, tzinfo=timezone.utc)]
    batch = propagate_batch([sat], times)
    r = batch.r_teme_km[0, 0]
    # Highly eccentric: r should be thousands of km
    assert 5000 < np.linalg.norm(r) < 50000
