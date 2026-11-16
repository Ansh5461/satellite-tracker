"""ITU-R P.834-style radio refraction for low-elevation passes."""

from __future__ import annotations

import numpy as np


def apparent_elevation_deg(
    geometric_elevation_deg: np.ndarray | float,
    *,
    N_s: float = 315.0,
) -> np.ndarray:
    """Approximate radio refraction correction (ITU-R P.834 §2).

    Δε ≈ N_s * 10⁻⁶ / tan(ε)  [rad] for ε ≳ 5°, with a soft floor near horizon
    to avoid singularity. Optical Bennett formula is intentionally NOT used.
    """
    el = np.asarray(geometric_elevation_deg, dtype=np.float64)
    el_rad = np.deg2rad(np.maximum(el, 0.1))
    delta_rad = (N_s * 1e-6) / np.tan(el_rad)
    # Cap correction near horizon (~0.7°)
    delta_rad = np.minimum(delta_rad, np.deg2rad(0.7))
    # No correction below geometric horizon
    delta_rad = np.where(el >= 0.0, delta_rad, 0.0)
    return el + np.rad2deg(delta_rad)
