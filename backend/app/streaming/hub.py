"""Redis pub/sub fan-out hub with per-client drop-oldest queues."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)


def observer_key(lat: float, lon: float, alt_m: float, freq_hz: float) -> str:
    """Quantize observer for channel multiplexing."""
    return f"{lat:.3f}:{lon:.3f}:{alt_m:.0f}:{freq_hz:.0f}"


class TelemetryHub:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.settings = get_settings()
        self._subs: dict[str, set[asyncio.Queue[bytes]]] = defaultdict(set)
        self._task: asyncio.Task | None = None
        self._pubsub = None

    async def start(self) -> None:
        if self._task:
            return
        self._pubsub = self.redis.pubsub()
        await self._pubsub.psubscribe("frames:*")
        self._task = asyncio.create_task(self._listen(), name="telemetry-hub")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._pubsub:
            await self._pubsub.aclose()
            self._pubsub = None

    async def _listen(self) -> None:
        assert self._pubsub is not None
        try:
            async for msg in self._pubsub.listen():
                if msg is None or msg.get("type") not in ("pmessage", "message"):
                    continue
                channel = msg.get("channel")
                data = msg.get("data")
                if isinstance(channel, bytes):
                    channel = channel.decode()
                if isinstance(data, str):
                    data = data.encode()
                if not isinstance(data, (bytes, bytearray)):
                    continue
                queues = list(self._subs.get(channel, ()))
                # Also deliver global to anyone subscribed to frames:global
                for q in queues:
                    self._offer(q, bytes(data))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("hub listen error: %s", exc)

    @staticmethod
    def _offer(q: asyncio.Queue[bytes], data: bytes) -> None:
        if q.full():
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            pass

    def subscribe(self, channel: str, maxsize: int = 8) -> asyncio.Queue[bytes]:
        q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=maxsize)
        self._subs[channel].add(q)
        return q

    def unsubscribe(self, channel: str, q: asyncio.Queue[bytes]) -> None:
        self._subs[channel].discard(q)
        if not self._subs[channel]:
            self._subs.pop(channel, None)

    async def register_observer(self, key: str) -> None:
        await self.redis.sadd(self.settings.observers_set_key, key)
        await self.redis.expire(self.settings.observers_set_key, 3600)

    async def heartbeat_age(self) -> float | None:
        raw = await self.redis.get(self.settings.ticker_heartbeat_key)
        if not raw:
            return None
        try:
            import time

            ts = float(raw)
            return time.time() - ts
        except Exception:
            return None
