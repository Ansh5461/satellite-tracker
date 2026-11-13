from __future__ import annotations

from pydantic import BaseModel, Field


class SatelliteSummary(BaseModel):
    norad_id: int
    name: str
    latitude: float
    longitude: float
    altitude_km: float
    velocity_kms: float
    period_min: float


class OrbitalElements(BaseModel):
    inclination_deg: float
    eccentricity: float
    mean_motion_rev_per_day: float
    epoch: str


class TrackPoint(BaseModel):
    timestamp: str
    latitude: float
    longitude: float
    altitude_km: float


class SatelliteTrackResponse(BaseModel):
    norad_id: int
    name: str
    elements: OrbitalElements
    footprint_radius_km: float
    past_track: list[TrackPoint]
    future_track: list[TrackPoint]


class PassRequest(BaseModel):
    norad_id: int
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    alt_m: float = Field(default=0, ge=0)
    freq_mhz: float = Field(default=137.1, gt=0)


class PassEvent(BaseModel):
    aos: str
    tca: str
    los: str
    max_elevation_deg: float
    aos_azimuth_deg: float
    los_azimuth_deg: float
    tca_azimuth_deg: float


class PassCurvePoint(BaseModel):
    timestamp: str
    azimuth_deg: float
    elevation_deg: float
    slant_range_km: float
    range_rate_km_s: float
    doppler_hz: float
    rx_freq_mhz: float


class PassResponse(BaseModel):
    norad_id: int
    passes: list[PassEvent]
    next_pass_curve: list[PassCurvePoint]


class TelemetryMessage(BaseModel):
    timestamp: str
    latitude: float
    longitude: float
    altitude_km: float
    velocity_kms: float
    azimuth_deg: float | None = None
    elevation_deg: float | None = None
    slant_range_km: float | None = None
    range_rate_km_s: float | None = None
    doppler_hz: float | None = None
    rx_freq_mhz: float | None = None
