from __future__ import annotations

import numpy as np

from app.physics.eclipse import shadow_function


def test_sunlit_on_dayside():
    r = np.array([7000.0, 0.0, 0.0])
    sun = np.array([1.0, 0.0, 0.0])
    nu, state = shadow_function(r, sun)
    assert float(nu) == 1.0
    assert state == "sunlit"


def test_umbra_deep_nightside():
    # Deep anti-sun, near Earth limb cylinder
    r = np.array([-7000.0, 0.0, 0.0])
    sun = np.array([1.0, 0.0, 0.0])
    nu, state = shadow_function(r, sun)
    assert state in ("umbra", "penumbra")
    assert float(nu) < 1.0
