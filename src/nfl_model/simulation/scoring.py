from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


DEFAULT_RUSH_OPPORTUNITY = {"QB": 4.5, "RB": 10.0, "WR": 0.3, "TE": 0.1}
DEFAULT_REC_OPPORTUNITY = {"QB": 0.0, "RB": 2.5, "WR": 5.0, "TE": 4.0}
RUSH_POSITION_WEIGHT = {"QB": 1.00, "RB": 1.12, "WR": 0.72, "TE": 0.55}
REC_POSITION_WEIGHT = {"RB": 0.92, "WR": 1.00, "TE": 1.07}


def _series(draws: dict[str, np.ndarray], pid: str, stat: str) -> np.ndarray | None:
    arr = draws.get(f"PLAYER|{pid}|{stat}")
    return np.asarray(arr, dtype=float) if arr is not None else None


def _fallback(base: float, n: int, rng: np.random.Generator, sigma: float) -> np.ndarray:
    base = max(float(base), 0.02)
    return np.maximum(0.01, base * rng.lognormal(mean=-0.5 * sigma**2, sigma=sigma, size=n))


def _rush_opportunity(draws: dict[str, np.ndarray], p: pd.Series, n: int, rng: np.random.Generator) -> np.ndarray:
    pid, pos = str(p["aita_player_id"]), str(p["position"])
    if pos == "RB":
        arr = _series(draws, pid, "rushing_attempts")
        if arr is not None:
            return np.maximum(arr, 0.01)
    # QB rushing attempts are intentionally not an existing prop draw in the source model; use historical
    # carries from the same nflverse player-stat input with game-level uncertainty rather than passing volume.
    base = float(p.get("rush_opportunities_ewm", DEFAULT_RUSH_OPPORTUNITY.get(pos, 0.1)) or 0.0)
    return _fallback(max(base, DEFAULT_RUSH_OPPORTUNITY.get(pos, 0.1)), n, rng, 0.20 if pos == "QB" else 0.30)


def _rec_opportunity(draws: dict[str, np.ndarray], p: pd.Series, n: int, rng: np.random.Generator) -> np.ndarray:
    pid, pos = str(p["aita_player_id"]), str(p["position"])
    targ = _series(draws, pid, "targets")
    if targ is not None:
        return np.maximum(targ, 0.01)
    rec = _series(draws, pid, "receptions")
    if rec is not None:
        return np.maximum(rec / 0.66, 0.01)
    base = float(p.get("receiving_opportunities_ewm", DEFAULT_REC_OPPORTUNITY.get(pos, 0.1)) or 0.0)
    return _fallback(max(base, DEFAULT_REC_OPPORTUNITY.get(pos, 0.1)), n, rng, 0.26)


def _allocate_dynamic_multinomial(
    rng: np.random.Generator,
    totals: np.ndarray,
    weights: np.ndarray,
    other_share: float,
) -> tuple[np.ndarray, np.ndarray]:
    n, k = weights.shape
    out = np.zeros((n, k), dtype=np.int16)
    remaining = totals.astype(np.int16).copy()
    player_sum = np.maximum(weights.sum(axis=1), 1e-9)
    os = float(np.clip(other_share, 0.02, 0.35))
    other_weight = player_sum * os / (1.0 - os)
    remaining_weight = player_sum + other_weight
    order = np.argsort(-np.nanmean(weights, axis=0))
    for j in order:
        cond = np.divide(weights[:, j], np.maximum(remaining_weight, 1e-9))
        x = rng.binomial(remaining.astype(np.int32), np.clip(cond, 0.0, 1.0)).astype(np.int16)
        out[:, j] = x
        remaining = (remaining - x).astype(np.int16)
        remaining_weight = np.maximum(1e-9, remaining_weight - weights[:, j])
    return out, remaining


def _team_rush_td_share(
    team: str,
    draws: dict[str, np.ndarray],
    team_td_state: pd.DataFrame,
    n: int,
) -> np.ndarray:
    hist = 0.36
    if team_td_state is not None and not team_td_state.empty:
        q = team_td_state[team_td_state["team"].astype(str).eq(team)]
        if not q.empty:
            hist = float(q.iloc[-1].get("historical_rush_td_share", hist))
    rush = draws.get(f"TEAM|{team}|rush_plays")
    plays = draws.get(f"TEAM|{team}|offensive_plays")
    if rush is None or plays is None:
        return np.full(n, np.clip(hist, 0.16, 0.62), dtype=float)
    run_share = np.divide(np.asarray(rush, dtype=float), np.maximum(np.asarray(plays, dtype=float), 1.0))
    # Goal-line TD mix is more stable than generic play calling; history gets most of the weight.
    share = 0.72 * hist + 0.28 * run_share
    return np.clip(share, 0.16, 0.62)


