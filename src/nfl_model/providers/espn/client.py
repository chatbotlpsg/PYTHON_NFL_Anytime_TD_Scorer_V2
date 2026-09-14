from __future__ import annotations

import time
import requests
from typing import Any


class ESPNClient:
    """Unsupported ESPN JSON adapter. Raw schema is intentionally isolated here."""

    def __init__(self, base_url: str, timeout: int = 20, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.espn.com/",
            "Origin": "https://www.espn.com",
        })

    def _get(self, resource: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{self.base_url}/{resource.lstrip('/')}"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                r = self.session.get(url, params=params, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
                if not isinstance(data, dict):
                    raise ValueError(f"ESPN expected object at {resource}, got {type(data)!r}")
                return data
            except Exception as exc:  # provider boundary: normalize failures here
                last_exc = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(0.6 * (2**attempt))
        raise RuntimeError(f"ESPN request failed: {resource}") from last_exc

    def get_weekly_slate(self, season: int, week: int, season_type: int = 2) -> dict:
        return self._get(
            "scoreboard",
            {
                "dates": str(season),
                "week": week,
                "seasontype": season_type,
            },
        )

    def get_teams(self) -> dict:
        return self._get("teams", {"limit": 32})

    def get_roster(self, team_id: str) -> dict:
        try:
            return self._get(f"teams/{team_id}/roster")
        except RuntimeError:
            # ESPN occasionally rejects or fails the dedicated roster
            # surface for an individual team. The detailed-team endpoint
            # also exposes the current roster under team.athletes.
            return self._get(
                f"teams/{team_id}",
                {"enable": "roster"},
            )

    def get_depth_chart(self, team_id: str) -> dict:
        return self._get(f"teams/{team_id}/depthcharts")

    def get_injuries(self, team_id: str | None = None) -> dict:
        return self._get(f"teams/{team_id}/injuries" if team_id else "injuries")

    def get_transactions(self) -> dict:
        return self._get("transactions")

    def get_game_summary(self, event_id: str) -> dict:
        return self._get("summary", {"event": event_id})
