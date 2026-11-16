"""Topocentric ENU / SEZ geometry (vectorized)."""

from __future__ import annotations

import numpy as np

from app.propagation.geodesy import observer_ecef


def enu_rotation_matrix(lat_deg: float, lon_deg: float) -> np.ndarray:
    """ECEF/ITRS → ENU rotation, shape (3, 3)."""
    lat = np.deg2rad(lat_deg)
    lon = np.deg2rad(lon_deg)
    sl, cl = np.sin(lat), np.cos(lat)
    slo, clo = np.sin(lon), np.cos(lon)
    return np.array(
        [
            [-slo, clo, 0.0],
            [-sl * clo, -sl * slo, cl],
            [cl * clo, cl * slo, sl],
        ],
        dtype=np.float64,
    )


def sez_rotation_matrix(lat_deg: float, lon_deg: float) -> np.ndarray:
    """ECEF/ITRS → SEZ (south-east-zenith), shape (3, 3)."""
    # SEZ = [[sl*clo, sl*slo, -cl], [-slo, clo, 0], [cl*clo, cl*slo, sl]]
    lat = np.deg2rad(lat_deg)
    lon = np.deg2rad(lon_deg)
    sl, cl = np.sin(lat), np.cos(lat)
    slo, clo = np.sin(lon), np.cos(lon)
    return np.array(
        [
            [sl * clo, sl * slo, -cl],
            [-slo, clo, 0.0],
            [cl * clo, cl * slo, sl],
        ],
        dtype=np.float64,
    )


def look_angles(
    obs_lat_deg: float,
    obs_lon_deg: float,
    obs_alt_m: float,
    r_sat_itrs_km: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (az_deg, el_deg, slant_km) for sat positions shape (..., 3)."""
    r_sat = np.asarray(r_sat_itrs_km, dtype=np.float64)
    r_obs = observer_ecef(obs_lat_deg, obs_lon_deg, obs_alt_m)
    rho_itrs = r_sat - r_obs
    rot = enu_rotation_matrix(obs_lat_deg, obs_lon_deg)
    enu = np.einsum("ij,...j->...i", rot, rho_itrs)
    east, north, up = enu[..., 0], enu[..., 1], enu[..., 2]
    slant = np.linalg.norm(rho_itrs, axis=-1)
    az = np.rad2deg(np.arctan2(east, north)) % 360.0
    el = np.rad2deg(np.arctan2(up, np.hypot(east, north)))
    return az, el, slant


def range_rate_km_s(
    obs_lat_deg: float,
    obs_lon_deg: float,
    obs_alt_m: float,
    r_sat_itrs_km: np.ndarray,
    v_sat_itrs_km_s: np.ndarray,
) -> np.ndarray:
    """Range rate [km/s]; fixed ground station (v_obs ≈ 0 in ITRS)."""
    r_sat = np.asarray(r_sat_itrs_km, dtype=np.float64)
    v_sat = np.asarray(v_sat_itrs_km_s, dtype=np.float64)
    r_obs = observer_ecef(obs_lat_deg, obs_lon_deg, obs_alt_m)
    rho = r_sat - r_obs
    slant = np.linalg.norm(rho, axis=-1, keepdims=True)
    slant = np.maximum(slant, 1e-12)
    rho_hat = rho / slant
    return np.sum(v_sat * rho_hat, axis=-1)
