from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from sgp4.api import Satrec

from app.physics.conjunction import screen_conjunctions


def test_conjunction_screening_runs(iss_tle):
    l1, l2 = iss_tle
    # Two identical sats → miss ≈ 0 (synthetic)
    a = Satrec.twoline2rv(l1, l2)
    b = Satrec.twoline2rv(l1, l2)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    alerts = screen_conjunctions(
        [a, b],
        [25544, 25545],
        start,
        hours=1.0,
        coarse_step_s=120.0,
        screening_radius_km=10.0,
    )
    assert isinstance(alerts, list)
    # Identical elements should produce near-zero miss if TCA found
    if alerts:
        assert alerts[0]["miss_distance_km"] < 1.0
