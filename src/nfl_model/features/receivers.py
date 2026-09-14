from __future__ import annotations
import numpy as np
import pandas as pd


def build_receiver_state(player_stats: pd.DataFrame, snap_counts: pd.DataFrame | None = None, halflife: float = 5.0) -> pd.DataFrame:
    if player_stats.empty:
        return pd.DataFrame()
    df = player_stats.copy()
    if "position" in df.columns:
        df = df[df["position"].isin(["WR", "TE"])]
    id_col = next((c for c in ["player_id", "gsis_id"] if c in df.columns), None)
    name_col = next((c for c in ["player_display_name", "player_name", "name"] if c in df.columns), None)
    team_col = next((c for c in ["recent_team", "team", "team_abbr"] if c in df.columns), None)
    if not id_col or not name_col or not team_col:
        return pd.DataFrame()
    for c in ["targets", "receptions", "receiving_yards", "receiving_air_yards", "receiving_yards_after_catch"]:
        if c not in df.columns: df[c] = 0.0
    snap_share_by_id = {}
    if snap_counts is not None and not snap_counts.empty:
        sid = next((c for c in ["player_id", "gsis_id"] if c in snap_counts.columns), None)
        share = next((c for c in ["offense_pct", "offense_snaps_pct", "offense_snap_pct"] if c in snap_counts.columns), None)
        if sid and share:
            tmp = snap_counts.copy()
            tmp[share] = pd.to_numeric(tmp[share], errors="coerce")
            if tmp[share].max(skipna=True) and tmp[share].max(skipna=True) > 1.5:
                tmp[share] = tmp[share] / 100.0
            snap_share_by_id = tmp.groupby(sid)[share].mean().to_dict()
    rows = []
    for pid, g in df.groupby(id_col):
        sort_cols = [c for c in ["season", "week"] if c in g.columns]
        if sort_cols: g = g.sort_values(sort_cols)
        targ = pd.to_numeric(g["targets"], errors="coerce").fillna(0)
        rec = pd.to_numeric(g["receptions"], errors="coerce").fillna(0)
        yds = pd.to_numeric(g["receiving_yards"], errors="coerce").fillna(0)
        air = pd.to_numeric(g["receiving_air_yards"], errors="coerce").fillna(0)
        yac = pd.to_numeric(g["receiving_yards_after_catch"], errors="coerce").fillna(0)
        targets_mean = float(targ.ewm(halflife=halflife, adjust=False).mean().iloc[-1])
        snap_share = float(np.clip(snap_share_by_id.get(pid, min(0.95, 0.45 + targets_mean / 20)), 0.15, 0.98))
        rows.append({
            "gsis_id": str(pid), "player_name": g.iloc[-1][name_col], "team": g.iloc[-1][team_col],
            "position": g.iloc[-1].get("position", "WR"), "targets_mean": targets_mean,
            "route_share_median": float(np.clip(snap_share * 0.95, 0.1, 0.98)),
            "route_share_sd": float(np.clip(0.09 + (1.0 - snap_share) * 0.08, 0.05, 0.18)),
            "catch_rate": float(np.clip(rec.sum() / max(targ.sum(), 1), 0.35, 0.92)),
            "yards_per_reception": float(np.clip(yds.sum() / max(rec.sum(), 1), 4.0, 22.0)),
            "adot": float(np.clip(air.sum() / max(targ.sum(), 1), 1.0, 22.0)) if air.sum() > 0 else float(np.clip((yds.sum() / max(rec.sum(), 1)) * 0.68, 2.0, 16.0)),
            "yac_per_reception": float(np.clip(yac.sum() / max(rec.sum(), 1), 0.5, 12.0)) if yac.sum() > 0 else float(np.clip((yds.sum() / max(rec.sum(), 1)) * 0.32, 1.0, 8.0)),
            "target_rate_per_route": float(np.clip(targets_mean / max(35.0 * snap_share, 1.0), 0.04, 0.40)),
            "games_observed": len(g),
        })
    return pd.DataFrame(rows)
