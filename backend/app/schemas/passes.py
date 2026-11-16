"""Pass prediction schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PassRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    norad_id: int
    lat_deg: float = Field(ge=-90, le=90, description="Observer geodetic latitude [deg]")
    lon_deg: float = Field(ge=-180, le=180, description="Observer geodetic longitude [deg]")
    alt_m: float = Field(default=0.0, ge=0, description="Observer altitude [m]")
    freq_hz: float = Field(default=137.1e6, gt=0, description="Downlink carrier [Hz]")
    hours: float = Field(default=24.0, gt=0, le=168, description="Prediction window [h]")
    min_elevation_deg: float = Field(default=10.0, ge=0, le=90)


class PassEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    aos: str
    tca: str
    los: str
    max_elevation_deg: float
    aos_azimuth_deg: float
    los_azimuth_deg: float
    tca_azimuth_deg: float
    max_doppler_hz: float | None = None
    min_fspl_db: float | None = None


class PassCurvePoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: str
    azimuth_deg: float
    elevation_deg: float
    elevation_apparent_deg: float
    slant_range_km: float
    range_rate_km_s: float
    doppler_hz: float
    doppler_drift_hz_s: float
    fspl_db: float
    rx_freq_hz: float


class PassResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    norad_id: int
    passes: list[PassEvent]
    next_pass_curve: list[PassCurvePoint]


class TrackPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float
    r_itrs_km: tuple[float, float, float] | None = None
    v_itrs_km_s: tuple[float, float, float] | None = None


class SatelliteTrackResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    norad_id: int
    name: str
    footprint_radius_km: float
    past_track: list[TrackPoint]
    future_track: list[TrackPoint]
    epoch_iso: str
    epoch_age_h: float
    stale_warning: bool
