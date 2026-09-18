from __future__ import annotations

from typing import Any
import requests


class YahooFantasyClient:
    """Official Yahoo Fantasy Sports API reader.

    Yahoo requires approved API access and OAuth 2.0. The pipeline therefore enables this
    layer only when YAHOO_FANTASY_ACCESS_TOKEN and YAHOO_FANTASY_LEAGUE_KEY are supplied.
    """

    def __init__(self, base_url: str, access_token: str, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {access_token}", "Accept": "application/json"})

    def get_league_players(self, league_key: str, week: int, page_size: int = 25, max_players: int = 600) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for start in range(0, max_players, page_size):
            resource = f"league/{league_key}/players;start={start};count={page_size}/stats;type=week;week={int(week)}"
            url = f"{self.base_url}/{resource}"
            r = self.session.get(url, params={"format": "json"}, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            payloads.append(data)
            # Stop when the page contains fewer player resources than requested.
            if str(data).count("player_key") < page_size:
                break
        return payloads
