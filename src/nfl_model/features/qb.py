from __future__ import annotations
import numpy as np
import pandas as pd


def build_qb_state(player_stats: pd.DataFrame, snap_counts: pd.DataFrame | None = None, halflife: float = 5.0) -> pd.DataFrame:
    if player_stats.empty:
        return pd.DataFrame()
    df = player_stats.copy()
    pos_col = "position" if "position" in df.columns else None
    if pos_col:
        df = df[df[pos_col].eq("QB")]
    id_col = next((c for c in ["player_id", "gsis_id", "player_id_nfl"] if c in df.columns), None)
    name_col = next((c for c in ["player_display_name", "player_name", "name"] if c in df.columns), None)
    team_col = next((c for c in ["recent_team", "team", "team_abbr"] if c in df.columns), None)
    if not id_col or not name_col or not team_col:
        return pd.DataFrame()
    for c in ["attempts", "completions", "passing_yards", "sacks", "carries"]:
        if c not in df.columns:
            df[c] = 0.0
    sort_cols = [c for c in ["season", "week"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols)
    rows = []
    for pid, g in df.groupby(id_col):
        att = pd.to_numeric(g["attempts"], errors="coerce").fillna(0)
        comp = pd.to_numeric(g["completions"], errors="coerce").fillna(0)
        yds = pd.to_numeric(g["passing_yards"], errors="coerce").fillna(0)
        sacks = pd.to_numeric(g["sacks"], errors="coerce").fillna(0)
        carries = pd.to_numeric(g["carries"], errors="coerce").fillna(0)
        ew = lambda s: float(s.ewm(halflife=halflife, adjust=False).mean().iloc[-1]) if len(s) else 0.0
        rows.append({
            "gsis_id": str(pid), "player_name": g.iloc[-1][name_col], "team": g.iloc[-1][team_col], "position": "QB",
            "attempts_mean": ew(att),
            "completion_rate": float(np.clip(comp.sum() / max(att.sum(), 1.0), 0.4, 0.8)),
            "pass_yards_per_attempt": float(np.clip(yds.sum() / max(att.sum(), 1.0), 4.0, 11.0)),
            "sack_per_dropback": float(np.clip(sacks.sum() / max(att.sum() + sacks.sum(), 1.0), 0.0, 0.2)),
            "scramble_proxy_rate": float(np.clip(carries.sum() / max(att.sum() + carries.sum(), 1.0) * 0.35, 0.0, 0.15)),
            "games_observed": len(g),
        })
    return pd.DataFrame(rows)
