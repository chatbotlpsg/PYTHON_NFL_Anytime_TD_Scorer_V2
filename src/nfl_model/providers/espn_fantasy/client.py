from __future__ import annotations

import json
import time
from typing import Any

import requests


class ESPNFantasyClient:
    """Read-only adapter for ESPN's public fantasy-football player pool.

    ESPN does not publish this surface as a supported commercial API. The adapter is isolated
    and fail-soft so a provider schema change cannot contaminate football-state identity.
    """

    def __init__(self, base_url: str, timeout: int = 20, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AITA-NFL-SCORER/0.2",
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://fantasy.espn.com/",
        })

    def _get(self, url: str, params: dict[str, Any], fantasy_filter: dict[str, Any]) -> Any:
        headers = {"X-Fantasy-Filter": json.dumps(fantasy_filter, separators=(",", ":"))}
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                r = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
                r.raise_for_status()
                return r.json()
            except Exception as exc:
                last_exc = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(0.6 * (2**attempt))
        raise RuntimeError("ESPN fantasy request failed") from last_exc

    def get_players(self, season: int, week: int) -> Any:
        filt = {
            "players": {
                "limit": 2500,
                "filterStatsForTopScoringPeriodIds": {"value": [int(week)]},
                "sortPercOwned": {"sortPriority": 4, "sortAsc": False},
            }
        }
        # The leaguedefaults view contains projections/ratings without requiring a private league.
        url = f"{self.base_url}/games/ffl/seasons/{season}/segments/0/leaguedefaults/3"
        try:
            return self._get(url, {"view": "kona_player_info", "scoringPeriodId": int(week)}, filt)
        except RuntimeError:
            # Fallback to the public player pool used by ESPN fantasy clients.
            fallback = f"{self.base_url}/games/ffl/seasons/{season}/players"
            return self._get(fallback, {"view": "kona_player_info", "scoringPeriodId": int(week)}, filt)