def simulate_scorers(
    slate: pd.DataFrame,
    draws: dict[str, np.ndarray],
    scorer_state: pd.DataFrame,
    player_map: pd.DataFrame,
    seed: int,
    team_td_state: pd.DataFrame | None = None,
    other_share: float = 0.12,
) -> tuple[dict[str, np.ndarray], pd.DataFrame, list[dict[str, Any]]]:
    """Allocate simulated offensive TDs to eligible players with separate rush/receive paths."""
    if slate.empty or scorer_state.empty or not draws:
        return {}, pd.DataFrame(), []
    n = len(next(iter(draws.values())))
    pm = player_map.set_index("aita_player_id") if not player_map.empty else pd.DataFrame()
    ss = scorer_state[scorer_state["position"].isin(["QB", "RB", "WR", "TE"])].copy()
    if "aita_player_id" not in ss.columns:
        return {}, pd.DataFrame(), []

    out_draws: dict[str, np.ndarray] = {}
    summary_rows: list[dict[str, Any]] = []
    recon: list[dict[str, Any]] = []
    master = np.random.default_rng(seed)

    for _, game in slate.reset_index(drop=True).iterrows():
        event_id = str(game["aita_event_id"])
        for side, team in [("home", str(game["home_team"])), ("away", str(game["away_team"]))]:
            td_key = f"GAME|{event_id}|{side}_touchdowns"
            if td_key not in draws:
                continue
            team_tds = np.asarray(draws[td_key], dtype=np.int16)
            pool = ss[ss["team"].astype(str).eq(team)].copy()
            if pool.empty:
                continue
            if not pm.empty:
                role_map = pm["role_certainty_score"].to_dict() if "role_certainty_score" in pm.columns else {}
                avail_map = pm["available_for_simulation"].to_dict() if "available_for_simulation" in pm.columns else {}
                pool["role_certainty_score"] = pool["aita_player_id"].astype(str).map(role_map).fillna(50.0)
                pool["available_for_simulation"] = pool["aita_player_id"].astype(str).map(avail_map).fillna(True)
                pool = pool[pool["available_for_simulation"].astype(bool)]
            if "primary_scorer_eligible" not in pool.columns:
                pool["primary_scorer_eligible"] = True
            def _pool_num(col: str, default: float) -> pd.Series:
                if col not in pool.columns:
                    return pd.Series(default, index=pool.index, dtype=float)
                return pd.to_numeric(pool[col], errors="coerce").fillna(default)
            pool["fantasy_role_multiplier"] = _pool_num("fantasy_role_multiplier", 1.0).clip(0.92, 1.08)
            pool["external_consensus_multiplier"] = _pool_num("external_consensus_multiplier", 1.0).clip(0.90, 1.10)
            pool["current_season_td_multiplier"] = _pool_num("current_season_td_multiplier", 1.0).clip(0.88, 1.10)
            pool["defense_td_multiplier"] = _pool_num("defense_td_multiplier", 1.0).clip(0.86, 1.14)
            pool["td_repeatability_multiplier"] = _pool_num("td_repeatability_multiplier", 0.98).clip(0.90, 1.08)
            pool["qb_goal_line_competition_multiplier"] = _pool_num("qb_goal_line_competition_multiplier", 1.0).clip(0.78, 1.30)
            pool["primary_pool_multiplier"] = np.where(pool["primary_scorer_eligible"].astype(bool), 1.0, 0.46)
            pool["context_weight_multiplier"] = (
                pool["fantasy_role_multiplier"]
                * pool["external_consensus_multiplier"]
                * pool["current_season_td_multiplier"]
                * pool["defense_td_multiplier"]
                * pool["td_repeatability_multiplier"]
                * pool["qb_goal_line_competition_multiplier"]
                * pool["primary_pool_multiplier"]
            ).clip(0.30, 1.35)
            pool["sort_score"] = (
                pd.to_numeric(pool.get("historical_td_per_game", 0.0), errors="coerce").fillna(0.0) * 3.0
                + pd.to_numeric(pool.get("role_certainty_score", 50.0), errors="coerce").fillna(50.0) / 100.0
                + _pool_num("espn_fantasy_projected_points", 0.0) / 25.0
            ) * pool["context_weight_multiplier"]
            pool = pool.sort_values("sort_score", ascending=False).head(16).reset_index(drop=True)
            if pool.empty:
                continue

            rng = np.random.default_rng(int(master.integers(1, 2**31 - 1)))
            rush_share = _team_rush_td_share(team, draws, team_td_state if team_td_state is not None else pd.DataFrame(), n)
            rushing_tds = rng.binomial(team_tds.astype(np.int32), rush_share).astype(np.int16)
            receiving_tds = (team_tds - rushing_tds).astype(np.int16)

            rush_idx = [j for j, p in pool.iterrows() if str(p["position"]) in {"QB", "RB", "WR", "TE"}]
            rec_idx = [j for j, p in pool.iterrows() if str(p["position"]) in {"RB", "WR", "TE"}]
            rush_alloc = np.zeros((n, len(pool)), dtype=np.int16)
            rec_alloc = np.zeros((n, len(pool)), dtype=np.int16)

            if rush_idx:
                cols=[]
                for j in rush_idx:
                    p=pool.iloc[j]; pos=str(p["position"])
                    opp=_rush_opportunity(draws,p,n,rng)
                    prop=float(np.clip(p.get("rush_td_propensity_multiplier",1.0) or 1.0,0.40,2.50))
                    context=float(np.clip(p.get("context_weight_multiplier",1.0) or 1.0,0.30,1.35))
                    cols.append(np.maximum(0.001, opp*prop*RUSH_POSITION_WEIGHT.get(pos,0.7)*context))
                alloc, other_rush = _allocate_dynamic_multinomial(rng, rushing_tds, np.column_stack(cols), other_share)
                for local,j in enumerate(rush_idx): rush_alloc[:,j]=alloc[:,local]
            else:
                other_rush=rushing_tds.copy()

            if rec_idx:
                cols=[]
                for j in rec_idx:
                    p=pool.iloc[j]; pos=str(p["position"])
                    opp=_rec_opportunity(draws,p,n,rng)
                    prop=float(np.clip(p.get("rec_td_propensity_multiplier",1.0) or 1.0,0.40,2.50))
                    context=float(np.clip(p.get("context_weight_multiplier",1.0) or 1.0,0.30,1.35))
                    cols.append(np.maximum(0.001, opp*prop*REC_POSITION_WEIGHT.get(pos,1.0)*context))
                alloc, other_rec = _allocate_dynamic_multinomial(rng, receiving_tds, np.column_stack(cols), other_share)
                for local,j in enumerate(rec_idx): rec_alloc[:,j]=alloc[:,local]
            else:
                other_rec=receiving_tds.copy()

            other=(other_rush+other_rec).astype(np.int16)
            total_alloc=rush_alloc+rec_alloc
            error=int(np.max(np.abs(total_alloc.sum(axis=1).astype(int)+other.astype(int)-team_tds.astype(int))))
            recon.append({
                "aita_event_id":event_id,"team":team,"max_team_td_allocation_abs_error":error,
                "mean_team_touchdowns":float(team_tds.mean()),"mean_rushing_touchdowns":float(rushing_tds.mean()),
                "mean_receiving_touchdowns":float(receiving_tds.mean()),"mean_other_touchdowns":float(other.mean()),
                "historical_rush_td_share_mean":float(rush_share.mean()),"status":"OK" if error==0 else "TD_RECONCILIATION_FAILURE",
            })
            out_draws[f"SCORER|{event_id}|{team}|OTHER|touchdowns"]=other

            for j,(_,p) in enumerate(pool.iterrows()):
                pid=str(p["aita_player_id"])
                rush_td=rush_alloc[:,j].astype(np.int16)
                rec_td=rec_alloc[:,j].astype(np.int16)
                td=(rush_td+rec_td).astype(np.int16)
                hit=(td>=1).astype(np.int8)
                out_draws[f"SCORER|{pid}|rushing_touchdowns"]=rush_td
                out_draws[f"SCORER|{pid}|receiving_touchdowns"]=rec_td
                out_draws[f"SCORER|{pid}|touchdowns"]=td
                out_draws[f"SCORER|{pid}|anytime"]=hit
                summary_rows.append({
                    "aita_event_id":event_id,"team":team,"aita_player_id":pid,"player_name":p.get("player_name"),"position":p.get("position"),
                    "expected_touchdowns":float(td.mean()),"expected_rushing_touchdowns":float(rush_td.mean()),"expected_receiving_touchdowns":float(rec_td.mean()),
                    "p_anytime_td_raw":float(hit.mean()),"p_2plus_td_raw":float((td>=2).mean()),"p_3plus_td_raw":float((td>=3).mean()),
                    "p_rushing_td_raw":float((rush_td>=1).mean()),"p_receiving_td_raw":float((rec_td>=1).mean()),
                    "historical_td_per_game":float(p.get("historical_td_per_game",np.nan)),
                    "historical_rush_td_per_carry":float(p.get("historical_rush_td_per_carry",np.nan)),
                    "historical_rec_td_per_target":float(p.get("historical_rec_td_per_target",np.nan)),
                    "rush_td_propensity_multiplier":float(p.get("rush_td_propensity_multiplier",1.0)),
                    "rec_td_propensity_multiplier":float(p.get("rec_td_propensity_multiplier",1.0)),
                    "scorer_games_observed":int(p.get("scorer_games_observed",0) or 0),"scorer_prior_source":p.get("scorer_prior_source"),
                    "roster_verified_current":bool(p.get("roster_verified_current",False)),
                    "depth_rank":p.get("depth_rank"),"primary_scorer_eligible":bool(p.get("primary_scorer_eligible",False)),
                    "espn_fantasy_projected_points":p.get("espn_fantasy_projected_points"),
                    "espn_fantasy_actual_points":p.get("espn_fantasy_actual_points"),
                    "fantasy_projection_position_rank":p.get("fantasy_projection_position_rank"),
                    "yahoo_fantasy_points":p.get("yahoo_fantasy_points"),
                    "fantasy_role_multiplier":float(p.get("fantasy_role_multiplier",1.0) or 1.0),
                    "external_consensus_score":p.get("external_consensus_score"),
                    "external_consensus_multiplier":float(p.get("external_consensus_multiplier",1.0) or 1.0),
                    "external_consensus_status":p.get("external_consensus_status","MODEL_ONLY_SIGNAL"),
                    "external_consensus_rejection_flag":bool(p.get("external_consensus_rejection_flag",False)),
                    "current_season_games":int(p.get("current_season_games",0) or 0),
                    "current_season_scorer_tds":float(p.get("current_season_scorer_tds",0.0) or 0.0),
                    "current_season_scorer_td_per_game":float(p.get("current_season_scorer_td_per_game",0.0) or 0.0),
                    "current_season_td_multiplier":float(p.get("current_season_td_multiplier",1.0) or 1.0),
                    "current_season_td_status":p.get("current_season_td_status","NO_CURRENT_SEASON_MATCH"),
                    "current_season_ppg":p.get("current_season_ppg"),
                    "current_season_offensive_td_per_game":p.get("current_season_offensive_td_per_game"),
                    "current_season_skill_ppr_per_game":p.get("current_season_skill_ppr_per_game"),
                    "current_season_offense_score":p.get("current_season_offense_score"),
                    "current_season_offense_multiplier":float(p.get("current_season_offense_multiplier",1.0) or 1.0),
                    "current_season_offense_tier":p.get("current_season_offense_tier","INSUFFICIENT_DATA"),
                    "current_scoring_suppression_flag":bool(p.get("current_scoring_suppression_flag",False)),
                    "starter_role_verified":bool(p.get("starter_role_verified",False)),
                    "starter_gate_status":p.get("starter_gate_status","UNKNOWN"),
                    "sharp_board_eligible":bool(p.get("sharp_board_eligible",p.get("primary_scorer_eligible",False))),
                    "fftoday_proj_fpts":p.get("fftoday_proj_fpts"),
                    "fftoday_proj_scorer_td_lambda":p.get("fftoday_proj_scorer_td_lambda"),
                    "fftoday_anytime_td_signal":p.get("fftoday_anytime_td_signal"),
                    "fantasypros_pos_rank":p.get("fantasypros_pos_rank"),
                    "fantasypros_avg_rank":p.get("fantasypros_avg_rank"),
                    "fantasypros_rank_stddev":p.get("fantasypros_rank_stddev"),
                    "pfr_fantasy_points":p.get("pfr_fantasy_points"),
                    "pfr_ppr_points":p.get("pfr_ppr_points"),
                    "pfr_pos_rank":p.get("pfr_pos_rank"),
                    "defense_td_multiplier":float(p.get("defense_td_multiplier",1.0) or 1.0),
                    "vulnerability_verdict":p.get("vulnerability_verdict","NEUTRAL"),
                    "td_style":p.get("td_style","NO_TD_HISTORY"),
                    "td_repeatability_multiplier":float(p.get("td_repeatability_multiplier",0.98) or 0.98),
                    "qb_goal_line_competition_multiplier":float(p.get("qb_goal_line_competition_multiplier",1.0) or 1.0),
                    "qb_goal_line_competition_verdict":p.get("qb_goal_line_competition_verdict","QB_NOT_MATERIAL"),
                    "context_weight_multiplier":float(p.get("context_weight_multiplier",1.0) or 1.0),
                })
    if any(r["status"]!="OK" for r in recon):
        raise RuntimeError(f"SCORER_RECONCILIATION_FAILED: {recon}")
    return out_draws,pd.DataFrame(summary_rows),recon
