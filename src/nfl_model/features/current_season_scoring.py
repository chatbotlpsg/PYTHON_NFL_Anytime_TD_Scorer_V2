from __future__ import annotations

import numpy as np
import pandas as pd

from nfl_model.features.scoring import POSITION_TD_GAME_PRIOR
from nfl_model.ids.teams import canonical_team
from nfl_model.utils import normalize_name


def _num(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    if col not in df.columns:
        return pd.Series(default, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce").fillna(default)


def pregame_rows(df: pd.DataFrame | None, season: int, week: int) -> pd.DataFrame:
    """Return only information that was knowable before the requested week.

    This is the anti-leakage gate used for current-season nflverse tables. Historical
    seasons are retained; current-season rows from the requested/future week are removed.
    """
    if df is None or df.empty:
        return pd.DataFrame() if df is None else df.copy()
    out = df.copy()
    if "season" not in out.columns or "week" not in out.columns:
        return out
    s = pd.to_numeric(out["season"], errors="coerce")
    w = pd.to_numeric(out["week"], errors="coerce")
    mask = s.lt(int(season)) | (s.eq(int(season)) & w.lt(int(week)))
    # Rows without a parseable season/week are unsafe for current-season form and are removed.
    return out[mask.fillna(False)].copy()


def _team_points_from_schedules(schedules: pd.DataFrame, season: int, week: int) -> pd.DataFrame:
    if schedules is None or schedules.empty:
        return pd.DataFrame(columns=["team", "current_season_team_games", "current_season_points", "current_season_ppg"])
    s = schedules.copy()
    if "season" in s.columns:
        s = s[pd.to_numeric(s["season"], errors="coerce").eq(int(season))].copy()
    if "week" in s.columns:
        s = s[pd.to_numeric(s["week"], errors="coerce").lt(int(week))].copy()
    needed = {"home_team", "away_team", "home_score", "away_score"}
    if not needed.issubset(s.columns):
        return pd.DataFrame(columns=["team", "current_season_team_games", "current_season_points", "current_season_ppg"])

    rows: list[dict] = []
    for _, r in s.iterrows():
        hs = pd.to_numeric(pd.Series([r.get("home_score")]), errors="coerce").iloc[0]
        aws = pd.to_numeric(pd.Series([r.get("away_score")]), errors="coerce").iloc[0]
        if pd.isna(hs) or pd.isna(aws):
            continue
        rows.append({"team": canonical_team(str(r.get("home_team") or "")), "points": float(hs)})
        rows.append({"team": canonical_team(str(r.get("away_team") or "")), "points": float(aws)})
    if not rows:
        return pd.DataFrame(columns=["team", "current_season_team_games", "current_season_points", "current_season_ppg"])
    x = pd.DataFrame(rows)
    x = x[x["team"].ne("")]
    return x.groupby("team", as_index=False).agg(
        current_season_team_games=("points", "size"),
        current_season_points=("points", "sum"),
        current_season_ppg=("points", "mean"),
    )


def build_current_season_scoring_context(
    player_stats: pd.DataFrame,
    schedules: pd.DataFrame,
    season: int,
    week: int,
    player_prior_games: float = 5.0,
    player_multiplier_min: float = 0.88,
    player_multiplier_max: float = 1.10,
    team_multiplier_min: float = 0.88,
    team_multiplier_max: float = 1.10,
    suppression_team_percentile: float = 0.20,
    minimum_games_for_suppression: int = 2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build pregame 2026-style scoring form without turning recent TDs into a hard truth.

    Team offense is ranked from actual points/game, offensive TD/game and (when available)
    summed skill-player PPR/game. Player TD form is Bayesian-shrunk to the position prior.
    A very weak offense + zero scorer TDs after a minimum sample is a sharp-board suppression
    flag, not a deletion from the audit/simulation universe.
    """
    ps = pregame_rows(player_stats, season, week)
    if not ps.empty and "season" in ps.columns:
        ps = ps[pd.to_numeric(ps["season"], errors="coerce").eq(int(season))].copy()

    player_rows: list[dict] = []
    team_td = pd.DataFrame()
    team_ppr = pd.DataFrame()
    if not ps.empty:
        id_col = next((c for c in ["player_id", "gsis_id", "player_id_nfl"] if c in ps.columns), None)
        name_col = next((c for c in ["player_display_name", "player_name", "name"] if c in ps.columns), None)
        team_col = next((c for c in ["recent_team", "team", "team_abbr"] if c in ps.columns), None)
        if team_col:
            ps["_team"] = ps[team_col].fillna("").map(canonical_team)
            ps["_rush_td"] = _num(ps, "rushing_tds")
            ps["_rec_td"] = _num(ps, "receiving_tds")
            ps["_offensive_td"] = ps["_rush_td"] + ps["_rec_td"]
            # receiving TDs count each passing score exactly once; do not add QB passing TDs.
            weekly_team = ps.groupby(["_team", "week"], as_index=False)["_offensive_td"].sum() if "week" in ps.columns else pd.DataFrame()
            if not weekly_team.empty:
                team_td = weekly_team.groupby("_team", as_index=False).agg(
                    current_season_offensive_tds=("_offensive_td", "sum"),
                    current_season_offensive_td_per_game=("_offensive_td", "mean"),
                    current_season_td_games=("week", "nunique"),
                ).rename(columns={"_team": "team"})
            if "fantasy_points_ppr" in ps.columns and "week" in ps.columns:
                ps["_ppr"] = _num(ps, "fantasy_points_ppr")
                weekly_ppr = ps.groupby(["_team", "week"], as_index=False)["_ppr"].sum()
                team_ppr = weekly_ppr.groupby("_team", as_index=False).agg(
                    current_season_skill_ppr_per_game=("_ppr", "mean")
                ).rename(columns={"_team": "team"})

        if id_col and name_col and team_col and "position" in ps.columns:
            for pid, g in ps.groupby(id_col, dropna=False):
                if pd.isna(pid) or str(pid).strip() in {"", "nan"}:
                    continue
                g = g.sort_values([c for c in ["season", "week"] if c in g.columns])
                pos = str(g.iloc[-1].get("position") or "").upper()
                if pos not in POSITION_TD_GAME_PRIOR:
                    continue
                rush_td = _num(g, "rushing_tds")
                rec_td = _num(g, "receiving_tds")
                scorer_td = rush_td if pos == "QB" else rush_td + rec_td
                games = int(pd.to_numeric(g.get("week"), errors="coerce").nunique()) if "week" in g.columns else int(len(g))
                games = max(games, int(len(g)) if games == 0 else games)
                tds = float(scorer_td.sum())
                prior = float(POSITION_TD_GAME_PRIOR[pos])
                pseudo = max(float(player_prior_games), 0.0)
                posterior = (tds + prior * pseudo) / max(games + pseudo, 1.0)
                mult = float(np.clip(posterior / max(prior, 1e-9), player_multiplier_min, player_multiplier_max))
                if games == 0:
                    status = "NO_CURRENT_SEASON_SAMPLE"
                elif tds == 0:
                    status = "ZERO_TD_CURRENT_SEASON"
                elif tds / max(games, 1) >= 1.0:
                    status = "HOT_TD_FORM"
                else:
                    status = "ESTABLISHED_TD_FORM"
                player_rows.append({
                    "gsis_id": str(pid),
                    "normalized_name": normalize_name(str(g.iloc[-1].get(name_col) or "")),
                    "team": canonical_team(str(g.iloc[-1].get(team_col) or "")),
                    "position": pos,
                    "current_season_games": games,
                    "current_season_rush_tds": float(rush_td.sum()),
                    "current_season_receiving_tds": float(rec_td.sum()),
                    "current_season_scorer_tds": tds,
                    "current_season_scorer_td_per_game": tds / max(games, 1),
                    "current_season_td_multiplier": mult,
                    "current_season_td_status": status,
                })

    player_state = pd.DataFrame(player_rows)
    team = _team_points_from_schedules(schedules, season, week)
    if not team_td.empty:
        team = team.merge(team_td, on="team", how="outer") if not team.empty else team_td.copy()
    if not team_ppr.empty:
        team = team.merge(team_ppr, on="team", how="outer") if not team.empty else team_ppr.copy()
    if team.empty:
        return player_state, pd.DataFrame(columns=[
            "team", "current_season_ppg", "current_season_offensive_td_per_game",
            "current_season_skill_ppr_per_game", "current_season_offense_score",
            "current_season_offense_multiplier", "current_season_offense_tier",
        ])

    metrics = [
        ("current_season_ppg", 0.55),
        ("current_season_offensive_td_per_game", 0.35),
        ("current_season_skill_ppr_per_game", 0.10),
    ]
    weighted = np.zeros(len(team), dtype=float)
    weights = np.zeros(len(team), dtype=float)
    for col, wt in metrics:
        if col not in team.columns:
            continue
        vals = pd.to_numeric(team[col], errors="coerce")
        if vals.notna().sum() == 0:
            continue
        # League-relative early-season scoring environment; higher is stronger.
        pct = vals.rank(pct=True, method="average")
        ok = pct.notna().to_numpy()
        weighted[ok] += pct[ok].to_numpy(dtype=float) * wt
        weights[ok] += wt
    score = np.divide(weighted, weights, out=np.full(len(team), 0.5, dtype=float), where=weights > 0)
    team["current_season_offense_score"] = np.clip(score, 0.0, 1.0)
    team["current_season_offense_multiplier"] = (
        float(team_multiplier_min)
        + team["current_season_offense_score"] * (float(team_multiplier_max) - float(team_multiplier_min))
    ).clip(float(team_multiplier_min), float(team_multiplier_max))

    def tier(x: float) -> str:
        if x < float(suppression_team_percentile):
            return "VERY_WEAK"
        if x < 0.40:
            return "WEAK"
        if x < 0.60:
            return "AVERAGE"
        if x < 0.80:
            return "STRONG"
        return "ELITE"

    team["current_season_offense_tier"] = team["current_season_offense_score"].map(tier)
    team["current_season_offense_suppression_threshold"] = float(suppression_team_percentile)
    team["current_season_min_games_for_suppression"] = int(minimum_games_for_suppression)
    return player_state, team


def attach_current_season_scoring_to_player_map(
    player_map: pd.DataFrame,
    player_state: pd.DataFrame,
    team_state: pd.DataFrame,
    minimum_games_for_suppression: int = 2,
) -> pd.DataFrame:
    p = player_map.copy()
    if p.empty:
        return p
    p["normalized_name"] = p["full_name"].fillna("").map(normalize_name)
    p["current_team"] = p["current_team"].fillna("").map(canonical_team)

    if player_state is not None and not player_state.empty:
        ps = player_state.copy()
        # Prefer GSIS identity, then fall back to name/team/position for new mappings.
        by_id = ps.drop_duplicates("gsis_id", keep="last").set_index("gsis_id")
        by_key = ps.drop_duplicates(["normalized_name", "team", "position"], keep="last").set_index(["normalized_name", "team", "position"])
        fields = [
            "current_season_games", "current_season_rush_tds", "current_season_receiving_tds",
            "current_season_scorer_tds", "current_season_scorer_td_per_game",
            "current_season_td_multiplier", "current_season_td_status",
        ]
        for idx, row in p.iterrows():
            rec = None
            gid = str(row.get("gsis_id") or "").strip()
            if gid and gid.lower() != "nan" and gid in by_id.index:
                rec = by_id.loc[gid]
            else:
                key = (normalize_name(str(row.get("full_name") or "")), canonical_team(str(row.get("current_team") or "")), str(row.get("position") or "").upper())
                if key in by_key.index:
                    rec = by_key.loc[key]
            if isinstance(rec, pd.DataFrame):
                rec = rec.iloc[-1]
            if rec is not None:
                for f in fields:
                    p.at[idx, f] = rec.get(f)

    defaults = {
        "current_season_games": 0,
        "current_season_rush_tds": 0.0,
        "current_season_receiving_tds": 0.0,
        "current_season_scorer_tds": 0.0,
        "current_season_scorer_td_per_game": 0.0,
        "current_season_td_multiplier": 1.0,
        "current_season_td_status": "NO_CURRENT_SEASON_MATCH",
    }
    for col, default in defaults.items():
        if col not in p.columns:
            p[col] = default
        p[col] = p[col].fillna(default)

    if team_state is not None and not team_state.empty:
        ts = team_state.drop_duplicates("team", keep="last").set_index("team")
        fields = [
            "current_season_team_games", "current_season_points", "current_season_ppg",
            "current_season_offensive_tds", "current_season_offensive_td_per_game",
            "current_season_skill_ppr_per_game", "current_season_offense_score",
            "current_season_offense_multiplier", "current_season_offense_tier",
        ]
        for f in fields:
            if f in ts.columns:
                p[f] = p["current_team"].map(ts[f].to_dict())

    if "current_season_offense_multiplier" not in p.columns:
        p["current_season_offense_multiplier"] = 1.0
    p["current_season_offense_multiplier"] = pd.to_numeric(p["current_season_offense_multiplier"], errors="coerce").fillna(1.0)
    if "current_season_offense_score" not in p.columns:
        p["current_season_offense_score"] = np.nan
    if "current_season_offense_tier" not in p.columns:
        p["current_season_offense_tier"] = "INSUFFICIENT_DATA"
    p["current_season_offense_tier"] = p["current_season_offense_tier"].fillna("INSUFFICIENT_DATA")

    games = pd.to_numeric(p["current_season_games"], errors="coerce").fillna(0)
    tds = pd.to_numeric(p["current_season_scorer_tds"], errors="coerce").fillna(0)
    p["current_scoring_suppression_flag"] = (
        p["current_season_offense_tier"].eq("VERY_WEAK")
        & games.ge(int(minimum_games_for_suppression))
        & tds.le(0.0)
    )
    p["current_scoring_sharp_eligible"] = p.get("primary_scorer_eligible", False).fillna(False).astype(bool) & ~p["current_scoring_suppression_flag"]
    return p


def attach_current_season_scoring_to_scorer_state(scorer_state: pd.DataFrame, player_map: pd.DataFrame) -> pd.DataFrame:
    if scorer_state is None or scorer_state.empty or player_map is None or player_map.empty:
        return scorer_state
    fields = [c for c in [
        "aita_player_id", "current_season_games", "current_season_rush_tds", "current_season_receiving_tds",
        "current_season_scorer_tds", "current_season_scorer_td_per_game", "current_season_td_multiplier",
        "current_season_td_status", "current_season_ppg", "current_season_offensive_td_per_game",
        "current_season_skill_ppr_per_game", "current_season_offense_score", "current_season_offense_multiplier",
        "current_season_offense_tier", "current_scoring_suppression_flag", "current_scoring_sharp_eligible",
    ] if c in player_map.columns]
    return scorer_state.merge(player_map[fields].drop_duplicates("aita_player_id"), on="aita_player_id", how="left")
