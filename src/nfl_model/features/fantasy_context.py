from __future__ import annotations

import numpy as np
import pandas as pd

from nfl_model.ids.teams import canonical_team
from nfl_model.utils import normalize_name


def build_fantasy_context(
    player_map: pd.DataFrame,
    espn_fantasy: pd.DataFrame,
    yahoo_fantasy: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join fantasy projections/points to verified NFL identities and derive a capped role prior.

    Fantasy is a role/opportunity corroboration layer, not a direct TD probability model.
    """
    p = player_map.copy()
    if p.empty:
        return p, pd.DataFrame()
    p["fantasy_identity_status"] = "NO_FANTASY_MATCH"
    p["espn_fantasy_projected_points"] = np.nan
    p["espn_fantasy_actual_points"] = np.nan
    p["espn_fantasy_positional_rank"] = np.nan
    p["yahoo_fantasy_points"] = np.nan

    ef = espn_fantasy.copy() if espn_fantasy is not None else pd.DataFrame()
    if not ef.empty:
        ef["team"] = ef["team"].fillna("").map(canonical_team)
        ef["normalized_name"] = ef["player_name"].fillna("").map(normalize_name)
        by_id = ef[ef["espn_athlete_id"].astype(str).str.strip().ne("")].drop_duplicates("espn_athlete_id").set_index("espn_athlete_id")
        by_key = ef.drop_duplicates(["normalized_name","team","position"]).set_index(["normalized_name","team","position"])
        for idx,row in p.iterrows():
            rec=None
            eid=str(row.get("espn_athlete_id") or "").strip()
            if eid and eid.lower()!="nan" and eid in by_id.index:
                rec=by_id.loc[eid]
            else:
                key=(normalize_name(str(row.get("full_name") or "")),canonical_team(str(row.get("current_team") or "")),str(row.get("position") or ""))
                if key in by_key.index: rec=by_key.loc[key]
            if isinstance(rec,pd.DataFrame): rec=rec.iloc[-1]
            if rec is not None:
                p.at[idx,"fantasy_identity_status"]="ESPN_MATCHED"
                for c in ["espn_fantasy_projected_points","espn_fantasy_actual_points","espn_fantasy_positional_rank"]:
                    p.at[idx,c]=rec.get(c)

    yf = yahoo_fantasy.copy() if yahoo_fantasy is not None else pd.DataFrame()
    if not yf.empty:
        yf["team"] = yf.get("team", pd.Series("",index=yf.index)).fillna("").map(canonical_team)
        yf["normalized_name"] = yf.get("player_name", pd.Series("",index=yf.index)).fillna("").map(normalize_name)
        ykey = yf.drop_duplicates(["normalized_name","team"]).set_index(["normalized_name","team"])
        for idx,row in p.iterrows():
            key=(normalize_name(str(row.get("full_name") or "")),canonical_team(str(row.get("current_team") or "")))
            if key in ykey.index:
                rec=ykey.loc[key]
                if isinstance(rec,pd.DataFrame): rec=rec.iloc[-1]
                p.at[idx,"yahoo_fantasy_points"]=rec.get("yahoo_fantasy_points")
                p.at[idx,"fantasy_identity_status"]="ESPN_AND_YAHOO_MATCHED" if p.at[idx,"fantasy_identity_status"]=="ESPN_MATCHED" else "YAHOO_MATCHED"

    proj=pd.to_numeric(p["espn_fantasy_projected_points"],errors="coerce")
    actual=pd.to_numeric(p["espn_fantasy_actual_points"],errors="coerce")
    p["fantasy_projection_position_rank"] = proj.groupby(p["position"]).rank(method="min", ascending=False)
    p["fantasy_actual_position_rank"] = actual.groupby(p["position"]).rank(method="min", ascending=False)
    # Capped influence: projection is evidence of role/opportunity, not a substitute for TD modeling.
    pct = proj.groupby(p["position"]).rank(pct=True).fillna(0.5)
    p["fantasy_role_multiplier"] = (0.92 + 0.16 * pct).clip(0.92, 1.08)
    # Verified players with a strong fantasy projection can override a missing ESPN depth rank.
    strong = p["fantasy_projection_position_rank"].le(p["position"].map({"QB":16,"RB":30,"WR":45,"TE":24}).fillna(0))
    p["fantasy_primary_override"] = p.get("available_for_simulation",False).astype(bool) & strong.fillna(False)
    p["primary_scorer_eligible"] = p.get("available_for_simulation",False).astype(bool) & (p.get("primary_depth_eligible",False).astype(bool) | p["fantasy_primary_override"])

    context_cols=[c for c in ["aita_player_id","full_name","current_team","position","roster_verified_current","depth_rank","availability_status","espn_fantasy_projected_points","espn_fantasy_actual_points","fantasy_projection_position_rank","fantasy_actual_position_rank","yahoo_fantasy_points","fantasy_role_multiplier","primary_scorer_eligible","fantasy_identity_status"] if c in p.columns]
    board=p[context_cols].copy().sort_values(["position","fantasy_projection_position_rank"],na_position="last")
    return p, board


def attach_fantasy_to_scorer_state(scorer_state: pd.DataFrame, player_map: pd.DataFrame) -> pd.DataFrame:
    if scorer_state is None or scorer_state.empty or player_map is None or player_map.empty:
        return scorer_state
    s=scorer_state.copy()
    keep=[c for c in ["aita_player_id","espn_fantasy_projected_points","espn_fantasy_actual_points","fantasy_projection_position_rank","fantasy_actual_position_rank","yahoo_fantasy_points","fantasy_role_multiplier","primary_scorer_eligible","roster_verified_current","depth_rank"] if c in player_map.columns]
    return s.merge(player_map[keep].drop_duplicates("aita_player_id"),on="aita_player_id",how="left")
