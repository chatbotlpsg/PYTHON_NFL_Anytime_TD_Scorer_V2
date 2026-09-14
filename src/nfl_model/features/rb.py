from __future__ import annotations
import numpy as np
import pandas as pd


def build_rb_state(player_stats: pd.DataFrame, halflife: float = 5.0) -> pd.DataFrame:
    if player_stats.empty:
        return pd.DataFrame()
    df = player_stats.copy()
    if "position" in df.columns:
        df = df[df["position"].eq("RB")]
    id_col = next((c for c in ["player_id", "gsis_id"] if c in df.columns), None)
    name_col = next((c for c in ["player_display_name", "player_name", "name"] if c in df.columns), None)
    team_col = next((c for c in ["recent_team", "team", "team_abbr"] if c in df.columns), None)
    if not id_col or not name_col or not team_col:
        return pd.DataFrame()
    for c in ["carries", "rushing_yards", "targets", "receptions", "receiving_yards", "receiving_air_yards", "receiving_yards_after_catch"]:
        if c not in df.columns: df[c] = 0.0
    rows = []
    for pid, g in df.groupby(id_col):
        g = g.sort_values([c for c in ["season", "week"] if c in g.columns])
        ew = lambda s: float(pd.to_numeric(s, errors="coerce").fillna(0).ewm(halflife=halflife, adjust=False).mean().iloc[-1])
        car = pd.to_numeric(g["carries"], errors="coerce").fillna(0)
        rushyd = pd.to_numeric(g["rushing_yards"], errors="coerce").fillna(0)
        targ = pd.to_numeric(g["targets"], errors="coerce").fillna(0)
        rec = pd.to_numeric(g["receptions"], errors="coerce").fillna(0)
        recyd = pd.to_numeric(g["receiving_yards"], errors="coerce").fillna(0)
        air = pd.to_numeric(g["receiving_air_yards"], errors="coerce").fillna(0)
        yac = pd.to_numeric(g["receiving_yards_after_catch"], errors="coerce").fillna(0)
        rows.append({
            "gsis_id": str(pid), "player_name": g.iloc[-1][name_col], "team": g.iloc[-1][team_col], "position": "RB",
            "carries_mean": ew(car), "targets_mean": ew(targ),
            "catch_rate": float(np.clip(rec.sum() / max(targ.sum(), 1), 0.35, 0.95)),
            "rush_yards_per_carry": float(np.clip(rushyd.sum() / max(car.sum(), 1), 2.0, 8.0)),
            "rec_yards_per_reception": float(np.clip(recyd.sum() / max(rec.sum(), 1), 2.0, 18.0)),
            "adot": float(np.clip(air.sum() / max(targ.sum(), 1), 0.0, 10.0)) if air.sum() > 0 else 1.8,
            "yac_per_reception": float(np.clip(yac.sum() / max(rec.sum(), 1), 1.0, 14.0)) if yac.sum() > 0 else float(np.clip(recyd.sum() / max(rec.sum(), 1) * 0.70, 2.0, 9.0)),
            "route_share_median": float(np.clip(0.14 + ew(targ) / 15.0, 0.10, 0.72)),
            "route_share_sd": 0.10,
            "games_observed": len(g),
        })
    return pd.DataFrame(rows)
