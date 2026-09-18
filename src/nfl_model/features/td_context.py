from __future__ import annotations

import re
import numpy as np
import pandas as pd

from nfl_model.ids.teams import canonical_team

SCORER_POSITIONS = {"QB", "RB", "WR", "TE"}


def _num(s: pd.Series | object, default: float = 0.0) -> pd.Series:
    if isinstance(s, pd.Series):
        return pd.to_numeric(s, errors="coerce").fillna(default)
    return pd.Series(dtype=float)


def _player_lookup(player_stats: pd.DataFrame) -> pd.DataFrame:
    if player_stats is None or player_stats.empty:
        return pd.DataFrame(columns=["player_id", "player_name", "position", "team"])
    df = player_stats.copy()
    id_col = next((c for c in ["player_id", "gsis_id", "player_id_nfl"] if c in df.columns), None)
    name_col = next((c for c in ["player_display_name", "player_name", "name"] if c in df.columns), None)
    team_col = next((c for c in ["recent_team", "team", "team_abbr"] if c in df.columns), None)
    if not id_col or not name_col or not team_col or "position" not in df.columns:
        return pd.DataFrame(columns=["player_id", "player_name", "position", "team"])
    sort_cols = [c for c in ["season", "week"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols)
    out = df.dropna(subset=[id_col]).drop_duplicates(id_col, keep="last")[[id_col, name_col, "position", team_col]].copy()
    out.columns = ["player_id", "player_name", "position", "team"]
    out["player_id"] = out["player_id"].astype(str)
    out["team"] = out["team"].fillna("").map(canonical_team)
    return out


def build_touchdown_history(pbp: pd.DataFrame, player_stats: pd.DataFrame) -> pd.DataFrame:
    """Create scorer-level TD events with field-location origin from nflverse PBP.

    This supports defensive TD vulnerability, player TD style and QB goal-line competition.
    It never infers slot/outside alignment because standard PBP does not reliably carry it.
    """
    if pbp is None or pbp.empty:
        return pd.DataFrame()
    p = pbp.copy()
    lookup = _player_lookup(player_stats).set_index("player_id") if player_stats is not None else pd.DataFrame()
    rows: list[dict] = []
    for _, r in p.iterrows():
        defteam = canonical_team(str(r.get("defteam") or ""))
        posteam = canonical_team(str(r.get("posteam") or ""))
        if not defteam or not posteam:
            continue
        yard = r.get("yardline_100")
        try:
            yard = float(yard)
        except (TypeError, ValueError):
            yard = np.nan
        desc = str(r.get("desc") or "")
        season = r.get("season")
        week = r.get("week")
        game_id = r.get("game_id") or f"{season}-{week}-{posteam}-{defteam}"

        candidates: list[tuple[str, str]] = []
        rush_td = float(r.get("rush_touchdown") or 0) == 1 or (float(r.get("touchdown") or 0) == 1 and float(r.get("rush_attempt") or 0) == 1)
        pass_td = float(r.get("pass_touchdown") or 0) == 1 or (float(r.get("touchdown") or 0) == 1 and float(r.get("pass_attempt") or 0) == 1 and not bool(r.get("interception")))
        if rush_td:
            pid = str(r.get("rusher_player_id") or "")
            if pid and pid.lower() != "nan":
                candidates.append((pid, "RUSHING"))
        if pass_td:
            pid = str(r.get("receiver_player_id") or "")
            if pid and pid.lower() != "nan":
                candidates.append((pid, "RECEIVING"))

        for pid, td_type in candidates:
            meta = lookup.loc[pid] if isinstance(lookup, pd.DataFrame) and pid in lookup.index else None
            if isinstance(meta, pd.DataFrame):
                meta = meta.iloc[-1]
            pos = str(meta.get("position") if meta is not None else "")
            if pos not in SCORER_POSITIONS:
                continue
            if np.isnan(yard):
                origin = "UNKNOWN"
            elif yard <= 5:
                origin = "INSIDE_5"
            elif yard <= 20:
                origin = "RED_ZONE_6_20"
            else:
                origin = "EXPLOSIVE_21_PLUS"
            rows.append({
                "game_id": str(game_id),
                "season": season,
                "week": week,
                "offense": posteam,
                "defense": defteam,
                "player_id": pid,
                "player_name": meta.get("player_name") if meta is not None else None,
                "position": pos,
                "td_type": td_type,
                "yardline_100": yard,
                "td_origin": origin,
                "is_qb_sneak": bool(pos == "QB" and td_type == "RUSHING" and re.search(r"\bsneak\b", desc, re.I)),
            })
    return pd.DataFrame(rows)


def build_defensive_td_vulnerability_state(td_history: pd.DataFrame, pbp: pd.DataFrame | None = None) -> pd.DataFrame:
    if td_history is None or td_history.empty:
        return pd.DataFrame()
    h = td_history.copy()
    # Recent seasons get more weight while preserving multi-season sample.
    seasons = pd.to_numeric(h.get("season"), errors="coerce")
    max_season = int(seasons.max()) if seasons.notna().any() else 0
    h["recency_weight"] = np.where(seasons.eq(max_season), 1.0, np.where(seasons.eq(max_season - 1), 0.76, 0.58))
    if pbp is not None and not pbp.empty and "defteam" in pbp.columns:
        gp = pbp.copy()
        gp["defense"] = gp["defteam"].fillna("").map(canonical_team)
        if "game_id" in gp.columns:
            game_counts = gp[gp["defense"].ne("")].groupby("defense")["game_id"].nunique().to_dict()
        else:
            game_counts = h.groupby("defense")["game_id"].nunique().to_dict()
    else:
        game_counts = h.groupby("defense")["game_id"].nunique().to_dict()

    red_zone_trips: dict[str, int] = {}
    if pbp is not None and not pbp.empty and "defteam" in pbp.columns and "yardline_100" in pbp.columns:
        gp = pbp.copy()
        gp["defense"] = gp["defteam"].fillna("").map(canonical_team)
        gp["_yard"] = pd.to_numeric(gp["yardline_100"], errors="coerce")
        rz = gp[gp["defense"].ne("") & gp["_yard"].le(20)].copy()
        if "drive" in rz.columns and "game_id" in rz.columns:
            trips = rz[["defense", "game_id", "drive"]].dropna().drop_duplicates()
            red_zone_trips = trips.groupby("defense").size().astype(int).to_dict()
        elif "game_id" in rz.columns:
            # Fallback is deliberately conservative: at most one red-zone trip per game.
            red_zone_trips = rz[["defense", "game_id"]].drop_duplicates().groupby("defense").size().astype(int).to_dict()

    team_path = {}
    for defense, g in h.groupby("defense"):
        rush_w = float(g.loc[g["td_type"].eq("RUSHING"), "recency_weight"].sum())
        rec_w = float(g.loc[g["td_type"].eq("RECEIVING"), "recency_weight"].sum())
        total_w = max(rush_w + rec_w, 1e-9)
        team_path[defense] = {
            "ground_td_share_allowed": rush_w / total_w,
            "air_td_share_allowed": rec_w / total_w,
            "primary_scoring_path_allowed": "GROUND" if rush_w > rec_w * 1.08 else ("AIR" if rec_w > rush_w * 1.08 else "BALANCED"),
        }
    rows: list[dict] = []
    for (defense, pos), g in h.groupby(["defense", "position"]):
        games = max(int(game_counts.get(defense, 1)), 1)
        w = pd.to_numeric(g["recency_weight"], errors="coerce").fillna(1.0)
        total = float(w.sum())
        red = float(w[g["td_origin"].isin(["INSIDE_5", "RED_ZONE_6_20"])].sum())
        inside5 = float(w[g["td_origin"].eq("INSIDE_5")].sum())
        explosive = float(w[g["td_origin"].eq("EXPLOSIVE_21_PLUS")].sum())
        rush = float(w[g["td_type"].eq("RUSHING")].sum())
        rec = float(w[g["td_type"].eq("RECEIVING")].sum())
        rows.append({
            "defense": defense,
            "position": pos,
            "games_sample": games,
            "td_allowed_weighted": total,
            "td_allowed_per_game": total / games,
            "red_zone_td_allowed_weighted": red,
            "inside5_td_allowed_weighted": inside5,
            "explosive_td_allowed_weighted": explosive,
            "rushing_td_allowed_weighted": rush,
            "receiving_td_allowed_weighted": rec,
            "red_zone_td_share": red / total if total > 0 else 0.0,
            "explosive_td_share": explosive / total if total > 0 else 0.0,
            "red_zone_trips_allowed": int(red_zone_trips.get(defense, 0)),
            "red_zone_td_rate_allowed": red / max(int(red_zone_trips.get(defense, 0)), 1),
            "ground_td_share_allowed": team_path.get(defense, {}).get("ground_td_share_allowed"),
            "air_td_share_allowed": team_path.get(defense, {}).get("air_td_share_allowed"),
            "primary_scoring_path_allowed": team_path.get(defense, {}).get("primary_scoring_path_allowed", "UNKNOWN"),
            "sample_quality": "SMALL_SAMPLE" if games < 8 else ("MEDIUM_SAMPLE" if games < 16 else "MULTI_SEASON_SAMPLE"),
            "vulnerability_cause": "SMALL_SAMPLE_UNCERTAIN" if games < 8 else "DATA_SIGNAL_ONLY_NO_UNSUPPORTED_SCHEME_ATTRIBUTION",
            "wr_alignment_resolution": "WR_AGGREGATE_NO_RELIABLE_SLOT_OUTSIDE_ALIGNMENT_IN_STANDARD_PBP" if pos == "WR" else "NOT_APPLICABLE",
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    pos_avg = out.groupby("position")["td_allowed_per_game"].mean().to_dict()
    out["position_td_vulnerability_ratio"] = [
        float(r["td_allowed_per_game"] / max(pos_avg.get(r["position"], r["td_allowed_per_game"]), 1e-6)) for _, r in out.iterrows()
    ]
    out["defense_td_multiplier"] = out["position_td_vulnerability_ratio"].clip(0.86, 1.14)
    out["vulnerability_verdict"] = np.select(
        [out["position_td_vulnerability_ratio"].ge(1.12), out["position_td_vulnerability_ratio"].le(0.88)],
        ["TARGET", "BAD_MATCHUP"],
        default="NEUTRAL",
    )
    weak = out.sort_values(["defense", "position_td_vulnerability_ratio"], ascending=[True, False]).groupby("defense").first()["position"].to_dict()
    out["weakest_position_group"] = out["defense"].map(weak)
    return out


def build_player_td_style_state(td_history: pd.DataFrame) -> pd.DataFrame:
    if td_history is None or td_history.empty:
        return pd.DataFrame()
    rows: list[dict] = []
    for pid, g in td_history.groupby("player_id"):
        total = len(g)
        in5 = int(g["td_origin"].eq("INSIDE_5").sum())
        rz = int(g["td_origin"].isin(["INSIDE_5", "RED_ZONE_6_20"]).sum())
        explosive = int(g["td_origin"].eq("EXPLOSIVE_21_PLUS").sum())
        if total < 2:
            style = "SMALL_SAMPLE"
            repeatability = 0.98
        elif explosive / total >= 0.50 and rz / total < 0.60:
            style = "DISTANCE_SCORER"
            repeatability = 0.93
        elif rz / total >= 0.72:
            style = "GOAL_LINE_RED_ZONE_SCORER"
            repeatability = 1.05
        else:
            style = "BOTH_OR_MIXED"
            repeatability = 1.01
        last = g.iloc[-1]
        rows.append({
            "gsis_id": str(pid),
            "player_name": last.get("player_name"),
            "position": last.get("position"),
            "historical_touchdowns_profiled": total,
            "inside5_td_share": in5 / total if total else 0.0,
            "red_zone_td_share": rz / total if total else 0.0,
            "explosive_21plus_td_share": explosive / total if total else 0.0,
            "td_style": style,
            "td_repeatability_multiplier": repeatability,
        })
    return pd.DataFrame(rows)


def build_qb_goal_line_state(pbp: pd.DataFrame, player_stats: pd.DataFrame) -> pd.DataFrame:
    if pbp is None or pbp.empty:
        return pd.DataFrame()
    lookup = _player_lookup(player_stats).set_index("player_id")
    p = pbp.copy()
    yard = pd.to_numeric(p.get("yardline_100"), errors="coerce") if "yardline_100" in p.columns else pd.Series(np.nan, index=p.index)
    rush = pd.to_numeric(p.get("rush_attempt"), errors="coerce").fillna(0).eq(1) if "rush_attempt" in p.columns else pd.Series(False, index=p.index)
    gl = p[rush & yard.le(5)].copy()
    if gl.empty:
        return pd.DataFrame()
    gl["posteam"] = gl["posteam"].fillna("").map(canonical_team)
    gl["rusher_player_id"] = gl.get("rusher_player_id", "").astype(str)
    team_attempts = gl.groupby("posteam").size().to_dict()
    rows=[]
    for (team, pid), g in gl.groupby(["posteam", "rusher_player_id"]):
        if pid not in lookup.index:
            continue
        meta = lookup.loc[pid]
        if isinstance(meta, pd.DataFrame): meta=meta.iloc[-1]
        if str(meta.get("position")) != "QB":
            continue
        attempts=len(g)
        sneaks=int(g.get("desc", pd.Series("", index=g.index)).astype(str).str.contains(r"\bsneak\b", case=False, regex=True).sum())
        tds=int(pd.to_numeric(g.get("rush_touchdown", 0), errors="coerce").fillna(0).eq(1).sum()) if "rush_touchdown" in g.columns else 0
        team_total=max(int(team_attempts.get(team, attempts)),1)
        share=attempts/team_total
        rows.append({
            "team":team,"gsis_id":pid,"qb_name":meta.get("player_name"),"qb_goal_line_rush_attempts":attempts,
            "team_goal_line_rush_attempts":team_total,"qb_goal_line_carry_share":share,"qb_goal_line_rush_tds":tds,
            "qb_sneak_attempts":sneaks,"qb_sneak_share_of_team_goal_line_rushes":sneaks/team_total,
            "qb_rb_competition_multiplier":float(np.clip(1.0-0.24*share-0.08*(sneaks/team_total),0.78,1.0)),
            "qb_receiving_competition_multiplier":float(np.clip(1.0-0.10*share,0.90,1.0)),
            "qb_self_rush_td_multiplier":float(np.clip(1.0+0.45*share,1.0,1.30)),
        })
    return pd.DataFrame(rows)


def attach_scorer_context(
    scorer_state: pd.DataFrame,
    slate: pd.DataFrame,
    defense_state: pd.DataFrame,
    td_style_state: pd.DataFrame,
    qb_goal_line_state: pd.DataFrame,
) -> pd.DataFrame:
    if scorer_state is None or scorer_state.empty:
        return pd.DataFrame()
    s = scorer_state.copy()
    opponent = {}
    for _, g in slate.iterrows():
        opponent[str(g["home_team"])] = str(g["away_team"])
        opponent[str(g["away_team"])] = str(g["home_team"])
    s["opponent"] = s["team"].astype(str).map(opponent)

    if td_style_state is not None and not td_style_state.empty and "gsis_id" in s.columns:
        keep=[c for c in ["gsis_id","historical_touchdowns_profiled","inside5_td_share","red_zone_td_share","explosive_21plus_td_share","td_style","td_repeatability_multiplier"] if c in td_style_state.columns]
        s=s.merge(td_style_state[keep].drop_duplicates("gsis_id"), on="gsis_id", how="left")
    if "td_repeatability_multiplier" not in s.columns: s["td_repeatability_multiplier"]=1.0
    s["td_repeatability_multiplier"]=pd.to_numeric(s["td_repeatability_multiplier"],errors="coerce").fillna(0.98).clip(0.90,1.08)
    s["td_style"]=s.get("td_style", pd.Series("NO_TD_HISTORY", index=s.index)).fillna("NO_TD_HISTORY")

    if defense_state is not None and not defense_state.empty:
        d=defense_state.rename(columns={"defense":"opponent"})
        keep=[c for c in ["opponent","position","td_allowed_per_game","red_zone_td_share","explosive_td_share","position_td_vulnerability_ratio","defense_td_multiplier","vulnerability_verdict","weakest_position_group","wr_alignment_resolution"] if c in d.columns]
        s=s.merge(d[keep].drop_duplicates(["opponent","position"]), on=["opponent","position"], how="left")
    s["defense_td_multiplier"]=pd.to_numeric(s.get("defense_td_multiplier",1.0),errors="coerce").fillna(1.0).clip(0.86,1.14)
    s["vulnerability_verdict"]=s.get("vulnerability_verdict", pd.Series("NEUTRAL", index=s.index)).fillna("NEUTRAL")

    team_qb={}
    if qb_goal_line_state is not None and not qb_goal_line_state.empty:
        q=qb_goal_line_state.sort_values("qb_goal_line_carry_share",ascending=False).drop_duplicates("team")
        team_qb=q.set_index("team").to_dict("index")
    qb_comp=[]
    qb_verdict=[]
    for _,r in s.iterrows():
        q=team_qb.get(str(r.get("team")),{})
        pos=str(r.get("position"))
        if pos=="RB": mult=float(q.get("qb_rb_competition_multiplier",1.0))
        elif pos in {"WR","TE"}: mult=float(q.get("qb_receiving_competition_multiplier",1.0))
        elif pos=="QB": mult=float(q.get("qb_self_rush_td_multiplier",1.0))
        else: mult=1.0
        share=float(q.get("qb_goal_line_carry_share",0.0) or 0.0)
        if pos=="QB": verdict="QB_SELF_SCORING_PATH"
        elif share>=0.28: verdict="QB_REAL_SCORING_THREAT"
        elif share>=0.12: verdict="QB_MINOR_SCORING_FACTOR"
        else: verdict="QB_NOT_MATERIAL"
        qb_comp.append(mult); qb_verdict.append(verdict)
    s["qb_goal_line_competition_multiplier"]=qb_comp
    s["qb_goal_line_competition_verdict"]=qb_verdict
    return s
