"""Conjunction screening schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ConjunctionAlert(BaseModel):
    model_config = ConfigDict(frozen=True)

    primary_norad: int
    secondary_norad: int
    tca: str = Field(description="Time of closest approach UTC ISO-8601")
    miss_distance_km: float = Field(description="Relative miss distance at TCA [km]")
    relative_speed_km_s: float = Field(description="Relative speed at TCA [km/s]")
    screening_radius_km: float = Field(description="Bounding-sphere threshold [km]")


class ConjunctionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    window_start: str
    window_end: str
    alerts: list[ConjunctionAlert]
