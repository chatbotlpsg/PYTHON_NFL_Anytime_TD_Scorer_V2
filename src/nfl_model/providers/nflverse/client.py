from __future__ import annotations

from pathlib import Path
from typing import Any


class NFLVerseClient:
    """Thin adapter around nflreadpy. Loading is lazy so offline tests do not require provider deps."""

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _libs():
        import nflreadpy as nfl
        import polars as pl
        return nfl, pl

    def _load_cached(self, name: str, seasons: list[int], loader) -> Any:
        _, pl = self._libs()
        tag = "_".join(map(str, seasons))
        path = self.cache_dir / f"{name}_{tag}.parquet"
        if path.exists():
            return pl.read_parquet(path)
        df = loader(seasons)
        if not isinstance(df, pl.DataFrame):
            df = pl.DataFrame(df)
        df.write_parquet(path)
        return df

    def load_pbp(self, seasons: list[int]):
        nfl, _ = self._libs()
        return self._load_cached("pbp", seasons, nfl.load_pbp)

    def load_player_stats(self, seasons: list[int]):
        nfl, _ = self._libs()
        return self._load_cached("player_stats", seasons, lambda s: nfl.load_player_stats(s, summary_level="week"))

    def load_team_stats(self, seasons: list[int]):
        nfl, _ = self._libs()
        return self._load_cached("team_stats", seasons, lambda s: nfl.load_team_stats(s, summary_level="week"))

    def load_schedules(self, seasons: list[int]):
        nfl, _ = self._libs()
        return self._load_cached("schedules", seasons, nfl.load_schedules)

    def load_rosters_weekly(self, seasons: list[int]):
        nfl, _ = self._libs()
        return self._load_cached("rosters_weekly", seasons, nfl.load_rosters_weekly)

    def load_snap_counts(self, seasons: list[int]):
        nfl, _ = self._libs()
        return self._load_cached("snap_counts", seasons, nfl.load_snap_counts)

    def load_participation(self, seasons: list[int]):
        nfl, _ = self._libs()
        return self._load_cached("participation", seasons, nfl.load_participation)

    def load_injuries(self, seasons: list[int]):
        nfl, _ = self._libs()
        return self._load_cached("injuries", seasons, nfl.load_injuries)

    def load_depth_charts(self, seasons: list[int]):
        nfl, _ = self._libs()
        return self._load_cached("depth_charts", seasons, nfl.load_depth_charts)
