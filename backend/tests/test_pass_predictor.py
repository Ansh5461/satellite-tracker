from datetime import datetime, timezone

from sgp4.api import Satrec

from services.pass_predictor import find_passes, predict_passes_with_curve

ISS_L1 = "1 25544U 98067A   26317.40012392  .00008768  00000+0  16503-3 0  9996"
ISS_L2 = "2 25544  51.6324 281.7005 0007366  20.9423 339.1866 15.49350588594886"


def test_find_iss_passes_within_24h():
    satrec = Satrec.twoline2rv(ISS_L1, ISS_L2)
    now = datetime.now(timezone.utc)
    passes = find_passes(satrec, 28.6139, 77.209, 0.0, now, hours=24.0)
    assert isinstance(passes, list)
    if passes:
        assert passes[0]["max_elevation_deg"] >= 10.0


def test_doppler_curve_has_points():
    satrec = Satrec.twoline2rv(ISS_L1, ISS_L2)
    events, curve = predict_passes_with_curve(satrec, 28.6139, 77.209, 0.0, 137.1)
    if events:
        assert len(curve) > 10
        assert abs(curve[0]["doppler_hz"]) < 50_000  # sanity kHz scale
