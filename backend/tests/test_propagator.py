"""Unit tests for frame transforms and look angles."""

from datetime import datetime, timezone

import numpy as np
import pytest
from sgp4.api import Satrec

from services.propagator import (
    ecef_to_geodetic,
    gmst_rad,
    julian_date,
    look_angles,
    observer_ecef,
    propagate_at,
    teme_to_ecef,
)

# ISS sample TLE (updates periodically; good for structural tests)
ISS_L1 = "1 25544U 98067A   26317.40012392  .00008768  00000+0  16503-3 0  9996"
ISS_L2 = "2 25544  51.6324 281.7005 0007366  20.9423 339.1866 15.49350588594886"


@pytest.fixture
def iss_satrec() -> Satrec:
    return Satrec.twoline2rv(ISS_L1, ISS_L2)


def test_gmst_at_j2000():
    gmst = gmst_rad(2451545, 0.0)
    # ~280.46 degrees at J2000.0 (Vallado GMST)
    assert 4.85 < gmst < 4.95


def test_teme_ecef_roundtrip_equator():
    jd = julian_date(datetime(2024, 6, 21, 12, 0, 0, tzinfo=timezone.utc))
    r_teme = np.array([7000.0, 0.0, 0.0])
    r_ecef = teme_to_ecef(r_teme, jd[0], jd[1])
    assert np.linalg.norm(r_ecef) == pytest.approx(7000.0, rel=1e-6)


def test_geodetic_equator():
    lat, lon, alt = ecef_to_geodetic(np.array([6378.137, 0.0, 0.0]))
    assert lat == pytest.approx(0.0, abs=1e-3)
    assert lon == pytest.approx(0.0, abs=1e-3)
    assert alt == pytest.approx(0.0, abs=0.5)


def test_propagate_iss_returns_state(iss_satrec: Satrec):
    dt = datetime.now(timezone.utc)
    state = propagate_at(iss_satrec, dt)
    assert state is not None
    assert 300 < state.altitude_km < 500
    assert 7.0 < state.velocity_kms < 8.5


def test_look_angles_elevation_positive_above_horizon(iss_satrec: Satrec):
    dt = datetime.now(timezone.utc)
    state = propagate_at(iss_satrec, dt)
    assert state is not None
    # Observer near subsatellite point should see high elevation
    az, el, slant = look_angles(
        state.latitude_deg, state.longitude_deg, 0.0, state.ecef_km
    )
    assert el > 80.0
    assert slant < 500
