"""Catalog service: Redis-backed OMM store with JSON fallback."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from redis.asyncio import Redis
from sgp4.api import Satrec

from app.config import get_settings
from app.ingestion.cache import EphemerisCache
from app.ingestion.celestrak_client import CelesTrakClient
from app.ingestion.omm_parser import parse_omm_json, record_from_tle_lines
from app.schemas.ephemeris import CatalogItem, CatalogResponse, OMMRecord

logger = logging.getLogger(__name__)
FALLBACK_PATH = Path(__file__).resolve().parents[2] / "data" / "tle_fallback.json"


class CatalogService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.cache = EphemerisCache(redis)
        self.client = CelesTrakClient()
        self.settings = get_settings()

    async def refresh_all(self, force: bool = False, remote: bool = True) -> int:
        # Always seed fallback first so the API stays usable offline / behind 403s.
        await self._load_fallback_into_redis()
        if not remote:
            return len(self.settings.norad_ids)
        try:
            records = await self.client.fetch_catalog()
        except Exception as exc:
            logger.error("catalog refresh failed: %s", exc)
            return 0
        if not records:
            return 0
        for rec in records.values():
            await self.cache.set_record(rec)
        # Merge remote into on-disk fallback without wiping unrelated entries.
        self._merge_persist_fallback(list(records.values()))
        return len(records)

    def refresh_remote_background(self) -> None:
        """Non-blocking CelesTrak update; never blocks startup or the ticker loop."""
        import asyncio

        async def _run() -> None:
            try:
                await self.refresh_all(remote=True)
            except Exception as exc:
                logger.warning("background catalog refresh failed: %s", exc)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_run())
        except RuntimeError:
            pass

    def _merge_persist_fallback(self, records: list[dict]) -> None:
        FALLBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing: dict[int, dict] = {}
        if FALLBACK_PATH.exists():
            try:
                for obj in json.loads(FALLBACK_PATH.read_text()):
                    existing[int(obj["NORAD_CAT_ID"])] = obj
            except Exception:
                existing = {}
        for r in records:
            existing[int(r["norad_id"])] = {
                "NORAD_CAT_ID": r["norad_id"],
                "OBJECT_NAME": r["name"],
                "TLE_LINE1": r["line1"],
                "TLE_LINE2": r["line2"],
            }
        payload = list(existing.values())
        FALLBACK_PATH.write_text(json.dumps(payload, indent=2))

    async def _load_fallback_into_redis(self) -> None:
        if not FALLBACK_PATH.exists():
            return
        data = json.loads(FALLBACK_PATH.read_text())
        for obj in data:
            try:
                nid = int(obj["NORAD_CAT_ID"])
                # Don't clobber a fresher Redis entry with disk fallback.
                if await self.cache.get(nid):
                    continue
                recs = parse_omm_json([obj], stale_hours=self.settings.epoch_stale_hours)
                for r in recs:
                    await self.cache.set_record(r)
            except Exception:
                continue

    def _fallback_record(self, norad_id: int) -> dict | None:
        if not FALLBACK_PATH.exists():
            return None
        try:
            data = json.loads(FALLBACK_PATH.read_text())
        except Exception:
            return None
        for obj in data:
            if int(obj.get("NORAD_CAT_ID", -1)) != norad_id:
                continue
            try:
                recs = parse_omm_json([obj], stale_hours=self.settings.epoch_stale_hours)
                return recs[0] if recs else None
            except Exception:
                return None
        return None

    async def get_record(self, norad_id: int) -> OMMRecord | None:
        # Seed from on-disk fallback before any upstream call so cold starts never block.
        if not await self.cache.get(norad_id):
            fb = self._fallback_record(norad_id)
            if fb:
                await self.cache.set_record(fb)

        async def fetch() -> dict | None:
            try:
                items = await self.client.fetch_by_norad(norad_id)
                if items:
                    return items[0]
            except Exception as exc:
                logger.warning("upstream fetch %s failed: %s", norad_id, exc)
            return self._fallback_record(norad_id)

        raw = await self.cache.get_or_revalidate(norad_id, fetch)
        if not raw:
            return None
        return OMMRecord(**raw)

    async def list_catalog(self) -> CatalogResponse:
        items: list[CatalogItem] = []
        for nid in self.settings.norad_ids:
            rec = await self.get_record(nid)
            if not rec:
                continue
            trend = await self.cache.bstar_trend(nid)
            items.append(
                CatalogItem(
                    norad_id=rec.norad_id,
                    name=rec.name,
                    epoch_iso=rec.epoch_iso,
                    epoch_age_h=rec.epoch_age_h,
                    stale_warning=rec.stale_warning,
                    bstar=rec.bstar,
                    bstar_trend=trend,
                    inclination_deg=rec.inclination_deg,
                    eccentricity=rec.eccentricity,
                    mean_motion_rev_per_day=rec.mean_motion_rev_per_day,
                )
            )
        return CatalogResponse(satellites=items)

    async def satrec_for(self, norad_id: int) -> tuple[Satrec, OMMRecord] | None:
        rec = await self.get_record(norad_id)
        if not rec:
            return None
        return Satrec.twoline2rv(rec.line1, rec.line2), rec

    async def all_satrecs(self) -> list[tuple[int, str, Satrec]]:
        out: list[tuple[int, str, Satrec]] = []
        for nid in self.settings.norad_ids:
            pair = await self.satrec_for(nid)
            if pair:
                sat, rec = pair
                out.append((nid, rec.name, sat))
        return out
