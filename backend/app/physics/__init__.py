"""RF, eclipse, conjunction, and attitude physics."""

from app.physics.attitude import simulate_attitude
from app.physics.conjunction import screen_conjunctions
from app.physics.doppler import doppler_drift_hz_s, relativistic_doppler_hz
from app.physics.eclipse import classify_eclipse, find_eclipse_events
from app.physics.link_budget import fspl_db
from app.physics.passes import predict_passes
from app.physics.refraction import apparent_elevation_deg

__all__ = [
    "apparent_elevation_deg",
    "classify_eclipse",
    "doppler_drift_hz_s",
    "find_eclipse_events",
    "fspl_db",
    "predict_passes",
    "relativistic_doppler_hz",
    "screen_conjunctions",
    "simulate_attitude",
]
