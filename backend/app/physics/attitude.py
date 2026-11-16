"""Torque-free rigid-body CubeSat attitude / tumbling simulator."""

from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp


def _quat_mul(q: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Hamilton product, scalar-first (w,x,y,z)."""
    w1, x1, y1, z1 = q
    w2, x2, y2, z2 = p
    return np.array(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ]
    )


def _normalize_quat(q: np.ndarray) -> np.ndarray:
    return q / np.linalg.norm(q)


def _euler_rhs(t: float, y: np.ndarray, I: np.ndarray) -> np.ndarray:
    """State y = [qw,qx,qy,qz, wx,wy,wz]. Torque-free Euler + quat kinematics."""
    q = y[:4]
    w = y[4:]
    Ix, Iy, Iz = I
    wx, wy, wz = w
    # Euler equations
    dwx = ((Iy - Iz) / Ix) * wy * wz
    dwy = ((Iz - Ix) / Iy) * wz * wx
    dwz = ((Ix - Iy) / Iz) * wx * wy
    # q̇ = 0.5 * q ⊗ [0, w]
    wq = np.array([0.0, wx, wy, wz])
    dq = 0.5 * _quat_mul(q, wq)
    return np.concatenate([dq, [dwx, dwy, dwz]])


def _rotate_vec_by_quat(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotate inertial vector v into body frame: v_b = q* ⊗ v ⊗ q (q = body←inertial)."""
    qn = _normalize_quat(q)
    q_conj = np.array([qn[0], -qn[1], -qn[2], -qn[3]])
    vq = np.array([0.0, v[0], v[1], v[2]])
    return _quat_mul(q_conj, _quat_mul(vq, qn))[1:]


def simulate_attitude(
    inertia_kg_m2: tuple[float, float, float] = (0.01, 0.012, 0.008),
    omega0_rad_s: tuple[float, float, float] = (0.5, 0.1, 0.05),
    duration_s: float = 600.0,
    dt_s: float = 0.5,
    sun_inertial: np.ndarray | None = None,
    observer_inertial: np.ndarray | None = None,
    p0_w: float = 10.0,
) -> dict:
    """Integrate torque-free dynamics; return samples + |H| conservation error."""
    I = np.asarray(inertia_kg_m2, dtype=np.float64)
    w0 = np.asarray(omega0_rad_s, dtype=np.float64)
    q0 = np.array([1.0, 0.0, 0.0, 0.0])
    y0 = np.concatenate([q0, w0])
    t_eval = np.arange(0.0, duration_s + 1e-9, dt_s)

    sol = solve_ivp(
        _euler_rhs,
        (0.0, duration_s),
        y0,
        t_eval=t_eval,
        args=(I,),
        method="DOP853",
        rtol=1e-10,
        atol=1e-12,
    )
    if not sol.success:
        raise RuntimeError(f"attitude integration failed: {sol.message}")

    if sun_inertial is None:
        sun_inertial = np.array([1.0, 0.0, 0.0])
    if observer_inertial is None:
        observer_inertial = np.array([0.0, 1.0, 0.0])
    sun_inertial = sun_inertial / np.linalg.norm(sun_inertial)
    observer_inertial = observer_inertial / np.linalg.norm(observer_inertial)

    # Panel normals in body frame (±X, ±Y, +Z)
    panels = np.array(
        [
            [1, 0, 0],
            [-1, 0, 0],
            [0, 1, 0],
            [0, -1, 0],
            [0, 0, 1],
        ],
        dtype=np.float64,
    )

    samples = []
    H0 = I * w0
    H0_mag = np.linalg.norm(H0)
    H_err = 0.0

    for i, t in enumerate(sol.t):
        q = _normalize_quat(sol.y[:4, i])
        w = sol.y[4:, i]
        H = I * w
        H_err = max(H_err, abs(np.linalg.norm(H) - H0_mag) / max(H0_mag, 1e-15))

        sun_b = _rotate_vec_by_quat(q, sun_inertial)
        power = 0.0
        for n in panels:
            power += p0_w * max(0.0, float(np.dot(n, sun_b))) / len(panels)

        # Dipole / linear antenna along body +Z; linear-linear pol mismatch
        ant_b = np.array([0.0, 0.0, 1.0])
        obs_b = _rotate_vec_by_quat(q, observer_inertial)
        # Polarization angle between antenna E-plane and observer direction projected
        cos_psi = abs(float(np.dot(ant_b, obs_b)))
        # linear-linear: loss = -10 log10(cos²ψ) with floor
        cos_psi = max(cos_psi, 1e-3)
        pol_loss_db = -10.0 * np.log10(cos_psi**2)

        samples.append(
            {
                "t_s": float(t),
                "q_body_inertial": tuple(float(x) for x in q),
                "omega_body_rad_s": tuple(float(x) for x in w),
                "solar_power_w": float(power),
                "polarization_loss_db": float(pol_loss_db),
            }
        )

    return {
        "samples": samples,
        "conserved_angular_momentum_err": float(H_err),
    }
