from __future__ import annotations

from app.ingestion.omm_parser import parse_tle_text, record_from_tle_lines


def test_parse_tle_text(iss_tle):
    l1, l2 = iss_tle
    raw = f"ISS (ZARYA)\n{l1}\n{l2}\n"
    recs = parse_tle_text(raw)
    assert len(recs) == 1
    assert recs[0]["norad_id"] == 25544
    assert "bstar" in recs[0]


def test_stale_warning_flag(iss_tle):
    l1, l2 = iss_tle
    rec = record_from_tle_lines("ISS", l1, l2, stale_hours=0.0)
    # epoch is 2024 → age >> 0 with stale_hours=0
    assert rec["stale_warning"] is True
