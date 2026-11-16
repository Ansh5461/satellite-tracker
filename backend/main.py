"""Shim: prefer `uvicorn app.main:app`. Kept for local/dev compatibility."""

from app.main import app

__all__ = ["app"]
