"""RF link-budget schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LinkBudgetConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    freq_hz: float = Field(description="Carrier frequency [Hz]")
    eirp_dbw: float = Field(default=5.0, description="Spacecraft EIRP [dBW]")
    gt_db_k: float = Field(default=-20.0, description="Ground station G/T [dB/K]")
    bandwidth_hz: float = Field(default=40e3, description="Noise bandwidth [Hz]")


class LinkBudgetResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    slant_range_km: float
    fspl_db: float = Field(description="Free-space path loss [dB]")
    cnr_db: float | None = Field(default=None, description="Carrier-to-noise ratio [dB]")
    band: str = Field(description="vhf | uhf | lband | other")
