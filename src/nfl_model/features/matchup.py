from __future__ import annotations
import numpy as np
import pandas as pd


def build_matchup_state(slate: pd.DataFrame, team_state: pd.DataFrame) -> pd.DataFrame:
    if slate.empty: return pd.DataFrame()
    idx = team_state.set_index("team") if not team_state.empty else pd.DataFrame()
    rows = []
    for _, game in slate.iterrows():
        for team_col, opp_col, loc in [("home_team", "away_team", "HOME"), ("away_team", "home_team", "AWAY")]:
            team, opp = game[team_col], game[opp_col]
            t = idx.loc[team] if isinstance(idx, pd.DataFrame) and team in idx.index else {}
            o = idx.loc[opp] if isinstance(idx, pd.DataFrame) and opp in idx.index else {}
            t_epa = float(t.get("epa_per_play", 0.0)) if hasattr(t, "get") else 0.0
            o_epa = float(o.get("epa_per_play", 0.0)) if hasattr(o, "get") else 0.0
            rows.append({
                "aita_event_id": game["aita_event_id"], "team": team, "opponent": opp, "location": loc,
                "matchup_epa_delta": float(np.clip(t_epa - o_epa, -0.35, 0.35)),
                "home_field_points": 1.5 if loc == "HOME" else -1.5,
            })
    return pd.DataFrame(rows)
