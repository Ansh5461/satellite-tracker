from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
from sgp4.api import Satrec, jday
from sgp4.conveniences import sat_epoch_datetime

# WGS-84
WGS84_A_KM = 6378.137
WGS84_F = 1 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)
OMEGA_E_RAD_S = 7.2921150e-5  # Earth rotation rate
C_KM_S = 299792.458  # speed of light km/s


@dataclass
class GeodeticState:
    timestamp: datetime
    latitude_deg: float
    longitude_deg: float
    altitude_km: float
    velocity_kms: float
    ecef_km: np.ndarray
    velocity_ecef_kms: np.ndarray


def julian_date(dt: datetime) -> tuple[int, float]:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return jday(
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second + dt.microsecond / 1e6,
    )


def gmst_rad(jd_whole: int, jd_frac: float) -> float:
    jd = jd_whole + jd_frac
    """Greenwich Mean Sidereal Time (radians) — Vallado 3rd ed. alg. 12."""
    t_ut1 = (jd - 2451545.0) / 36525.0
    gst_sec = (
        67310.54841
        + (876600.0 * 3600.0 + 8640184.812866) * t_ut1
        + 0.093104 * t_ut1**2
        - 6.2e-6 * t_ut1**3
    )
    gst_deg = (gst_sec / 240.0) % 360.0
    return np.radians(gst_deg)


def teme_to_ecef(r_teme: np.ndarray, jd_whole: int, jd_frac: float) -> np.ndarray:
    theta = gmst_rad(jd_whole, jd_frac)
    c, s = np.cos(theta), np.sin(theta)
    rot = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
    return rot @ r_teme


def teme_vel_to_ecef(
    v_teme: np.ndarray, r_ecef: np.ndarray, jd_whole: int, jd_frac: float
) -> np.ndarray:
    """ω × r + R * v_teme"""
    theta = gmst_rad(jd_whole, jd_frac)
    c, s = np.cos(theta), np.sin(theta)
    rot = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
    omega = np.array([0.0, 0.0, OMEGA_E_RAD_S])
    return rot @ v_teme + np.cross(omega, r_ecef)


def ecef_to_geodetic(r_ecef: np.ndarray) -> tuple[float, float, float]:
    x, y, z = r_ecef
    lon = np.arctan2(y, x)
    p = np.hypot(x, y)
    lat = np.arctan2(z, p * (1 - WGS84_E2))
    for _ in range(5):
        sin_lat = np.sin(lat)
        n = WGS84_A_KM / np.sqrt(1 - WGS84_E2 * sin_lat**2)
        lat = np.arctan2(z + WGS84_E2 * n * sin_lat, p)
    sin_lat = np.sin(lat)
    n = WGS84_A_KM / np.sqrt(1 - WGS84_E2 * sin_lat**2)
    alt = p / np.cos(lat) - n if abs(np.cos(lat)) > 1e-12 else abs(z) / abs(sin_lat) - n
    return np.degrees(lat), np.degrees(lon), float(alt)


def observer_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> np.ndarray:
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    alt_km = alt_m / 1000.0
    sin_lat, cos_lat = np.sin(lat), np.cos(lat)
    n = WGS84_A_KM / np.sqrt(1 - WGS84_E2 * sin_lat**2)
    x = (n + alt_km) * cos_lat * np.cos(lon)
    y = (n + alt_km) * cos_lat * np.sin(lon)
    z = (n * (1 - WGS84_E2) + alt_km) * sin_lat
    return np.array([x, y, z])


def ecef_to_enu_matrix(lat_deg: float, lon_deg: float) -> np.ndarray:
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    sl, cl = np.sin(lat), np.cos(lat)
    slo, clo = np.sin(lon), np.cos(lon)
    return np.array(
        [
            [-slo, clo, 0],
            [-sl * clo, -sl * slo, cl],
            [cl * clo, cl * slo, sl],
        ]
    )


