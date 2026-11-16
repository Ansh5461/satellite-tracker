"""FastAPI application factory."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import get_settings
from app.ingestion.catalog import CatalogService
from app.streaming.executor import get_pool, shutdown_pool
from app.streaming.hub import TelemetryHub
from app.streaming.rest_routes import router as rest_router
from app.streaming.ws_routes import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    catalog = CatalogService(redis)
    hub = TelemetryHub(redis)

    app.state.settings = settings
    app.state.redis = redis
    app.state.catalog = catalog
    app.state.hub = hub

    # Ensure process pool is warm
    get_pool()

    try:
        await catalog.refresh_all(force=True, remote=False)
    except Exception:
        pass
    catalog.refresh_remote_background()

    await hub.start()

    async def periodic_refresh():
        while True:
            await asyncio.sleep(settings.omm_fresh_seconds)
            catalog.refresh_remote_background()

    refresh_task = asyncio.create_task(periodic_refresh())
    yield
    refresh_task.cancel()
    await hub.stop()
    shutdown_pool()
    await redis.aclose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="LEO Orbital Telemetry & RF Pass Predictor",
        version="2.0.0",
        lifespan=lifespan,
    )
    origins = (
        ["*"]
        if settings.cors_origins.strip() == "*"
        else [o.strip() for o in settings.cors_origins.split(",")]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(rest_router)
    app.include_router(ws_router)

    # Legacy aliases
    @app.get("/api/health")
    async def legacy_health():
        from fastapi import Request

        # thin redirect via internal call not available; duplicate minimal
        return {"status": "ok", "see": "/api/v1/health"}

    return app


app = create_app()
