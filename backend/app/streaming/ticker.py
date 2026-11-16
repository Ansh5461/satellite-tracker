"""Dedicated ticker process: SatrecArray propagate → Redis publish @ 1–2 Hz."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

import numpy as np
from redis.asyncio import Redis

from app.config import get_settings
from app.ingestion.catalog import CatalogService
from app.physics.doppler import (
    doppler_drift_hz_s,
    range_accel_from_state,
    relativistic_doppler_hz,
)
from app.physics.eclipse import classify_eclipse
from app.physics.link_budget import fspl_db
from app.physics.refraction import apparent_elevation_deg
from app.propagation.geodesy import observer_ecef
from app.propagation.sgp4_batch import propagate_batch
from app.propagation.topocentric import look_angles, range_rate_km_s
from app.schemas.telemetry import GlobalFrame, ObserverGeometry, SatelliteState, TelemetryFrame
from app.streaming.serialization import dumps

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ticker")


def _parse_observer_key(key: str) -> tuple[float, float, float, float] | None:
    try:
        lat, lon, alt, freq = key.split(":")
        return float(lat), float(lon), float(alt), float(freq)
    except Exception:
        return None


async def run_ticker() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    catalog = CatalogService(redis)
    try:
        await catalog.refresh_all(force=True, remote=False)
    except Exception as exc:
        logger.warning("initial catalog seed failed: %s", exc)
    catalog.refresh_remote_background()

    tick_id = 0
    period = 1.0 / settings.tick_hz
    refresh_every = max(60, int(settings.omm_fresh_seconds // 4))
    ticks_since_refresh = 0

    logger.info("ticker started at %.2f Hz", settings.tick_hz)
    try:
        while True:
            t_start = time.monotonic()
            tick_id += 1
            now = datetime.now(timezone.utc)
            ticks_since_refresh += 1

            try:
                sats = await catalog.all_satrecs()
            except Exception as exc:
                logger.warning("all_satrecs failed: %s", exc)
                sats = []

            if not sats and ticks_since_refresh >= 5:
                ticks_since_refresh = 0
                try:
                    await catalog.refresh_all(remote=False)
                    catalog.refresh_remote_background()
                    sats = await catalog.all_satrecs()
                except Exception as exc:
                    logger.warning("catalog refresh failed: %s", exc)

            if sats:
                norads = [s[0] for s in sats]
                names = [s[1] for s in sats]
                satrecs = [s[2] for s in sats]

                # Dedicated ticker container already owns the CPU work; use a
                # thread (not ProcessPool) so Satrec objects need not pickle.
                batch = await asyncio.to_thread(propagate_batch, satrecs, [now])
                nu, estate = classify_eclipse(
                    batch.r_teme_km[:, 0, :],
                    np.array([batch.timescales.jd_tt[0]] * len(satrecs)),
                    np.array([batch.timescales.fr_tt[0]] * len(satrecs)),
                )
                states: list[SatelliteState] = []
                for i, nid in enumerate(norads):
                    if not batch.valid[i, 0]:
                        continue
                    states.append(
                        SatelliteState(
                            norad_id=nid,
                            name=names[i],
                            timestamp=now.isoformat(),
                            r_teme_km=tuple(float(x) for x in batch.r_teme_km[i, 0]),
                            v_teme_km_s=tuple(float(x) for x in batch.v_teme_km_s[i, 0]),
                            r_itrs_km=tuple(float(x) for x in batch.r_itrs_km[i, 0]),
                            v_itrs_km_s=tuple(float(x) for x in batch.v_itrs_km_s[i, 0]),
                            latitude_deg=float(batch.latitude_deg[i, 0]),
                            longitude_deg=float(batch.longitude_deg[i, 0]),
                            altitude_km=float(batch.altitude_km[i, 0]),
                            velocity_km_s=float(np.linalg.norm(batch.v_itrs_km_s[i, 0])),
                            eclipse_state=str(estate[i]),
                            shadow_function=float(nu[i]),
                        )
                    )

                frame = GlobalFrame(
                    timestamp=now.isoformat(),
                    tick_id=tick_id,
                    satellites=states,
                    degraded_iers=batch.timescales.degraded,
                )
                payload = dumps(frame)
                await redis.publish(settings.frames_global_channel, payload)
                await redis.set(
                    "frames:global:latest", payload, ex=10
                )

                # Per-observer topocentric frames
                obs_raw = await redis.smembers(settings.observers_set_key)
                for ok in obs_raw:
                    key = ok.decode() if isinstance(ok, bytes) else str(ok)
                    parsed = _parse_observer_key(key)
                    if not parsed:
                        continue
                    lat, lon, alt_m, freq_hz = parsed
                    for st in states:
                        idx = norads.index(st.norad_id)
                        r = batch.r_itrs_km[idx, 0]
                        v = batch.v_itrs_km_s[idx, 0]
                        az, el, slant = look_angles(lat, lon, alt_m, r)
                        rr = range_rate_km_s(lat, lon, alt_m, r, v)
                        speed = float(np.linalg.norm(v))
                        d_hz = float(relativistic_doppler_hz(freq_hz, rr, speed))
                        rho = r - observer_ecef(lat, lon, alt_m)
                        accel = float(range_accel_from_state(rho, v))
                        drift = float(doppler_drift_hz_s(freq_hz, rr, accel))
                        obs = ObserverGeometry(
                            azimuth_deg=float(az),
                            elevation_deg=float(el),
                            elevation_apparent_deg=float(apparent_elevation_deg(el)),
                            slant_range_km=float(slant),
                            range_rate_km_s=float(rr),
                            doppler_hz=d_hz,
                            doppler_drift_hz_s=drift,
                            fspl_db=float(fspl_db(slant, freq_hz)),
                            rx_freq_hz=float(freq_hz + d_hz),
                        )
                        tf = TelemetryFrame(
                            timestamp=now.isoformat(),
                            tick_id=tick_id,
                            satellite=st,
                            observer=obs,
                            degraded_iers=batch.timescales.degraded,
                        )
                        await redis.publish(f"frames:obs:{key}:{st.norad_id}", dumps(tf))
            elif tick_id % 10 == 0:
                logger.warning("ticker has 0 satellites — check Redis / fallback TLEs")

            # Heartbeat even when catalog empty so /health can diagnose ticker liveness
            await redis.set(
                settings.ticker_heartbeat_key,
                str(time.time()),
                ex=settings.ticker_heartbeat_ttl_s,
            )

            if ticks_since_refresh >= refresh_every:
                ticks_since_refresh = 0
                catalog.refresh_remote_background()

            elapsed = time.monotonic() - t_start
            await asyncio.sleep(max(0.0, period - elapsed))
    finally:
        await redis.aclose()


def main() -> None:
    asyncio.run(run_ticker())


if __name__ == "__main__":
    main()
