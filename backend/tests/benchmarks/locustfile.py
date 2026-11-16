"""
Locust WebSocket load script.

  locust -f tests/benchmarks/locustfile.py --host http://localhost:8000
"""

from __future__ import annotations

import json

from locust import User, between, task


class TelemetryUser(User):
    wait_time = between(1, 2)

    @task
    def health(self):
        self.client.get("/api/v1/health")

    @task
    def catalog(self):
        self.client.get("/api/v1/catalog")
