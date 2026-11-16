from __future__ import annotations

import pytest


@pytest.fixture
def iss_tle() -> tuple[str, str]:
    # Public ISS TLE sample (epoch arbitrary; for unit geometry only)
    line1 = "1 25544U 98067A   24001.00000000  .00016717  00000-0  10270-3 0  9001"
    line2 = "2 25544  51.6400 208.9163 0006703  61.9319  73.5363 15.49578403800000"
    return line1, line2
