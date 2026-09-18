from __future__ import annotations

from pathlib import Path

from nfl_model.providers.public_fantasy import PublicHTMLClient, PublicHTMLResponse


class PFRFantasyClient:
    def __init__(self, base_url: str, cache_dir: Path, user_agent: str, timeout: int = 20,
                 cache_ttl_hours: float = 6.0, min_request_interval_seconds: float = 0.75) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = PublicHTMLClient(cache_dir, user_agent, timeout, cache_ttl_hours, min_request_interval_seconds)

    def season_fantasy(self, season: int, max_age_hours: float) -> PublicHTMLResponse:
        return self.http.get(
            f"{self.base_url}/years/{int(season)}/fantasy.htm",
            max_age_hours=max_age_hours,
        )
