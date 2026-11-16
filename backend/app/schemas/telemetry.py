"""Live telemetry frame schemas. Frame suffixes are mandatory."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SatelliteState(BaseModel):
    model_config = ConfigDict(frozen=True)

    norad_id: int
    name: str
    timestamp: str = Field(description="UTC ISO-8601")
    r_teme_km: tuple[float, float, float] = Field(description="Position TEME [km]")
    v_teme_km_s: tuple[float, float, float] = Field(description="Velocity TEME [km/s]")
    r_itrs_km: tuple[float, float, float] = Field(description="Position ITRS [km]")
    v_itrs_km_s: tuple[float, float, float] = Field(description="Velocity ITRS [km/s]")
    latitude_deg: float = Field(description="Geodetic latitude [deg]")
    longitude_deg: float = Field(description="Geodetic longitude [deg]")
    altitude_km: float = Field(description="Geodetic altitude [km]")
    velocity_km_s: float = Field(description="Speed in ITRS [km/s]")
    eclipse_state: str = Field(description="sunlit | penumbra | umbra")
    shadow_function: float = Field(ge=0.0, le=1.0, description="1=sunlit, 0=umbra [-]")


class ObserverGeometry(BaseModel):
    model_config = ConfigDict(frozen=True)

    azimuth_deg: float = Field(description="Azimuth from north [deg]")
    elevation_deg: float = Field(description="Geometric elevation [deg]")
    elevation_apparent_deg: float = Field(description="Refraction-corrected elevation [deg]")
    slant_range_km: float = Field(description="Slant range [km]")
    range_rate_km_s: float = Field(description="Range rate [km/s]")
    doppler_hz: float = Field(description="Relativistic Doppler shift [Hz]")
    doppler_drift_hz_s: float = Field(description="Doppler drift rate [Hz/s]")
    fspl_db: float = Field(description="Free-space path loss [dB]")
    rx_freq_hz: float = Field(description="Predicted receive frequency [Hz]")


class TelemetryFrame(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: str
    tick_id: int
    satellite: SatelliteState
    observer: ObserverGeometry | None = None
    degraded_iers: bool = False


class GlobalFrame(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: str
    tick_id: int
    satellites: list[SatelliteState]
    degraded_iers: bool = False


class HealthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    redis_ok: bool
    ticker_ok: bool
    ticker_age_s: float | None
    satellite_count: int
    degraded_iers: bool
    version: str = "2.0.0"
