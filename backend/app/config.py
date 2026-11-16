"""Application settings (pydantic-settings)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    tick_hz: float = Field(default=1.0, ge=0.5, le=2.0, description="Ticker rate [Hz]")
    omm_fresh_seconds: int = Field(default=7200, description="SWR fresh TTL [s]")
    omm_stale_seconds: int = Field(default=86400, description="SWR stale TTL [s]")
    epoch_stale_hours: float = Field(default=48.0, description="TLE epoch age warning [h]")
    iers_auto_download: bool = Field(default=False, description="Allow IERS auto-download")
    process_pool_workers: int = Field(default=2, ge=1, le=8)
    cors_origins: str = Field(default="*")
    catalog_norad_ids: str = Field(
        # Prefer assets present in data/tle_fallback.json so offline / CelesTrak-403 still works.
        default="25544,40069,44387,57166,59051,43013,43689,48274",
        description="Comma-separated NORAD catalog IDs",
    )
    ticker_heartbeat_key: str = "ticker:heartbeat"
    ticker_heartbeat_ttl_s: int = 5
    frames_global_channel: str = "frames:global"
    observers_set_key: str = "observers:active"
    celestrak_base: str = "https://celestrak.org/NORAD/elements/gp.php"

    @property
    def norad_ids(self) -> list[int]:
        return [int(x.strip()) for x in self.catalog_norad_ids.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
