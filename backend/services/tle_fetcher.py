from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from sgp4.api import Satrec

CELESTRAK_TLE_URLS = (
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=weather&FORMAT=tle",
    "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle",
)

DEFAULT_TTL = int(os.environ.get("TLE_CACHE_TTL_SECONDS", "7200"))
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FALLBACK_PATH = DATA_DIR / "tle_fallback.json"


@dataclass
class TLEEntry:
    norad_id: int
    name: str
    line1: str
    line2: str
    satrec: Satrec

    @classmethod
    def from_lines(cls, name: str, line1: str, line2: str) -> TLEEntry:
        norad = int(line1[2:7])
        satrec = Satrec.twoline2rv(line1, line2)
        return cls(
            norad_id=norad, name=name.strip(), line1=line1, line2=line2, satrec=satrec
        )

    @classmethod
    def from_gp_json(cls, obj: dict) -> TLEEntry:
        name = (obj.get("OBJECT_NAME") or obj.get("SATNAME") or "UNKNOWN").strip()
        line1 = obj.get("TLE_LINE1") or obj.get("LINE1")
        line2 = obj.get("TLE_LINE2") or obj.get("LINE2")
        if not line1 or not line2:
            raise ValueError("Record missing TLE lines")
        return cls.from_lines(name, line1.strip(), line2.strip())


def parse_tle_text(raw: str) -> list[TLEEntry]:
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
    entries: list[TLEEntry] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("1 ") and i > 0 and not lines[i - 1].startswith(
            ("1 ", "2 ")
        ):
            # orphan line1 — skip
            i += 1
            continue
        if i + 2 < len(lines) and lines[i + 1].startswith("1 ") and lines[
            i + 2
        ].startswith("2 "):
            name, line1, line2 = lines[i], lines[i + 1], lines[i + 2]
            try:
                entries.append(TLEEntry.from_lines(name, line1, line2))
            except (ValueError, TypeError):
                pass
            i += 3
            continue
        i += 1
    return entries


class TLEFetcher:
    def __init__(self, ttl_seconds: int = DEFAULT_TTL) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: dict[int, TLEEntry] = {}
        self._fetched_at: float = 0.0

    async def refresh(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and self._cache and (now - self._fetched_at) < self.ttl_seconds:
            return

        merged: dict[int, TLEEntry] = {}
        errors: list[str] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for url in CELESTRAK_TLE_URLS:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    for entry in parse_tle_text(resp.text):
                        merged[entry.norad_id] = entry
                except Exception as exc:
                    errors.append(str(exc))

        if merged:
            self._cache = merged
            self._fetched_at = now
            self._persist_fallback(merged)
            return

        if self._cache:
            return

        self._load_fallback()
        if not self._cache and errors:
            raise RuntimeError(f"Failed to load TLE data: {'; '.join(errors)}")

    def _persist_fallback(self, entries: dict[int, TLEEntry]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "NORAD_CAT_ID": e.norad_id,
                "OBJECT_NAME": e.name,
                "TLE_LINE1": e.line1,
                "TLE_LINE2": e.line2,
            }
            for e in entries.values()
        ]
        FALLBACK_PATH.write_text(json.dumps(payload, indent=2))

    def _load_fallback(self) -> None:
        if not FALLBACK_PATH.exists():
            return
        data = json.loads(FALLBACK_PATH.read_text())
        for obj in data:
            try:
                entry = TLEEntry.from_gp_json(obj)
                self._cache[entry.norad_id] = entry
            except (ValueError, KeyError, TypeError):
                continue
        self._fetched_at = time.monotonic()

    def get(self, norad_id: int) -> TLEEntry | None:
        return self._cache.get(norad_id)

    def all(self) -> list[TLEEntry]:
        return sorted(self._cache.values(), key=lambda e: e.name)


tle_fetcher = TLEFetcher()
