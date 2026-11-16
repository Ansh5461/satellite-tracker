"""Redis stale-while-revalidate cache for OMM records + B* history."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable

import numpy as np
from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)


class EphemerisCache:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.settings = get_settings()
        self._bg: set[asyncio.Task] = set()

    def _key(self, norad_id: int) -> str:
        return f"omm:{norad_id}"

    def _meta_key(self, norad_id: int) -> str:
        return f"omm:{norad_id}:meta"

    def _lock_key(self, norad_id: int) -> str:
        return f"omm:{norad_id}:lock"

    def _bstar_key(self, norad_id: int) -> str:
        return f"bstar:{norad_id}"

    async def get(self, norad_id: int) -> dict | None:
        raw = await self.redis.get(self._key(norad_id))
        if not raw:
            return None
        return json.loads(raw)

    async def get_meta(self, norad_id: int) -> dict:
        raw = await self.redis.get(self._meta_key(norad_id))
        if not raw:
            return {}
        return json.loads(raw)

    async def set_record(self, record: dict) -> None:
        norad = int(record["norad_id"])
        now = time.time()
        fresh_until = now + self.settings.omm_fresh_seconds
        stale_until = now + self.settings.omm_stale_seconds
        meta = {"fresh_until": fresh_until, "stale_until": stale_until, "stored_at": now}
        pipe = self.redis.pipeline()
        pipe.set(self._key(norad), json.dumps(record), ex=self.settings.omm_stale_seconds)
        pipe.set(self._meta_key(norad), json.dumps(meta), ex=self.settings.omm_stale_seconds)
        # B* history sorted set: score = epoch unix
        try:
            from datetime import datetime

            epoch = datetime.fromisoformat(record["epoch_iso"])
            score = epoch.timestamp()
            member = json.dumps({"bstar": record["bstar"], "n": record["mean_motion_rev_per_day"]})
            pipe.zadd(self._bstar_key(norad), {member: score})
            pipe.zremrangebyrank(self._bstar_key(norad), 0, -50)  # keep last 49
        except Exception:
            pass
        await pipe.execute()

    async def bstar_trend(self, norad_id: int) -> float | None:
        """Linear fit slope of B* vs epoch [1/earth-radii / day]."""
        items = await self.redis.zrange(self._bstar_key(norad_id), 0, -1, withscores=True)
        if len(items) < 2:
            return None
        xs = []
        ys = []
        for member, score in items:
            try:
                obj = json.loads(member)
                xs.append(float(score) / 86400.0)
                ys.append(float(obj["bstar"]))
            except Exception:
                continue
        if len(xs) < 2:
            return None
        x = np.asarray(xs)
        y = np.asarray(ys)
        x = x - x.mean()
        denom = float(np.dot(x, x))
        if denom < 1e-18:
            return 0.0
        return float(np.dot(x, y - y.mean()) / denom)

    def _spawn(self, coro: Awaitable[Any]) -> None:
        task = asyncio.create_task(coro)
        self._bg.add(task)
        task.add_done_callback(self._bg.discard)

    async def _revalidate_locked(
        self,
        norad_id: int,
        fetch_fn: Callable[[], Awaitable[dict | None]],
    ) -> None:
        try:
            fresh = await fetch_fn()
            if fresh:
                await self.set_record(fresh)
        except Exception as exc:
            logger.warning("revalidate %s failed: %s", norad_id, exc)
        finally:
            try:
                await self.redis.delete(self._lock_key(norad_id))
            except Exception:
                pass

    async def get_or_revalidate(
        self,
        norad_id: int,
        fetch_fn: Callable[[], Awaitable[dict | None]],
    ) -> dict | None:
        """SWR: return cached immediately; single-flight background refresh when stale."""
        record = await self.get(norad_id)
        meta = await self.get_meta(norad_id)
        now = time.time()
        if record and meta.get("fresh_until", 0) > now:
            return record

        # Past fresh TTL → try single-flight background refresh, serve stale now.
        lock = await self.redis.set(self._lock_key(norad_id), "1", nx=True, px=60_000)
        if lock:
            if record:
                self._spawn(self._revalidate_locked(norad_id, fetch_fn))
            else:
                # Cold miss: must await once so callers get a record when upstream works.
                await self._revalidate_locked(norad_id, fetch_fn)
                record = await self.get(norad_id)
                return record

        if record and meta.get("stale_until", 0) > now:
            return record
        return record  # may be None / expired
