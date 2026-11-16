"""Relativistic Doppler shift and drift rate."""

from __future__ import annotations

import numpy as np

C_M_S = 299_792_458.0
C_KM_S = C_M_S / 1000.0


def relativistic_doppler_hz(
    freq_hz: float | np.ndarray,
    range_rate_km_s: np.ndarray,
    speed_km_s: np.ndarray | None = None,
) -> np.ndarray:
    """Special-relativistic Doppler for a downlink (source = satellite).

    Classical term: Δf = -f0 * ρ̇/c
    Transverse/relativistic correction via time-dilation γ when speed is supplied:

        f_r = f0 / [γ (1 + ρ̇/c)]   (receiver at rest in ITRS approximation)

    where γ = 1/√(1-v²/c²). For LEO the transverse term is ~0.5 Hz at L-band.
    """
    f0 = np.asarray(freq_hz, dtype=np.float64)
    rr = np.asarray(range_rate_km_s, dtype=np.float64)
    beta_r = rr / C_KM_S
    if speed_km_s is None:
        # Classical (longitudinal only)
        return -f0 * beta_r
    v = np.asarray(speed_km_s, dtype=np.float64)
    beta2 = (v / C_KM_S) ** 2
    gamma = 1.0 / np.sqrt(np.maximum(1.0 - beta2, 1e-30))
    # Source moving; receiver approx at rest → f_r = f0 / [γ (1 + ρ̇/c)]
    # (sign: positive range-rate = receding → redshift)
    return f0 / (gamma * (1.0 + beta_r)) - f0


def doppler_drift_hz_s(
    freq_hz: float,
    range_rate_km_s: np.ndarray,
    range_accel_km_s2: np.ndarray,
) -> np.ndarray:
    """ḟ ≈ -f0 * ρ̈ / c  [Hz/s]."""
    return -float(freq_hz) * np.asarray(range_accel_km_s2, dtype=np.float64) / C_KM_S


def range_accel_from_state(
    rho_itrs_km: np.ndarray,
    v_rel_itrs_km_s: np.ndarray,
    a_rel_itrs_km_s2: np.ndarray | None = None,
) -> np.ndarray:
    """ρ̈ = (v·v + ρ·a)/ρ - (ρ·v)²/ρ³ ; if a unknown, approximate a=0."""
    rho = np.asarray(rho_itrs_km, dtype=np.float64)
    v = np.asarray(v_rel_itrs_km_s, dtype=np.float64)
    r = np.linalg.norm(rho, axis=-1)
    r = np.maximum(r, 1e-12)
    rv = np.sum(rho * v, axis=-1)
    vv = np.sum(v * v, axis=-1)
    if a_rel_itrs_km_s2 is None:
        ra = 0.0
    else:
        a = np.asarray(a_rel_itrs_km_s2, dtype=np.float64)
        ra = np.sum(rho * a, axis=-1)
    return (vv + ra) / r - (rv**2) / (r**3)
