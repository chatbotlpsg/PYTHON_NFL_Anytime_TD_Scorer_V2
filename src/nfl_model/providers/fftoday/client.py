from __future__ import annotations

from pathlib import Path

from nfl_model.providers.public_fantasy import PublicHTMLClient, PublicHTMLResponse

POS_ID = {"QB": 10, "RB": 20, "WR": 30, "TE": 40}


class FFTodayClient:
    def __init__(self, base_url: str, cache_dir: Path, user_agent: str, timeout: int = 20,
                 cache_ttl_hours: float = 6.0, min_request_interval_seconds: float = 0.75) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = PublicHTMLClient(cache_dir, user_agent, timeout, cache_ttl_hours, min_request_interval_seconds)

    def weekly_projection(self, season: int, week: int, position: str, max_age_hours: float) -> PublicHTMLResponse:
        pos = str(position).upper()
        if pos not in POS_ID:
            raise ValueError(f"Unsupported FFToday position: {position}")
        return self.http.get(
            f"{self.base_url}/rankings/playerwkproj.php",
            params={"GameWeek": int(week), "LeagueID": 1, "PosID": POS_ID[pos], "Season": int(season)},
            max_age_hours=max_age_hours,
        )
