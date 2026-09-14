from __future__ import annotations

import numpy as np
import pandas as pd


SCORER_POSITIONS = {"QB", "RB", "WR", "TE"}
POSITION_OPPORTUNITY_TD_PRIOR = {
    "QB": 0.080,   # rushing TD per modeled rush opportunity
    "RB": 0.035,   # rush attempts + targets
    "WR": 0.065,   # targets
    "TE": 0.070,   # targets
}
POSITION_TD_GAME_PRIOR = {"QB": 0.22, "RB": 0.42, "WR": 0.34, "TE": 0.25}
DEFAULT_RUSH_OPPORTUNITY = {"QB": 4.5, "RB": 10.0, "WR": 0.3, "TE": 0.1}
DEFAULT_REC_OPPORTUNITY = {"QB": 0.0, "RB": 2.5, "WR": 5.0, "TE": 4.0}


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(0.0, index=df.index, dtype=float)
    return pd.to_numeric(df[col], errors="coerce").fillna(0.0)


def build_scorer_state(player_stats: pd.DataFrame, halflife: float = 5.0) -> pd.DataFrame:
    """Build a market-blind TD-scorer state from the same nflverse weekly player stats.

    Passing touchdowns do not count as an anytime-TD score for the passer. QB scoring state
    therefore uses rushing touchdowns only. RB/WR/TE scoring state uses rushing + receiving TDs.
    The propensity multiplier is Bayesian-smoothed toward a position opportunity baseline to
    prevent tiny samples from dominating the scorer allocation layer.
    """
    if player_stats is None or player_stats.empty:
        return pd.DataFrame()
    df = player_stats.copy()
    if "position" in df.columns:
        df = df[df["position"].isin(sorted(SCORER_POSITIONS))].copy()
    id_col = next((c for c in ["player_id", "gsis_id", "player_id_nfl"] if c in df.columns), None)
    name_col = next((c for c in ["player_display_name", "player_name", "name"] if c in df.columns), None)
    team_col = next((c for c in ["recent_team", "team", "team_abbr"] if c in df.columns), None)
    if not id_col or not name_col or not team_col:
        return pd.DataFrame()

    for c in ["carries", "targets", "rushing_tds", "receiving_tds"]:
        if c not in df.columns:
            df[c] = 0.0

    rows: list[dict] = []
    for pid, g in df.groupby(id_col):
        sort_cols = [c for c in ["season", "week"] if c in g.columns]
        if sort_cols:
            g = g.sort_values(sort_cols)
        pos = str(g.iloc[-1].get("position") or "")
        if pos not in SCORER_POSITIONS:
            continue
        carries = _num(g, "carries")
        targets = _num(g, "targets")
        rush_td = _num(g, "rushing_tds")
        rec_td = _num(g, "receiving_tds")
        scorer_td = rush_td if pos == "QB" else rush_td + rec_td
        opportunities = carries if pos == "QB" else (carries + targets if pos == "RB" else targets)
        ew = lambda s: float(s.ewm(halflife=halflife, adjust=False).mean().iloc[-1]) if len(s) else 0.0

        prior_rate = POSITION_OPPORTUNITY_TD_PRIOR[pos]
        # Type-specific priors keep rushing and receiving TD allocation separate.
        rush_prior = 0.080 if pos == "QB" else (0.035 if pos == "RB" else 0.012)
        rec_prior = 0.060 if pos in {"WR", "TE"} else (0.045 if pos == "RB" else 0.001)
        posterior_rush_rate = float((rush_td.sum() + rush_prior * 20.0) / max(carries.sum() + 20.0, 1.0))
        posterior_rec_rate = float((rec_td.sum() + rec_prior * 20.0) / max(targets.sum() + 20.0, 1.0))
        rush_propensity = float(np.clip(posterior_rush_rate / max(rush_prior, 1e-6), 0.40, 2.50))
        rec_propensity = float(np.clip(posterior_rec_rate / max(rec_prior, 1e-6), 0.40, 2.50))
        # Combined scorer propensity is retained for board diagnostics.
        posterior_rate = float((scorer_td.sum() + prior_rate * 24.0) / max(opportunities.sum() + 24.0, 1.0))
        propensity = float(np.clip(posterior_rate / max(prior_rate, 1e-6), 0.45, 2.25))
        game_prior = POSITION_TD_GAME_PRIOR[pos]
        posterior_td_game = float((scorer_td.sum() + game_prior * 4.0) / (len(g) + 4.0))

        rows.append({
            "gsis_id": str(pid),
            "player_name": g.iloc[-1][name_col],
            "team": g.iloc[-1][team_col],
            "position": pos,
            "scorer_games_observed": int(len(g)),
            "rush_tds_ewm": ew(rush_td),
            "receiving_tds_ewm": ew(rec_td),
            "scoring_tds_ewm": ew(scorer_td),
            "scoring_opportunities_ewm": ew(opportunities),
            "rush_opportunities_ewm": ew(carries),
            "receiving_opportunities_ewm": ew(targets),
            "historical_rush_td_per_carry": posterior_rush_rate,
            "historical_rec_td_per_target": posterior_rec_rate,
            "rush_td_propensity_multiplier": rush_propensity,
            "rec_td_propensity_multiplier": rec_propensity,
            "historical_td_per_game": posterior_td_game,
            "historical_td_per_opportunity": posterior_rate,
            "td_propensity_multiplier": propensity,
            "scorer_prior_source": "NFLVERSE_WEEKLY_PLAYER_STATS_BAYES_SHRINK",
        })
    return pd.DataFrame(rows)


