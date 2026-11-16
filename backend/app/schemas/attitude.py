"""CubeSat attitude / tumbling schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AttitudeSimRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    inertia_kg_m2: tuple[float, float, float] = Field(
        default=(0.01, 0.012, 0.008), description="Principal moments [kg·m²]"
    )
    omega0_rad_s: tuple[float, float, float] = Field(
        default=(0.5, 0.1, 0.05), description="Initial body rates [rad/s]"
    )
    duration_s: float = Field(default=600.0, gt=0, le=3600)
    dt_s: float = Field(default=0.5, gt=0, le=10)


class AttitudeSample(BaseModel):
    model_config = ConfigDict(frozen=True)

    t_s: float = Field(description="Simulation time [s]")
    q_body_inertial: tuple[float, float, float, float] = Field(
        description="Quaternion (w,x,y,z) body←inertial [-]"
    )
    omega_body_rad_s: tuple[float, float, float] = Field(description="Body rates [rad/s]")
    solar_power_w: float = Field(description="Instantaneous array power [W]")
    polarization_loss_db: float = Field(description="Polarization mismatch loss [dB]")


class AttitudeSimResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    samples: list[AttitudeSample]
    conserved_angular_momentum_err: float = Field(
        description="Relative |H| drift over integration [-]"
    )
