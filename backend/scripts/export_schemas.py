"""Export Pydantic models to JSON Schema for frontend type generation."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas import (
    AttitudeSimResponse,
    CatalogResponse,
    ConjunctionResponse,
    EclipseResponse,
    GlobalFrame,
    HealthResponse,
    PassResponse,
    SatelliteTrackResponse,
    TelemetryFrame,
)

OUT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "schemas"
MODELS = {
    "TelemetryFrame": TelemetryFrame,
    "GlobalFrame": GlobalFrame,
    "HealthResponse": HealthResponse,
    "CatalogResponse": CatalogResponse,
    "PassResponse": PassResponse,
    "SatelliteTrackResponse": SatelliteTrackResponse,
    "EclipseResponse": EclipseResponse,
    "ConjunctionResponse": ConjunctionResponse,
    "AttitudeSimResponse": AttitudeSimResponse,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    combined = {}
    for name, model in MODELS.items():
        schema = model.model_json_schema()
        (OUT / f"{name}.json").write_text(json.dumps(schema, indent=2))
        combined[name] = schema
    (OUT / "all.json").write_text(json.dumps(combined, indent=2))
    # Keep generated.ts as the hand-maintained contract; JSON schemas are the export artifact.
    # Prefer `npm run gen:types` from all.json when regenerating TS from JSON Schema.
    print(f"Wrote JSON schemas to {OUT} (generated.ts is maintained separately)")


if __name__ == "__main__":
    main()
