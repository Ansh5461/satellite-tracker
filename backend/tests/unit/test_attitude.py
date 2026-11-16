from __future__ import annotations

from app.physics.attitude import simulate_attitude


def test_angular_momentum_conserved():
    out = simulate_attitude(duration_s=120.0, dt_s=1.0)
    assert out["conserved_angular_momentum_err"] < 1e-6
    assert len(out["samples"]) > 10
    assert "q_body_inertial" in out["samples"][0]
