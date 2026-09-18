from __future__ import annotations

from pathlib import Path

from nfl_model.providers.public_fantasy import PublicHTMLClient, PublicHTMLResponse


class FantasyProsClient:
    def __init__(self, base_url: str, cache_dir: Path, user_agent: str, timeout: int = 20,
                 cache_ttl_hours: float = 6.0, min_request_interval_seconds: float = 0.75) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = PublicHTMLClient(cache_dir, user_agent, timeout, cache_ttl_hours, min_request_interval_seconds)

    def weekly_rankings(self, week: int, position: str, max_age_hours: float) -> PublicHTMLResponse:
        pos = str(position).upper()
        return self.http.get(
            f"{self.base_url}/nfl/rankings/",
            params={"position": pos, "scoring": "HALF", "type": "weekly", "week": int(week)},
            max_age_hours=max_age_hours,
        )
