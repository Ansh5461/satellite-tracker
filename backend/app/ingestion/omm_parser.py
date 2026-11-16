"""Parse CelesTrak OMM JSON and TLE text into normalized records."""

from __future__ import annotations

from datetime import datetime, timezone

from sgp4.api import Satrec
from sgp4.conveniences import sat_epoch_datetime


def _epoch_age_h(epoch: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    if epoch.tzinfo is None:
        epoch = epoch.replace(tzinfo=timezone.utc)
    return (now - epoch.astimezone(timezone.utc)).total_seconds() / 3600.0


def record_from_tle_lines(
    name: str,
    line1: str,
    line2: str,
    *,
    stale_hours: float = 48.0,
    fetched_at: datetime | None = None,
) -> dict:
    sat = Satrec.twoline2rv(line1, line2)
    epoch = sat_epoch_datetime(sat)
    if epoch.tzinfo is None:
        epoch = epoch.replace(tzinfo=timezone.utc)
    age = _epoch_age_h(epoch)
    norad = int(line1[2:7])
    fetched_at = fetched_at or datetime.now(timezone.utc)
    return {
        "norad_id": norad,
        "name": name.strip(),
        "line1": line1.strip(),
        "line2": line2.strip(),
        "epoch_iso": epoch.astimezone(timezone.utc).isoformat(),
        "bstar": float(sat.bstar),
        "mean_motion_rev_per_day": float(sat.no * 1440.0 / (2 * np_pi())),
        "eccentricity": float(sat.ecco),
        "inclination_deg": float(np_degrees(sat.inclo)),
        "epoch_age_h": age,
        "stale_warning": age > stale_hours,
        "fetched_at_iso": fetched_at.astimezone(timezone.utc).isoformat(),
    }


def np_pi() -> float:
    return 3.141592653589793


def np_degrees(rad: float) -> float:
    return rad * 180.0 / np_pi()


def parse_omm_json(
    payload: list[dict] | dict,
    *,
    stale_hours: float = 48.0,
    fetched_at: datetime | None = None,
) -> list[dict]:
    objs = payload if isinstance(payload, list) else [payload]
    out: list[dict] = []
    for obj in objs:
        name = (obj.get("OBJECT_NAME") or obj.get("SATNAME") or "UNKNOWN").strip()
        line1 = obj.get("TLE_LINE1") or obj.get("LINE1")
        line2 = obj.get("TLE_LINE2") or obj.get("LINE2")
        if not line1 or not line2:
            # Build from mean elements if present — fall back skip
            continue
        try:
            out.append(
                record_from_tle_lines(
                    name, line1.strip(), line2.strip(), stale_hours=stale_hours, fetched_at=fetched_at
                )
            )
        except Exception:
            continue
    return out


def parse_tle_text(
    raw: str,
    *,
    stale_hours: float = 48.0,
    fetched_at: datetime | None = None,
) -> list[dict]:
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
    entries: list[dict] = []
    i = 0
    while i < len(lines):
        if (
            i + 2 < len(lines)
            and lines[i + 1].startswith("1 ")
            and lines[i + 2].startswith("2 ")
        ):
            name, line1, line2 = lines[i], lines[i + 1], lines[i + 2]
            try:
                entries.append(
                    record_from_tle_lines(
                        name, line1, line2, stale_hours=stale_hours, fetched_at=fetched_at
                    )
                )
            except Exception:
                pass
            i += 3
            continue
        i += 1
    return entries
