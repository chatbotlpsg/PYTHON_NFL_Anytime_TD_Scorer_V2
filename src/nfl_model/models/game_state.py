from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class GameEnvironment:
    team_points_mean: float
    opponent_points_mean: float
    team_plays_mean: float
    pass_rate_shift: float


def baseline_environment(team_epa: float, opponent_epa: float, plays_mean: float, home: bool) -> GameEnvironment:
    strength = np.clip((team_epa - opponent_epa) * 8.0, -7.0, 7.0)
    home_pts = 1.4 if home else 0.0
    team_pts = float(np.clip(22.5 + strength + home_pts, 10.0, 38.0))
    opp_pts = float(np.clip(22.5 - strength - home_pts * 0.6, 10.0, 38.0))
    script_shift = float(np.clip((opp_pts - team_pts) / 100.0, -0.08, 0.08))
    return GameEnvironment(team_pts, opp_pts, plays_mean, script_shift)


def market_anchor(env: GameEnvironment, team_total_market: float | None, weight: float = 0.65) -> GameEnvironment:
    if team_total_market is None:
        return env
    anchored = weight * team_total_market + (1.0 - weight) * env.team_points_mean
    shift = np.clip((env.opponent_points_mean - anchored) / 100.0, -0.08, 0.08)
    return GameEnvironment(float(anchored), env.opponent_points_mean, env.team_plays_mean, float(shift))
