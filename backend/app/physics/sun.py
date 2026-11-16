"""Low-precision Sun vector in inertial / TEME-compatible frame (Vallado)."""

from __future__ import annotations

import numpy as np

AU_KM = 149_597_870.7


def sun_unit_teme(jd_tt: np.ndarray, fr_tt: np.ndarray) -> np.ndarray:
    """Approximate Sun unit vector in mean-equinox / TEME-compatible frame.

    Vallado Algorithm 16 (low precision). Accuracy ~0.01° vs astropy for
    eclipse geometry. Shape (..., 3).
    """
    jd = np.asarray(jd_tt, dtype=np.float64) + np.asarray(fr_tt, dtype=np.float64)
    t = (jd - 2451545.0) / 36525.0
    # Mean longitude / anomaly [deg]
    lambda_m = np.mod(280.460 + 36000.771 * t, 360.0)
    m = np.deg2rad(np.mod(357.528 + 35999.050 * t, 360.0))
    # Ecliptic longitude
    lambda_ecl = np.deg2rad(lambda_m + 1.915 * np.sin(m) + 0.020 * np.sin(2 * m))
    eps = np.deg2rad(23.439291 - 0.0130042 * t)
    s = np.stack(
        [
            np.cos(lambda_ecl),
            np.cos(eps) * np.sin(lambda_ecl),
            np.sin(eps) * np.sin(lambda_ecl),
        ],
        axis=-1,
    )
    return s / np.linalg.norm(s, axis=-1, keepdims=True)


def sun_position_teme_km(jd_tt: np.ndarray, fr_tt: np.ndarray) -> np.ndarray:
    return sun_unit_teme(jd_tt, fr_tt) * AU_KM
