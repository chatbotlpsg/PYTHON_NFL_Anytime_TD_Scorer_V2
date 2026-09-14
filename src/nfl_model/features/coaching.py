from __future__ import annotations
import pandas as pd


def build_coaching_state(team_state: pd.DataFrame) -> pd.DataFrame:
    if team_state.empty:
        return pd.DataFrame()
    out = team_state[[c for c in ["team", "pass_rate", "plays_mean"] if c in team_state.columns]].copy()
    out = out.rename(columns={"pass_rate": "neutral_pass_rate_prior", "plays_mean": "pace_plays_prior"})
    out["coordinator_change_flag"] = False
    out["coaching_uncertainty"] = 0.08
    return out
