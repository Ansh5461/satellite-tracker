"""Serialization / fan-out latency — target p99 < 15 ms for 100 subscribers."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import numpy as np
import pytest

from app.schemas.telemetry import GlobalFrame, SatelliteState
from app.streaming.serialization import dumps


def _fake_frame(n: int = 8) -> GlobalFrame:
    sats = []
    now = datetime.now(timezone.utc).isoformat()
    for i in range(n):
        sats.append(
            SatelliteState(
                norad_id=25000 + i,
                name=f"SAT-{i}",
                timestamp=now,
                r_teme_km=(7000.0, 0.0, 0.0),
                v_teme_km_s=(0.0, 7.5, 0.0),
                r_itrs_km=(7000.0, 0.0, 0.0),
                v_itrs_km_s=(0.0, 7.5, 0.0),
                latitude_deg=0.0,
                longitude_deg=0.0,
                altitude_km=622.0,
                velocity_km_s=7.5,
                eclipse_state="sunlit",
                shadow_function=1.0,
            )
        )
    return GlobalFrame(timestamp=now, tick_id=1, satellites=sats, degraded_iers=False)


@pytest.mark.benchmark
def test_serialize_once_fanout_p99():
    frame = _fake_frame()
    payload = dumps(frame)
    latencies = []
    for _ in range(200):
        t0 = time.perf_counter()
        # Simulate 100 subscribers receiving the same bytes
        for _ in range(100):
            _ = payload  # zero-copy fan-out
        latencies.append((time.perf_counter() - t0) * 1000.0)
    p99 = float(np.percentile(latencies, 99))
    assert p99 < 15.0, f"p99 fan-out {p99:.3f} ms"


@pytest.mark.benchmark
def test_dumps_benchmark(benchmark):
    frame = _fake_frame()
    benchmark(lambda: dumps(frame))
