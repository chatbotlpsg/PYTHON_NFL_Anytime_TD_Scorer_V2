from __future__ import annotations

from datetime import datetime, timezone
import os
import requests


class NWSClient:
    def __init__(self, base_url: str = "https://api.weather.gov", timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": os.getenv("NWS_USER_AGENT", "AITA-NFL-MODEL/0.3.0a3"),
            "Accept": "application/geo+json",
        })

    def point(self, lat: float, lon: float) -> dict:
        r = self.session.get(f"{self.base_url}/points/{lat:.4f},{lon:.4f}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def hourly(self, lat: float, lon: float) -> dict:
        point = self.point(lat, lon)
        url = point["properties"]["forecastHourly"]
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def nearest_period(hourly_payload: dict, kickoff_utc: str) -> dict:
        target = datetime.fromisoformat(kickoff_utc.replace("Z", "+00:00")).astimezone(timezone.utc)
        periods = (hourly_payload.get("properties") or {}).get("periods") or []
        if not periods:
            return {}
        def dist(p):
            dt = datetime.fromisoformat(p["startTime"]).astimezone(timezone.utc)
            return abs((dt - target).total_seconds())
        return min(periods, key=dist)
