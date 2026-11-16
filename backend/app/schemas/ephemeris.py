"""Ephemeris / catalog schemas. Units annotated in Field descriptions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OMMRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    norad_id: int = Field(description="NORAD catalog number [-]")
    name: str
    line1: str
    line2: str
    epoch_iso: str = Field(description="TLE epoch as ISO-8601 UTC")
    bstar: float = Field(description="SGP4 B* drag term [1/earth radii]")
    mean_motion_rev_per_day: float = Field(description="Mean motion [rev/day]")
    eccentricity: float = Field(description="Eccentricity [-]")
    inclination_deg: float = Field(description="Inclination [deg]")
    epoch_age_h: float = Field(description="Age of TLE epoch relative to now [h]")
    stale_warning: bool = Field(description="True if epoch_age_h > 48 h")
    fetched_at_iso: str = Field(description="Ingestion timestamp ISO-8601 UTC")


class CatalogItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    norad_id: int
    name: str
    epoch_iso: str
    epoch_age_h: float
    stale_warning: bool
    bstar: float = Field(description="B* [1/earth radii]")
    bstar_trend: float | None = Field(
        default=None, description="Linear fit slope of B* vs epoch [1/earth radii / day]"
    )
    inclination_deg: float
    eccentricity: float
    mean_motion_rev_per_day: float


class CatalogResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    satellites: list[CatalogItem]
    source: str = "celestrak"