def look_angles(
    obs_lat: float, obs_lon: float, obs_alt_m: float, sat_ecef: np.ndarray
) -> tuple[float, float, float]:
    obs = observer_ecef(obs_lat, obs_lon, obs_alt_m)
    rho_ecef = sat_ecef - obs
    enu = ecef_to_enu_matrix(obs_lat, obs_lon) @ rho_ecef
    east, north, up = enu
    slant = float(np.linalg.norm(rho_ecef))
    az = (np.degrees(np.arctan2(east, north)) + 360.0) % 360.0
    el = np.degrees(np.arctan2(up, np.hypot(east, north)))
    return float(az), float(el), slant


def range_rate_km_s(
    obs_lat: float,
    obs_lon: float,
    obs_alt_m: float,
    sat_ecef: np.ndarray,
    sat_vel_ecef: np.ndarray,
) -> float:
    obs = observer_ecef(obs_lat, obs_lon, obs_alt_m)
    rho = sat_ecef - obs
    slant = np.linalg.norm(rho)
    if slant < 1e-6:
        return 0.0
    rho_hat = rho / slant
    # observer velocity ~ 0 for fixed ground station
    return float(np.dot(sat_vel_ecef, rho_hat))


def doppler_hz(freq_mhz: float, range_rate_km_s: float) -> float:
    f0_hz = freq_mhz * 1e6
    return -f0_hz * (range_rate_km_s / C_KM_S)


def propagate_at(satrec: Satrec, dt: datetime) -> GeodeticState | None:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    jd_whole, jd_frac = julian_date(dt)
    try:
        error, r_teme, v_teme = satrec.sgp4(jd_whole, jd_frac)
    except Exception:
        return None
    if error != 0:
        return None
    r_teme = np.asarray(r_teme, dtype=float)
    v_teme = np.asarray(v_teme, dtype=float)
    r_ecef = teme_to_ecef(r_teme, jd_whole, jd_frac)
    v_ecef = teme_vel_to_ecef(v_teme, r_ecef, jd_whole, jd_frac)
    lat, lon, alt = ecef_to_geodetic(r_ecef)
    speed = float(np.linalg.norm(v_ecef))
    return GeodeticState(
        timestamp=dt.astimezone(timezone.utc),
        latitude_deg=lat,
        longitude_deg=lon,
        altitude_km=alt,
        velocity_kms=speed,
        ecef_km=r_ecef,
        velocity_ecef_kms=v_ecef,
    )


def ground_track(
    satrec: Satrec,
    start: datetime,
    duration_sec: float,
    step_sec: float = 30.0,
) -> list[GeodeticState]:
    sign = 1 if duration_sec >= 0 else -1
    n = int(abs(duration_sec) / step_sec)
    out: list[GeodeticState] = []
    for i in range(n + 1):
        dt = start + timedelta(seconds=sign * i * step_sec)
        state = propagate_at(satrec, dt)
        if state:
            out.append(state)
    return out


def orbital_period_min(satrec: Satrec) -> float:
    """satrec.no is radians per minute (SGP4)."""
    if satrec.no <= 0:
        return 90.0
    return float((2 * np.pi) / satrec.no)


def footprint_radius_km(altitude_km: float) -> float:
    """Horizon circle radius for zero elevation (geometric)."""
    h = altitude_km
    if h <= 0:
        return 0.0
    return float(WGS84_A_KM * np.arccos(WGS84_A_KM / (WGS84_A_KM + h)))


def elements_from_satrec(satrec: Satrec) -> dict[str, float | str]:
    epoch_dt = sat_epoch_datetime(satrec)
    ecc = satrec.ecco
    incl = np.degrees(satrec.inclo)
    mm = satrec.no * 1440.0 / (2 * np.pi)  # rev/day
    return {
        "inclination_deg": float(incl),
        "eccentricity": float(ecc),
        "mean_motion_rev_per_day": float(mm),
        "epoch": epoch_dt.isoformat(),
    }
