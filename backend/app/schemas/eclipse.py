"""Eclipse / illumination schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EclipseEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry: str = Field(description="UTC ISO-8601 entry into penumbra/umbra")
    exit: str = Field(description="UTC ISO-8601 exit")
    kind: str = Field(description="penumbra | umbra")
    duration_s: float = Field(description="Duration [s]")


class EclipseResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    norad_id: int
    window_start: str
    window_end: str
    events: list[EclipseEvent]
