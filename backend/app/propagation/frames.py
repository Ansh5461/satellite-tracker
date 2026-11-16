"""TEME → PEF → ITRS rotations with polar motion. All arrays are (... , 3)."""

from __future__ import annotations

import numpy as np

from app.propagation.timescales import gmst82_rad

# WGS-84 Earth rotation rate [rad/s]
OMEGA_E_RAD_S = 7.2921150e-5


def _rotz(theta: np.ndarray) -> np.ndarray:
    """Stack of R3(theta) matrices, shape (n, 3, 3)."""
    c = np.cos(theta)
    s = np.sin(theta)
    n = theta.shape[0]
    r = np.zeros((n, 3, 3), dtype=np.float64)
    r[:, 0, 0] = c
    r[:, 0, 1] = s
    r[:, 1, 0] = -s
    r[:, 1, 1] = c
    r[:, 2, 2] = 1.0
    return r


def _polar_motion_matrix(xp_rad: np.ndarray, yp_rad: np.ndarray) -> np.ndarray:
    """W = R2(xp) @ R1(yp) (small-angle PEF→ITRS), shape (n, 3, 3)."""
    # For tiny angles: [[1, 0, -xp], [0, 1, yp], [xp, -yp, 1]] approx
    n = xp_rad.shape[0]
    w = np.zeros((n, 3, 3), dtype=np.float64)
    cx, sx = np.cos(xp_rad), np.sin(xp_rad)
    cy, sy = np.cos(yp_rad), np.sin(yp_rad)
    # R1(yp)
    r1 = np.zeros((n, 3, 3), dtype=np.float64)
    r1[:, 0, 0] = 1.0
    r1[:, 1, 1] = cy
    r1[:, 1, 2] = sy
    r1[:, 2, 1] = -sy
    r1[:, 2, 2] = cy
    # R2(xp)
    r2 = np.zeros((n, 3, 3), dtype=np.float64)
    r2[:, 0, 0] = cx
    r2[:, 0, 2] = -sx
    r2[:, 1, 1] = 1.0
    r2[:, 2, 0] = sx
    r2[:, 2, 2] = cx
    return np.einsum("nij,njk->nik", r2, r1)


def teme_to_pef(
    r_teme: np.ndarray,
    v_teme: np.ndarray,
    jd_ut1: np.ndarray,
    fr_ut1: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Rotate TEME → PEF (pseudo-Earth-fixed) using GMST82.

    Parameters
    ----------
    r_teme, v_teme : (..., 3) km, km/s
    jd_ut1, fr_ut1 : broadcastable to leading dims

    Returns
    -------
    r_pef, v_pef : same shape; v includes Earth-rotation term.
    """
    r_teme = np.asarray(r_teme, dtype=np.float64)
    v_teme = np.asarray(v_teme, dtype=np.float64)
    shape = r_teme.shape
    flat_r = r_teme.reshape(-1, 3)
    flat_v = v_teme.reshape(-1, 3)
    n = flat_r.shape[0]

    jd = np.broadcast_to(np.asarray(jd_ut1, dtype=np.float64), r_teme.shape[:-1]).reshape(n)
    fr = np.broadcast_to(np.asarray(fr_ut1, dtype=np.float64), r_teme.shape[:-1]).reshape(n)
    theta = gmst82_rad(jd, fr)
    r3 = _rotz(theta)
    r_pef = np.einsum("nij,nj->ni", r3, flat_r)
    v_rot = np.einsum("nij,nj->ni", r3, flat_v)
    omega = np.array([0.0, 0.0, OMEGA_E_RAD_S])
    v_pef = v_rot + np.cross(np.broadcast_to(omega, (n, 3)), r_pef)
    return r_pef.reshape(shape), v_pef.reshape(shape)


def pef_to_itrs(
    r_pef: np.ndarray,
    v_pef: np.ndarray,
    xp_rad: np.ndarray,
    yp_rad: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply polar motion PEF → ITRS."""
    r_pef = np.asarray(r_pef, dtype=np.float64)
    v_pef = np.asarray(v_pef, dtype=np.float64)
    shape = r_pef.shape
    flat_r = r_pef.reshape(-1, 3)
    flat_v = v_pef.reshape(-1, 3)
    n = flat_r.shape[0]
    xp = np.broadcast_to(np.asarray(xp_rad, dtype=np.float64), r_pef.shape[:-1]).reshape(n)
    yp = np.broadcast_to(np.asarray(yp_rad, dtype=np.float64), r_pef.shape[:-1]).reshape(n)
    w = _polar_motion_matrix(xp, yp)
    r_itrs = np.einsum("nij,nj->ni", w, flat_r)
    v_itrs = np.einsum("nij,nj->ni", w, flat_v)
    return r_itrs.reshape(shape), v_itrs.reshape(shape)


def teme_to_itrs(
    r_teme: np.ndarray,
    v_teme: np.ndarray,
    jd_ut1: np.ndarray,
    fr_ut1: np.ndarray,
    xp_rad: np.ndarray | None = None,
    yp_rad: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Full TEME → ITRS pipeline."""
    r_pef, v_pef = teme_to_pef(r_teme, v_teme, jd_ut1, fr_ut1)
    if xp_rad is None:
        xp_rad = np.zeros(np.asarray(r_teme).shape[:-1], dtype=np.float64)
    if yp_rad is None:
        yp_rad = np.zeros_like(xp_rad)
    return pef_to_itrs(r_pef, v_pef, xp_rad, yp_rad)
