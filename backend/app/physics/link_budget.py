"""Free-space path loss and simple link budget."""

from __future__ import annotations

import numpy as np

from app.physics.doppler import C_M_S

K_BOLTZMANN = 1.380649e-23  # J/K


def classify_band(freq_hz: float) -> str:
    f = float(freq_hz)
    if 30e6 <= f < 300e6:
        return "vhf"
    if 300e6 <= f < 1e9:
        return "uhf"
    if 1e9 <= f < 2e9:
        return "lband"
    return "other"


def fspl_db(slant_range_km: np.ndarray | float, freq_hz: float) -> np.ndarray:
    """FSPL = 20 log10(4 π d f / c) [dB], d in metres."""
    d_m = np.asarray(slant_range_km, dtype=np.float64) * 1000.0
    d_m = np.maximum(d_m, 1.0)
    return 20.0 * np.log10(4.0 * np.pi * d_m * float(freq_hz) / C_M_S)


def carrier_to_noise_db(
    slant_range_km: float,
    freq_hz: float,
    eirp_dbw: float,
    gt_db_k: float,
    bandwidth_hz: float,
) -> float:
    """CNR = EIRP - FSPL + G/T - k - 10 log10(B)."""
    fspl = float(fspl_db(slant_range_km, freq_hz))
    k_db = 10.0 * np.log10(K_BOLTZMANN)
    b_db = 10.0 * np.log10(bandwidth_hz)
    return eirp_dbw - fspl + gt_db_k - k_db - b_db