def build_team_td_state(player_stats: pd.DataFrame, halflife: float = 6.0) -> pd.DataFrame:
    """Historical team rushing-vs-passing TD mix from the same nflverse weekly player table."""
    if player_stats is None or player_stats.empty:
        return pd.DataFrame()
    df = player_stats.copy()
    team_col = next((c for c in ["recent_team", "team", "team_abbr"] if c in df.columns), None)
    if team_col is None:
        return pd.DataFrame()
    for c in ["rushing_tds", "passing_tds"]:
        if c not in df.columns:
            df[c] = 0.0
    group_cols = [c for c in ["season", "week", team_col] if c in df.columns]
    if len(group_cols) < 2:
        return pd.DataFrame()
    weekly = df.groupby(group_cols, dropna=False).agg(
        rushing_tds=("rushing_tds", "sum"),
        passing_tds=("passing_tds", "sum"),
    ).reset_index()
    rows=[]
    for team, g in weekly.groupby(team_col):
        sort_cols=[c for c in ["season","week"] if c in g.columns]
        if sort_cols: g=g.sort_values(sort_cols)
        rush=pd.to_numeric(g["rushing_tds"], errors="coerce").fillna(0.0)
        pas=pd.to_numeric(g["passing_tds"], errors="coerce").fillna(0.0)
        rush_ew=float(rush.ewm(halflife=halflife, adjust=False).mean().iloc[-1]) if len(g) else 0.0
        pass_ew=float(pas.ewm(halflife=halflife, adjust=False).mean().iloc[-1]) if len(g) else 0.0
        # Prior centered near a 36% offensive rushing-TD share, equivalent to 4 pseudo TDs.
        share=float((rush.sum()+1.44)/max(rush.sum()+pas.sum()+4.0,1.0))
        rows.append({"team": team, "rush_tds_ewm": rush_ew, "pass_tds_ewm": pass_ew,
                     "historical_rush_td_share": float(np.clip(share,0.16,0.62)), "td_mix_weeks_observed": int(len(g))})
    return pd.DataFrame(rows)

def bootstrap_missing_scorer_state(player_map: pd.DataFrame, scorer_state: pd.DataFrame) -> pd.DataFrame:
    out = scorer_state.copy()
    existing = set(out["aita_player_id"].dropna().astype(str)) if (not out.empty and "aita_player_id" in out.columns) else set()
    if player_map is None or player_map.empty:
        return out
    rows = []
    for _, p in player_map.iterrows():
        pid = str(p.get("aita_player_id") or "")
        pos = str(p.get("position") or "")
        if not pid or pid in existing or pos not in SCORER_POSITIONS or not bool(p.get("available_for_simulation", True)):
            continue
        rows.append({
            "aita_player_id": pid,
            "gsis_id": p.get("gsis_id"),
            "player_name": p.get("full_name"),
            "team": p.get("current_team"),
            "position": pos,
            "scorer_games_observed": 0,
            "rush_tds_ewm": 0.0,
            "receiving_tds_ewm": 0.0,
            "scoring_tds_ewm": POSITION_TD_GAME_PRIOR[pos],
            "scoring_opportunities_ewm": 0.0,
            "rush_opportunities_ewm": DEFAULT_RUSH_OPPORTUNITY.get(pos, 0.0),
            "receiving_opportunities_ewm": DEFAULT_REC_OPPORTUNITY.get(pos, 0.0),
            "historical_rush_td_per_carry": 0.080 if pos == "QB" else (0.035 if pos == "RB" else 0.012),
            "historical_rec_td_per_target": 0.060 if pos in {"WR", "TE"} else (0.045 if pos == "RB" else 0.001),
            "rush_td_propensity_multiplier": 1.0,
            "rec_td_propensity_multiplier": 1.0,
            "historical_td_per_game": POSITION_TD_GAME_PRIOR[pos],
            "historical_td_per_opportunity": POSITION_OPPORTUNITY_TD_PRIOR[pos],
            "td_propensity_multiplier": 1.0,
            "scorer_prior_source": "CURRENT_DEPTH_POSITION_PRIOR",
        })
    if rows:
        out = pd.concat([out, pd.DataFrame(rows)], ignore_index=True, sort=False)
    return out
