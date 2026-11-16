"""Async CelesTrak OMM/TLE fetcher with exponential backoff."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.ingestion.omm_parser import parse_omm_json, parse_tle_text

logger = logging.getLogger(__name__)

# Do not retry these — they won't succeed with the same request.
_NO_RETRY_STATUS = frozenset({400, 401, 403, 404, 410, 422})


class CelesTrakClient:
    def __init__(self, base_url: str | None = None, timeout: float = 12.0) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.celestrak_base
        self.timeout = timeout
        self.stale_hours = settings.epoch_stale_hours

    async def _get_with_backoff(self, url: str, max_retries: int = 3) -> httpx.Response:
        delay = 0.4
        last_exc: Exception | None = None
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": "gp-visualiser/2.0 (mission-control; +https://localhost)"},
            follow_redirects=True,
        ) as client:
            for attempt in range(max_retries):
                try:
                    resp = await client.get(url)
                    if resp.status_code in _NO_RETRY_STATUS:
                        raise RuntimeError(
                            f"CelesTrak fetch failed for {url}: HTTP {resp.status_code}"
                        )
                    if resp.status_code in (429, 500, 502, 503, 504):
                        retry_after = resp.headers.get("Retry-After")
                        wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
                        wait += random.uniform(0, 0.25 * wait)
                        logger.warning(
                            "CelesTrak %s → %s; backoff %.2fs (attempt %d)",
                            url,
                            resp.status_code,
                            wait,
                            attempt + 1,
                        )
                        await asyncio.sleep(wait)
                        delay = min(delay * 2, 20.0)
                        continue
                    resp.raise_for_status()
                    return resp
                except RuntimeError:
                    raise
                except Exception as exc:
                    last_exc = exc
                    wait = delay + random.uniform(0, 0.25 * delay)
                    await asyncio.sleep(wait)
                    delay = min(delay * 2, 20.0)
        raise RuntimeError(f"CelesTrak fetch failed for {url}: {last_exc}")

    async def fetch_by_norad(self, norad_id: int) -> list[dict]:
        url = f"{self.base_url}?CATNR={norad_id}&FORMAT=json"
        resp = await self._get_with_backoff(url)
        fetched = datetime.now(timezone.utc)
        try:
            data = resp.json()
            return parse_omm_json(data, stale_hours=self.stale_hours, fetched_at=fetched)
        except Exception:
            return parse_tle_text(resp.text, stale_hours=self.stale_hours, fetched_at=fetched)

    async def fetch_group(self, group: str) -> list[dict]:
        url = f"{self.base_url}?GROUP={group}&FORMAT=json"
        resp = await self._get_with_backoff(url)
        fetched = datetime.now(timezone.utc)
        try:
            data = resp.json()
            return parse_omm_json(data, stale_hours=self.stale_hours, fetched_at=fetched)
        except Exception:
            return parse_tle_text(resp.text, stale_hours=self.stale_hours, fetched_at=fetched)

    async def fetch_catalog(self, norad_ids: list[int] | None = None) -> dict[int, dict]:
        settings = get_settings()
        ids = norad_ids or settings.norad_ids
        merged: dict[int, dict] = {}
        # Prefer group pulls then overlay specific CATNR
        for group in ("weather", "stations"):
            try:
                for rec in await self.fetch_group(group):
                    merged[rec["norad_id"]] = rec
            except Exception as exc:
                logger.warning("group %s fetch failed: %s", group, exc)
        for nid in ids:
            if nid in merged:
                continue
            try:
                for rec in await self.fetch_by_norad(nid):
                    merged[rec["norad_id"]] = rec
            except Exception as exc:
                logger.warning("CATNR %s fetch failed: %s", nid, exc)
        # Restrict to requested catalog if provided
        if ids:
            return {k: v for k, v in merged.items() if k in set(ids)}
        return merged
