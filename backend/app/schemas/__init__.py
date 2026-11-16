"""Contract-first Pydantic v2 schemas."""

from app.schemas.attitude import AttitudeSample, AttitudeSimRequest, AttitudeSimResponse
from app.schemas.conjunction import ConjunctionAlert, ConjunctionResponse
from app.schemas.eclipse import EclipseEvent, EclipseResponse
from app.schemas.ephemeris import CatalogItem, CatalogResponse, OMMRecord
from app.schemas.passes import (
    PassCurvePoint,
    PassEvent,
    PassRequest,
    PassResponse,
    SatelliteTrackResponse,
    TrackPoint,
)
from app.schemas.rf import LinkBudgetConfig, LinkBudgetResult
from app.schemas.telemetry import (
    GlobalFrame,
    HealthResponse,
    ObserverGeometry,
    SatelliteState,
    TelemetryFrame,
)

__all__ = [
    "AttitudeSample",
    "AttitudeSimRequest",
    "AttitudeSimResponse",
    "CatalogItem",
    "CatalogResponse",
    "ConjunctionAlert",
    "ConjunctionResponse",
    "EclipseEvent",
    "EclipseResponse",
    "GlobalFrame",
    "HealthResponse",
    "LinkBudgetConfig",
    "LinkBudgetResult",
    "OMMRecord",
    "ObserverGeometry",
    "PassCurvePoint",
    "PassEvent",
    "PassRequest",
    "PassResponse",
    "SatelliteState",
    "SatelliteTrackResponse",
    "TelemetryFrame",
    "TrackPoint",
]
