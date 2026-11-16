"""WGS-84 geodesy helpers (vectorized)."""

from __future__ import annotations

import numpy as np

WGS84_A_KM = 6378.137
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)
WGS84_B_KM = WGS84_A_KM * (1.0 - WGS84_F)


def observer_ecef(
    lat_deg: np.ndarray | float,
    lon_deg: np.ndarray | float,
    alt_m: np.ndarray | float,
) -> np.ndarray:
    """Geodetic → ECEF/ITRS position [km]. Shape (..., 3)."""
    lat = np.deg2rad(np.asarray(lat_deg, dtype=np.float64))
    lon = np.deg2rad(np.asarray(lon_deg, dtype=np.float64))
    alt_km = np.asarray(alt_m, dtype=np.float64) / 1000.0
    sin_lat, cos_lat = np.sin(lat), np.cos(lat)
    n = WGS84_A_KM / np.sqrt(1.0 - WGS84_E2 * sin_lat**2)
    x = (n + alt_km) * cos_lat * np.cos(lon)
    y = (n + alt_km) * cos_lat * np.sin(lon)
    z = (n * (1.0 - WGS84_E2) + alt_km) * sin_lat
    return np.stack([x, y, z], axis=-1)


def itrs_to_geodetic(r_itrs_km: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorized iterative ECEF/ITRS → geodetic (lat[deg], lon[deg], alt[km])."""
    r = np.asarray(r_itrs_km, dtype=np.float64)
    x, y, z = r[..., 0], r[..., 1], r[..., 2]
    lon = np.arctan2(y, x)
    p = np.hypot(x, y)
    lat = np.arctan2(z, p * (1.0 - WGS84_E2))
    for _ in range(6):
        sin_lat = np.sin(lat)
        n = WGS84_A_KM / np.sqrt(1.0 - WGS84_E2 * sin_lat**2)
        lat = np.arctan2(z + WGS84_E2 * n * sin_lat, p)
    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    n = WGS84_A_KM / np.sqrt(1.0 - WGS84_E2 * sin_lat**2)
    alt = np.where(
        np.abs(cos_lat) > 1e-12,
        p / cos_lat - n,
        np.abs(z) / np.maximum(np.abs(sin_lat), 1e-15) - n,
    )
    return np.rad2deg(lat), np.rad2deg(lon), alt


def footprint_central_angle_rad(altitude_km: float, min_elevation_deg: float = 0.0) -> float:
    """Earth central angle for geometric horizon / min-elevation footprint."""
    h = float(altitude_km)
    if h <= 0:
        return 0.0
    eps = np.deg2rad(min_elevation_deg)
    ratio = WGS84_A_KM / (WGS84_A_KM + h)
    arg = np.clip(ratio * np.cos(eps), -1.0, 1.0)
    return float(np.arccos(arg) - eps)


def footprint_radius_km(altitude_km: float, min_elevation_deg: float = 0.0) -> float:
    return float(WGS84_A_KM * footprint_central_angle_rad(altitude_km, min_elevation_deg))
