"""Pass predictor smoke test using the new physics.passes module."""

from __future__ import annotations

from datetime import datetime, timezone

from sgp4.api import Satrec

from app.physics.passes import predict_passes


def test_predict_passes_runs(iss_tle):
    l1, l2 = iss_tle
    sat = Satrec.twoline2rv(l1, l2)
    events, curve = predict_passes(
        sat,
        28.6,
        77.2,
        200.0,
        137.1e6,
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        hours=6.0,
        coarse_step_s=60.0,
    )
    assert isinstance(events, list)
    assert isinstance(curve, list)
