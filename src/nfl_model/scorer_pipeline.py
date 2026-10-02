from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import re
import subprocess
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from nfl_model import __version__
from nfl_model.boards.scorers import build_scorer_probability_boards, build_joint_scorer_boards
from nfl_model.config import AppConfig
from nfl_model.normalize.market import attach_player_ids
from nfl_model.package.handoff import deterministic_zip, boundary_manifest
from nfl_model.pipeline import (
    ingest_football,
    simulate_slate,
    _subset_state_for_slate,
    _map_odds_events,
    _build_game_pricing_board,
)
from nfl_model.pricing.scorer import normalize_anytime_td_market, price_anytime_td_rows
from nfl_model.pricing.odds import american_to_implied
from nfl_model.providers.odds_api.client import OddsAPIClient
from nfl_model.providers.odds_api.normalize import normalize_event_odds
from nfl_model.utils import utc_now_iso


@dataclass
class ScorerPipelineArtifacts:
    run_id: str
    run_dir: Path
    handoff_zip: Path


def make_scorer_run_id(season: int, week: int, label: str | None = None) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = f"NFL-SCORER-{season}-W{week:02d}-{stamp}"
    if label:
        clean = re.sub(r"[^A-Za-z0-9_-]+", "_", label.strip().upper()).strip("_")
        if clean:
            base += f"-{clean}"
    return base


def _git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "UNAVAILABLE"


def _subset_by_date(state: dict[str, Any], slate_date: str | None) -> dict[str, Any]:
    if not slate_date:
        return state
    target = pd.Timestamp(slate_date).date()
    slate = state["slate"].copy()
    local = pd.to_datetime(slate["kickoff_utc"], utc=True, errors="coerce").dt.tz_convert(ZoneInfo("America/New_York"))
    ids = slate.loc[local.dt.date.eq(target), "aita_event_id"].astype(str).tolist()
    if not ids:
        raise RuntimeError(f"NO_GAMES_FOR_SLATE_DATE: {slate_date}")
    out = _subset_state_for_slate(state, ids)
    out["selected_slate_date"] = slate_date
    return out


def _odds_client(cfg: AppConfig) -> OddsAPIClient:
    o = cfg.get("odds")
    return OddsAPIClient(
        cfg.get("providers", "odds_base"),
        cfg.root / cfg.get("storage", "cache_dir") / "odds_api",
        cfg.root / cfg.get("storage", "raw_dir") / "odds_api" / "quota_ledger.jsonl",
        bookmakers=list(o["bookmakers"]), reserve=int(o["monthly_credit_reserve"]),
        ttl_minutes=int(o["cache_ttl_minutes"]), timeout=int(o["timeout_seconds"]), max_retries=int(o["max_retries"]),
    )


def _provider_health_json(health: dict, odds_client: OddsAPIClient | None) -> dict:
    out = dict(health)
    if odds_client is not None:
        out["odds_api"] = "OK"
        out["odds_credits_remaining"] = odds_client.last_remaining
    return out


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    (df if isinstance(df, pd.DataFrame) else pd.DataFrame()).to_csv(path, index=False)


def _candidate_id(row: pd.Series, run_id: str) -> str:
    raw = "|".join(map(str, [run_id, row.get("aita_event_id"), row.get("aita_player_id"), row.get("bookmaker"), row.get("american_odds")]))
    return f"NFL-SCORER-CAND-{hashlib.sha1(raw.encode()).hexdigest()[:18].upper()}"


def _final_markdown(run_id: str, boards: dict[str, pd.DataFrame]) -> str:
    parts = [
        f"# NFL Touchdown Scorer Boards — {run_id}", "",
        "Python probability/EV snapshot only. Live execution and parlay quoting belong to the separate Trading Agent.", "",
        "## Doctrine", "",
        "- Current ESPN roster verification is a hard gate. Unverified/stale historical names cannot enter primary scorer or EV boards.",
        "- Starter verification is a hard promotion gate: primary/EV boards require ESPN depth-rank 1 at QB/RB/WR/TE; fantasy projections cannot promote backups.",
        "- Current-season pregame scoring form uses only completed prior weeks: team PPG/offensive TD/PPR strength and player scorer TD production are bounded modifiers.",
        "- Very-weak offenses plus zero current-season scorer TDs after the minimum sample are suppressed from sharp/EV promotion but retained in audit simulation data.",
        "- Slate position boards and matchup probability boards are market-blind and are produced before sportsbook pricing.",
        "- ESPN fantasy plus public FFToday/FantasyPros/PFR data are capped role/opportunity corroboration layers, not direct sportsbook-price inputs. Yahoo remains optional and is not required.",
        "- Defensive TD vulnerability is based on scores allowed by position and field location; yardage alone is not treated as red-zone weakness.",
        "- Player TD style distinguishes goal-line/red-zone scoring from 21+ yard explosive scoring.",
        "- QB goal-line/sneak usage is modeled as competition for RB/receiver touchdown share.",
        "- EV boards are price-sensitive and require the frozen sportsbook reference price.",
        "- Joint pair/triple boards are empirical shared-Monte-Carlo probabilities; do not replace them with independence multiplication.", "",
    ]
    ordered = [
        ("Most Probable QB Scorers — Slate", "qb"),
        ("Most Probable RB Scorers — Slate", "rb"),
        ("Most Probable WR Scorers — Slate", "wr"),
        ("Most Probable TE Scorers — Slate", "te"),
        ("Most Probable Scorers — Whole Slate", "slate"),
        ("Most Probable Scorers — By Matchup", "matchup"),
        ("EV+ Scorer Board", "ev"),
        ("EV Edge Leaderboard", "leaderboard"),
    ]
    cols = [
        "position_slate_rank", "slate_rank", "matchup_rank", "game_label", "player_name", "position", "team", "opponent",
        "p_anytime_td_raw", "p_rushing_td_raw", "p_receiving_td_raw", "fair_anytime_td_odds_raw",
        "depth_rank", "starter_role_verified", "starter_gate_status",
        "current_season_games", "current_season_scorer_tds", "current_season_scorer_td_per_game",
        "current_season_ppg", "current_season_offensive_td_per_game", "current_season_offense_tier",
        "current_scoring_suppression_flag", "espn_fantasy_projected_points", "fantasy_projection_position_rank",
        "fftoday_proj_fpts", "fftoday_anytime_td_signal", "fantasypros_pos_rank", "fantasypros_rank_stddev", "pfr_pos_rank",
        "external_consensus_status", "external_consensus_score", "sharp_board_eligible",
        "vulnerability_verdict", "td_style", "qb_goal_line_competition_verdict", "role_certainty_score",
        "bookmaker", "american_odds", "p_conservative", "ev_conservative_pct", "buy_to_price", "hard_stop_price", "confidence_score",
    ]
    for title, key in ordered:
        df = boards.get(key, pd.DataFrame())
        parts += [f"## {title}", ""]
        if df.empty:
            parts += ["No qualified rows.", ""]
        else:
            keep = [c for c in cols if c in df.columns]
            parts += [df[keep].head(200).to_markdown(index=False), ""]
    return "\n".join(parts)


def _write_parlay_protocol(path: Path) -> None:
    path.write_text(
        """# NFL Scorer Trading-Agent Parlay Protocol\n\n"
        "1. Re-verify every straight scorer price and the sportsbook's actual parlay/SGP payout at decision time.\n"
        "2. Use `NFL_SCORER_JOINT_PAIR_BOARD` for 2-leg scorer combinations and `NFL_SCORER_JOINT_TRIPLE_BOARD` for covered 3-leg combinations.\n"
        "3. Never multiply same-game leg probabilities when an empirical joint row exists.\n"
        "4. For a quoted parlay price, compute EV per $1 as `p_joint * profit_per_dollar - (1-p_joint)` and EV% = 100*EV.\n"
        "5. A parlay is actionable only if the CURRENT quoted payout clears the configured parlay EV floor after a conservative probability haircut.\n"
        "6. If a desired 3+ leg combination is not present in the joint board, do not invent correlation. Request a larger joint-board run or restrict to mathematically supported combinations.\n"
        "7. Straight-leg EV+ status is useful context but the parlay's own joint EV at the live payout is the final mathematical test.\n"
        "8. Record actual entry, closing straight prices when available, result, realized P&L, and CLV/price movement in Dataset B.\n"
        """,
        encoding="utf-8",
    )


def build_scorer_handoff(
    cfg: AppConfig,
    season: int,
    week: int,
    run_id: str,
    state: dict[str, Any],
    draws: dict[str, np.ndarray],
    priced: pd.DataFrame,
    game_pricing: pd.DataFrame,
    odds_client: OddsAPIClient | None,
    quota_report: dict[str, Any],
    lineage: dict[str, Any],
) -> ScorerPipelineArtifacts:
    outputs_root = cfg.root / cfg.get("storage", "outputs_dir")
    run_dir = outputs_root / run_id
    if run_dir.exists():
        raise RuntimeError(f"Immutable run already exists: {run_dir}")
    run_dir.mkdir(parents=True)

    snapshot_time = utc_now_iso()
    prob = build_scorer_probability_boards(
        state.get("scorer_sim_summary", pd.DataFrame()),
        state["slate"],
        state["player_map"],
        run_id,
        snapshot_time,
        probability_floor=float(cfg.get("scoring", "primary_board_probability_floor", default=0.08)),
        matchup_max_players=int(cfg.get("scoring", "primary_matchup_max_players", default=12)),
        position_max_players=int(cfg.get("scoring", "primary_position_max_players", default=24)),
        slate_max_players=int(cfg.get("scoring", "primary_slate_max_players", default=60)),
    )
    joint = build_joint_scorer_boards(
        prob["slate"], draws, run_id,
        top_pair_candidates=int(cfg.get("scoring", "joint_pair_top_n", default=30)),
        top_triple_candidates=int(cfg.get("scoring", "joint_triple_top_n", default=15)),
    )
    if not priced.empty:
        priced = priced.copy()
        priced["candidate_id"] = priced.apply(lambda r: _candidate_id(r, run_id), axis=1)
        labels = prob["slate"][["aita_event_id", "aita_player_id", "game_label"]].drop_duplicates()
        priced = priced.merge(labels, on=["aita_event_id", "aita_player_id"], how="left")
    ev = priced[priced["model_status"].eq("ACTIONABLE_AT_REFERENCE_PRICE")].copy() if not priced.empty else pd.DataFrame()
    if not ev.empty:
        ev["matchup_ev_rank"] = ev.groupby("aita_event_id")["ev_conservative_pct"].rank(method="first", ascending=False).astype(int)
        ev["slate_ev_rank"] = ev["ev_conservative_pct"].rank(method="first", ascending=False).astype(int)
    leaderboard = ev.sort_values(["ev_conservative_pct", "confidence_score"], ascending=False).copy() if not ev.empty else ev.copy()
    rejection = priced[~priced["model_status"].eq("ACTIONABLE_AT_REFERENCE_PRICE")].copy() if not priced.empty else pd.DataFrame()

    parlay_parts = []
    if not joint["pairs"].empty:
        x = joint["pairs"].copy()
        x["parlay_type"] = "2_LEG_SCORER"
        x["legs"] = x["leg1_player"].astype(str) + " + " + x["leg2_player"].astype(str)
        x["parlay_ev_status"] = "NEEDS_LIVE_PARLAY_QUOTE"
        x["minimum_required_parlay_ev_pct"] = float(cfg.get("scoring", "parlay_ev_floor", default=0.08)) * 100.0
        parlay_parts.append(x)
    if not joint["triples"].empty:
        x = joint["triples"].copy()
        x["parlay_type"] = "3_LEG_SCORER"
        x["legs"] = x["leg1_player"].astype(str) + " + " + x["leg2_player"].astype(str) + " + " + x["leg3_player"].astype(str)
        x["parlay_ev_status"] = "NEEDS_LIVE_PARLAY_QUOTE"
        x["minimum_required_parlay_ev_pct"] = float(cfg.get("scoring", "parlay_ev_floor", default=0.08)) * 100.0
        parlay_parts.append(x)
    parlay_candidates = pd.concat(parlay_parts, ignore_index=True, sort=False) if parlay_parts else pd.DataFrame()
    if not parlay_candidates.empty:
        parlay_candidates = parlay_candidates.sort_values(["p_joint_model_raw", "parlay_type"], ascending=[False, True]).reset_index(drop=True)
        parlay_candidates["slate_parlay_probability_rank"] = np.arange(1, len(parlay_candidates) + 1)

    boards = {**prob, "ev": ev, "leaderboard": leaderboard, "rejection": rejection, "pairs": joint["pairs"], "triples": joint["triples"], "parlay_candidates": parlay_candidates}

    tag = f"{season}-W{week:02d}"
    _write_csv(state["slate"], run_dir / f"NFL_SCORER_SLATE_{tag}.csv")
    _write_csv(state.get("team_state", pd.DataFrame()), run_dir / f"NFL_SCORER_TEAM_STATE_{tag}.csv")
    _write_csv(state.get("current_season_team_scoring", pd.DataFrame()), run_dir / f"NFL_SCORER_CURRENT_SEASON_TEAM_OFFENSE_{tag}.csv")
    _write_csv(state.get("current_season_player_scoring", pd.DataFrame()), run_dir / f"NFL_SCORER_CURRENT_SEASON_PLAYER_TD_FORM_{tag}.csv")
    _write_csv(state.get("game_day_override_audit", pd.DataFrame()), run_dir / f"NFL_SCORER_GAMEDAY_OVERRIDE_AUDIT_{tag}.csv")
    _write_csv(state.get("scorer_state", pd.DataFrame()), run_dir / f"NFL_SCORER_PLAYER_STATE_{tag}.csv")
    _write_csv(game_pricing, run_dir / f"NFL_SCORER_GAME_CONTEXT_BOARD_{tag}.csv")
    _write_csv(prob["qb"], run_dir / f"NFL_SCORER_QB_SLATE_PROBABILITY_BOARD_{tag}.csv")
    _write_csv(prob["rb"], run_dir / f"NFL_SCORER_RB_SLATE_PROBABILITY_BOARD_{tag}.csv")
    _write_csv(prob["wr"], run_dir / f"NFL_SCORER_WR_SLATE_PROBABILITY_BOARD_{tag}.csv")
    _write_csv(prob["te"], run_dir / f"NFL_SCORER_TE_SLATE_PROBABILITY_BOARD_{tag}.csv")
    _write_csv(prob["slate"], run_dir / f"NFL_SCORER_SLATE_PROBABILITY_BOARD_{tag}.csv")
    _write_csv(prob["matchup"], run_dir / f"NFL_SCORER_MATCHUP_PROBABILITY_BOARD_{tag}.csv")
    _write_csv(prob["all"], run_dir / f"NFL_SCORER_FULL_MODEL_AUDIT_BOARD_{tag}.csv")
    _write_csv(state.get("player_map", pd.DataFrame()), run_dir / f"NFL_SCORER_CURRENT_ROSTER_VALIDATION_BOARD_{tag}.csv")
    _write_csv(state.get("espn_team_leaders", pd.DataFrame()), run_dir / f"NFL_SCORER_ESPN_TOP_STATS_BOARD_{tag}.csv")
    _write_csv(state.get("fantasy_context", pd.DataFrame()), run_dir / f"NFL_SCORER_FANTASY_CONTEXT_BOARD_{tag}.csv")
    _write_csv(state.get("fftoday", pd.DataFrame()), run_dir / f"NFL_SCORER_FFTODAY_WEEKLY_PROJECTIONS_{tag}.csv")
    _write_csv(state.get("fantasypros", pd.DataFrame()), run_dir / f"NFL_SCORER_FANTASYPROS_WEEKLY_RANKINGS_{tag}.csv")
    _write_csv(state.get("pfr_fantasy", pd.DataFrame()), run_dir / f"NFL_SCORER_PFR_CURRENT_FANTASY_ACTUALS_{tag}.csv")
    _write_csv(state.get("external_fantasy_context", pd.DataFrame()), run_dir / f"NFL_SCORER_EXTERNAL_FANTASY_CONSENSUS_BOARD_{tag}.csv")
    _write_csv(state.get("defense_td_state", pd.DataFrame()), run_dir / f"NFL_SCORER_DEFENSIVE_TD_VULNERABILITY_BOARD_{tag}.csv")
    _write_csv(state.get("td_style_state", pd.DataFrame()), run_dir / f"NFL_SCORER_PLAYER_TD_STYLE_BOARD_{tag}.csv")
    _write_csv(state.get("qb_goal_line_state", pd.DataFrame()), run_dir / f"NFL_SCORER_QB_GOAL_LINE_COMPETITION_BOARD_{tag}.csv")
    _write_csv(priced, run_dir / f"NFL_SCORER_MARKET_SNAPSHOT_{tag}.csv")
    _write_csv(ev, run_dir / f"NFL_SCORER_EV_PLAY_BOARD_{tag}.csv")
    _write_csv(ev.sort_values(["aita_event_id", "matchup_ev_rank"]) if not ev.empty else ev, run_dir / f"NFL_SCORER_MATCHUP_EV_PLAY_BOARD_{tag}.csv")
    _write_csv(leaderboard, run_dir / f"NFL_SCORER_SLATE_EV_PLAY_BOARD_{tag}.csv")
    _write_csv(leaderboard, run_dir / f"NFL_SCORER_EDGE_LEADERBOARD_{tag}.csv")
    _write_csv(rejection, run_dir / f"NFL_SCORER_REJECTION_BOARD_{tag}.csv")
    _write_csv(joint["pairs"], run_dir / f"NFL_SCORER_JOINT_PAIR_BOARD_{tag}.csv")
    _write_csv(joint["triples"], run_dir / f"NFL_SCORER_JOINT_TRIPLE_BOARD_{tag}.csv")
    _write_csv(parlay_candidates, run_dir / f"NFL_SCORER_PARLAY_MATH_CANDIDATE_BOARD_{tag}.csv")

    matchup_dir = run_dir / "MATCHUPS"
    matchup_dir.mkdir(exist_ok=True)
    for _, game in state["slate"].iterrows():
        eid = str(game["aita_event_id"])
        label = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{game['away_team']}_AT_{game['home_team']}").strip("_")
        game_prob = prob["matchup"][prob["matchup"]["aita_event_id"].astype(str).eq(eid)]
        _write_csv(game_prob, matchup_dir / f"SCORERS_{label}.csv")
        for pos in ["QB", "RB", "WR", "TE"]:
            _write_csv(game_prob[game_prob["position"].astype(str).eq(pos)], matchup_dir / f"SCORERS_{pos}_{label}.csv")
        if not ev.empty:
            _write_csv(ev[ev["aita_event_id"].astype(str).eq(eid)].sort_values("matchup_ev_rank"), matchup_dir / f"EV_{label}.csv")
        else:
            _write_csv(pd.DataFrame(), matchup_dir / f"EV_{label}.csv")
    _write_csv(state.get("scorer_sim_summary", pd.DataFrame()), run_dir / f"NFL_SCORER_MONTE_CARLO_SUMMARY_{tag}.csv")
    _write_csv(pd.DataFrame(state.get("scorer_reconciliation", [])), run_dir / f"NFL_SCORER_RECONCILIATION_{tag}.csv")

    health = _provider_health_json(state.get("provider_health", {}), odds_client)
    (run_dir / f"NFL_SCORER_PROVIDER_HEALTH_{tag}.json").write_text(json.dumps(health, indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / f"NFL_SCORER_ODDS_QUOTA_REPORT_{tag}.json").write_text(json.dumps(quota_report, indent=2, sort_keys=True), encoding="utf-8")
    metadata = {
        "model_family": "AITA_NFL_TOUCHDOWN_SCORER",
        "model_version": __version__,
        "source_foundation": "AITA_NFL_PLAYER_PROP_PIPELINE_0.4.1a1",
        "market": "player_anytime_td",
        "scorer_definition": "OFFENSIVE_RUSHING_OR_RECEIVING_TOUCHDOWN;PASSING_TD_DOES_NOT_CREDIT_PASSER;RETURN_AND_FUMBLE_RECOVERY_PLAYER_PATHS_NOT_NAMED_IN_V0.2",
        "probability_board_doctrine": "MARKET_BLIND_CURRENT_ROSTER_VERIFIED_STARTER_ONLY_CURRENT_SEASON_SCORING_FORM_EXTERNAL_CHALLENGER_BOUNDED",
        "starter_gate_doctrine": "PRIMARY_AND_EV_PROMOTION_REQUIRE_ESPN_DEPTH_RANK_1;FANTASY_CANNOT_OVERRIDE_BACKUP_STATUS",
        "current_season_scoring_doctrine": "ONLY_PRIOR_COMPLETED_WEEKS;TEAM_PPG_OFFENSIVE_TD_PPR_BOUNDED_SCORE_PRIOR;PLAYER_TD_FORM_BAYES_SHRUNK;VERY_WEAK_PLUS_ZERO_TD_CAN_SUPPRESS_SHARP_PROMOTION",
        "external_consensus_doctrine": "FFTODAY_45_FANTASYPROS_35_PFR_20_NORMALIZED_OVER_AVAILABLE_SOURCES;MULTIPLIER_CAPPED_0.90_1.10;MULTISOURCE_DISAGREEMENT_CAN_BLOCK_SHARP_EV_PROMOTION",
        "ev_board_doctrine": "PRICE_SENSITIVE_CONSERVATIVE_EV",
        "parlay_doctrine": "TRADING_AGENT_MUST_USE_EMPIRICAL_JOINT_PROBABILITY_AND_LIVE_PARLAY_PAYOUT",
        "pipeline_boundary": boundary_manifest(),
    }
    (run_dir / "NFL_SCORER_MODEL_METADATA.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / "NFL_SCORER_DATA_LINEAGE.json").write_text(json.dumps(lineage, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "run_id": run_id,
        "model_version": __version__,
        "git_commit": _git_commit(cfg.root),
        "season": season,
        "week": week,
        "run_timestamp_utc": utc_now_iso(),
        "config_hash": cfg.config_hash,
        "simulation_count": int(len(next(iter(draws.values()))) if draws else 0),
        "slate_date": state.get("selected_slate_date"),
        "game_day_starter_overrides": state.get("game_day_starter_overrides", []),
        "game_day_inactive_overrides": state.get("game_day_inactive_overrides", []),
        "pipeline_boundary": boundary_manifest(),
    }
    (run_dir / f"NFL_SCORER_RUN_MANIFEST_{tag}.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / f"NFL_SCORER_FINAL_BOARDS_{tag}.md").write_text(_final_markdown(run_id, boards), encoding="utf-8")
    _write_parlay_protocol(run_dir / "TRADING_AGENT_PARLAY_PROTOCOL.md")
    trading_prompt = cfg.root / "NFL Scorer Agent" / "NFL_SCORER_TRADING_AGENT_USER_INPUT_PROMPT_V1.md"
    if trading_prompt.exists():
        (run_dir / trading_prompt.name).write_bytes(trading_prompt.read_bytes())
    (run_dir / "README.md").write_text(
        f"# AITA NFL Touchdown Scorer Trading-Agent Handoff\n\nRun: `{run_id}`\n\n"
        "Python owns football-state ingestion, scorer probability simulation, straight scorer pricing/EV, and empirical scorer joint probabilities. "
        "The separate Trading Agent owns live price verification, live parlay quote capture, final parlay EV, execution, close capture, CLV, and grading.\n",
        encoding="utf-8",
    )
    zip_path = outputs_root / f"NFL_SCORER_TRADING_AGENT_HANDOFF_{tag}_{run_id}.zip"
    deterministic_zip(run_dir, zip_path)
    return ScorerPipelineArtifacts(run_id, run_dir, zip_path)


def run_scorer_live(
    cfg: AppConfig,
    season: int,
    week: int,
    draws_n: int | None = None,
    slate_date: str | None = None,
    selected_aita_event_ids: list[str] | None = None,
    slate_label: str | None = None,
    starter_overrides: list[str] | None = None,
    inactive_players: list[str] | None = None,
) -> ScorerPipelineArtifacts:
    load_dotenv(cfg.root / ".env")
    run_id = make_scorer_run_id(season, week, slate_label or (slate_date.replace("-", "") if slate_date else None))
    state = ingest_football(cfg, season, week, starter_overrides=starter_overrides, inactive_players=inactive_players)
    state = _subset_by_date(state, slate_date)
    state = _subset_state_for_slate(state, selected_aita_event_ids)
    draws_n = int(draws_n or cfg.get("simulation", "production_draws", default=500000))
    draws, _, player_recon = simulate_slate(cfg, season, week, state, draws_n)

    odds_client = _odds_client(cfg)
    o = cfg.get("odds")
    events = odds_client.events(o["sport_key"])
    event_to_aita, event_teams = _map_odds_events(events, state["slate"])
    eligible = [e for e in events if str(e.get("id")) in event_to_aita]
    reserve = int(o["monthly_credit_reserve"])
    planned_max = 3 + 2 * len(eligible)  # mainlines + initial scorer pull + possible scorer reprice per event
    if odds_client.last_remaining is not None and odds_client.last_remaining - planned_max < reserve:
        raise RuntimeError(f"BLOCKED_BY_QUOTA_GOVERNOR: remaining={odds_client.last_remaining} planned={planned_max} reserve={reserve}")
    quota_report = {
        "events": len(eligible), "mainline_market_families": 3, "scorer_market_families": 1,
        "planned_max_internal_credits": planned_max, "credits_remaining_before_paid_calls": odds_client.last_remaining,
        "monthly_credit_reserve": reserve,
    }

    main_raw = odds_client.mainlines(o["sport_key"], list(o["mainlines"]))
    main_df = normalize_event_odds(main_raw, utc_now_iso())
    if not main_df.empty:
        main_df["aita_event_id"] = main_df["odds_api_event_id"].astype(str).map(event_to_aita)
        main_df = main_df[main_df["aita_event_id"].notna()].copy()
    game_pricing = _build_game_pricing_board(main_df, state["slate"], draws)

    frames = []
    for ev in eligible:
        payload = odds_client.event_odds(o["sport_key"], str(ev["id"]), ["player_anytime_td"])
        f = normalize_anytime_td_market(normalize_event_odds(payload, utc_now_iso()))
        if not f.empty:
            frames.append(f)
    odds = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not odds.empty:
        odds["aita_event_id"] = odds["odds_api_event_id"].astype(str).map(event_to_aita)
        odds = attach_player_ids(odds, state["player_map"], event_teams)
        priced = price_anytime_td_rows(
            odds, draws, state["player_map"],
            ev_floor=float(cfg.get("scoring", "straight_ev_floor", default=0.06)),
            market_trust=float(cfg.get("scoring", "market_trust", default=0.28)),
            week=week,
            week1_multiplier=float(cfg.get("uncertainty", "week1_multiplier", default=1.35)),
            max_haircut_fraction=float(cfg.get("uncertainty", "max_edge_haircut_fraction", default=0.80)),
            max_market_age_minutes=float(cfg.get("pricing", "max_market_age_minutes", default=90.0)),
            buy_to_extra_ev_margin=float(cfg.get("pricing", "buy_to_extra_ev_margin", default=0.01)),
            hard_stop_extra_ev_margin=float(cfg.get("pricing", "hard_stop_extra_ev_margin", default=0.0)),
            convergence_checkpoints=[int(x) for x in cfg.get("simulation", "convergence_checkpoints")],
            convergence_tolerance=float(cfg.get("simulation", "probability_tolerance")),
        )
    else:
        priced = pd.DataFrame()

    # Refresh only events that currently contain at least one actionable scorer. Replace the entire event's scorer
    # reference snapshot so the handoff cannot mix stale and refreshed book rows for the same game.
    if not priced.empty:
        candidate_events = priced.loc[priced["model_status"].eq("ACTIONABLE_AT_REFERENCE_PRICE"), "odds_api_event_id"].astype(str).drop_duplicates().tolist()
        refreshed = []
        for oid in candidate_events:
            payload = odds_client.event_odds(o["sport_key"], oid, ["player_anytime_td"], force_refresh=True)
            f = normalize_anytime_td_market(normalize_event_odds(payload, utc_now_iso()))
            if f.empty:
                continue
            f["aita_event_id"] = f["odds_api_event_id"].astype(str).map(event_to_aita)
            f = attach_player_ids(f, state["player_map"], event_teams)
            refreshed.append(price_anytime_td_rows(
                f, draws, state["player_map"],
                ev_floor=float(cfg.get("scoring", "straight_ev_floor", default=0.06)),
                market_trust=float(cfg.get("scoring", "market_trust", default=0.28)),
                week=week,
                week1_multiplier=float(cfg.get("uncertainty", "week1_multiplier", default=1.35)),
                max_haircut_fraction=float(cfg.get("uncertainty", "max_edge_haircut_fraction", default=0.80)),
                max_market_age_minutes=float(cfg.get("pricing", "max_market_age_minutes", default=90.0)),
                buy_to_extra_ev_margin=float(cfg.get("pricing", "buy_to_extra_ev_margin", default=0.01)),
                hard_stop_extra_ev_margin=float(cfg.get("pricing", "hard_stop_extra_ev_margin", default=0.0)),
                convergence_checkpoints=[int(x) for x in cfg.get("simulation", "convergence_checkpoints")],
                convergence_tolerance=float(cfg.get("simulation", "probability_tolerance")),
            ))
        if refreshed:
            refreshed_df = pd.concat(refreshed, ignore_index=True, sort=False)
            keep = ~priced["odds_api_event_id"].astype(str).isin(candidate_events)
            priced = pd.concat([priced.loc[keep], refreshed_df], ignore_index=True, sort=False)

    quota_report["credits_remaining_after_pricing"] = odds_client.last_remaining
    lineage = {
        "scoreboard_snapshot": str(state.get("scoreboard_snapshot")),
        "same_data_inputs_as_player_prop_model": True,
        "football_inputs": ["ESPN_SCOREBOARD", "ESPN_ROSTERS", "ESPN_DEPTH_CHARTS", "ESPN_INJURIES", "ESPN_TRANSACTIONS", "ESPN_TEAM_LEADERS", "ESPN_FANTASY_PROJECTIONS", "FFTODAY_PUBLIC_WEEKLY_PROJECTIONS", "FANTASYPROS_PUBLIC_WEEKLY_CONSENSUS", "PFR_PUBLIC_CURRENT_FANTASY_ACTUALS", "YAHOO_FANTASY_OPTIONAL_OAUTH", "NFLVERSE_PBP", "NFLVERSE_PLAYER_STATS", "NFLVERSE_SNAP_COUNTS", "NWS_WEATHER"],
        "pricing_inputs": ["THE_ODDS_API_MAINLINES", "THE_ODDS_API_PLAYER_ANYTIME_TD"],
        "scorer_reconciliation": state.get("scorer_reconciliation", []),
        "player_simulation_reconciliation": player_recon,
        "selected_slate_date": slate_date,
        "selected_aita_event_ids": state["slate"]["aita_event_id"].astype(str).tolist(),
    }
    return build_scorer_handoff(cfg, season, week, run_id, state, draws, priced, game_pricing, odds_client, quota_report, lineage)


def run_scorer_demo(cfg: AppConfig, season: int, week: int, draws_n: int = 50000) -> ScorerPipelineArtifacts:
    """Offline deterministic scorer/EV/joint-handoff proof without provider or Odds API calls."""
    rng = np.random.default_rng(260913)
    n = int(draws_n)
    run_id = make_scorer_run_id(season, week, "DEMO")
    eid = f"NFL-SCORER-DEMO-{season}-W{week:02d}"
    slate = pd.DataFrame([{"aita_event_id": eid, "season": season, "week": week, "kickoff_utc": f"{season}-09-13T17:00:00Z", "home_team": "KC", "away_team": "BUF"}])
    players = [
        ("P1", "Demo KC RB", "RB", "KC", .49), ("P2", "Demo KC WR", "WR", "KC", .37),
        ("P3", "Demo BUF QB", "QB", "BUF", .29), ("P4", "Demo BUF WR", "WR", "BUF", .34),
    ]
    draws: dict[str, np.ndarray] = {}
    summary = []
    pm_rows = []
    for pid, name, pos, team, p in players:
        latent = rng.random(n)
        hit = (latent < p).astype(np.int8)
        td = hit + ((latent < p * .16) & (rng.random(n) < .45)).astype(np.int8)
        draws[f"SCORER|{pid}|anytime"] = hit
        draws[f"SCORER|{pid}|touchdowns"] = td
        summary.append({"aita_event_id": eid, "team": team, "aita_player_id": pid, "player_name": name, "position": pos,
                        "expected_touchdowns": float(td.mean()), "p_anytime_td_raw": float(hit.mean()), "p_2plus_td_raw": float((td>=2).mean()), "p_3plus_td_raw": 0.0,
                        "historical_td_per_game": p, "historical_td_per_opportunity": .04, "td_propensity_multiplier": 1.0, "scorer_games_observed": 20, "scorer_prior_source": "DEMO"})
        pm_rows.append({"aita_player_id": pid, "full_name": name, "position": pos, "current_team": team, "role_certainty_score": 90.0, "data_freshness_score": 100.0, "critical_current_state_ok": True, "roster_verified_current": True, "roster_gate_reason": "DEMO_CURRENT_ROSTER", "depth_rank": 1, "primary_scorer_eligible": True, "sharp_board_eligible": True, "external_consensus_status": "DEMO", "external_consensus_multiplier": 1.0, "available_for_simulation": True})
    player_map = pd.DataFrame(pm_rows)
    state = {"slate": slate, "player_map": player_map, "scorer_sim_summary": pd.DataFrame(summary), "scorer_state": pd.DataFrame(summary),
             "team_state": pd.DataFrame(), "espn_team_leaders": pd.DataFrame(), "fantasy_context": pd.DataFrame(), "fftoday": pd.DataFrame(), "fantasypros": pd.DataFrame(), "pfr_fantasy": pd.DataFrame(), "external_fantasy_context": pd.DataFrame(), "defense_td_state": pd.DataFrame(), "td_style_state": pd.DataFrame(), "qb_goal_line_state": pd.DataFrame(), "provider_health": {"demo": "OK"}, "scorer_reconciliation": [{"aita_event_id": eid, "team": "DEMO", "status": "OK"}]}
    market_rows = []
    prices = {"P1": 135, "P2": 190, "P3": 260, "P4": 220}
    for pid, name, pos, team, p in players:
        market_rows.append({"aita_event_id": eid, "odds_api_event_id": "DEMO-ODDS", "aita_player_id": pid, "player_name": name, "player_name_raw": name, "position": pos, "team": team,
                            "bookmaker": "demo_book", "market_key": "player_anytime_td", "side": "YES", "line": .5, "american_odds": prices[pid],
                            "market_raw_implied_prob": american_to_implied(float(prices[pid])), "snapshot_time_utc": utc_now_iso(), "entity_status": "RESOLVED"})
    odds = pd.DataFrame(market_rows)
    priced = price_anytime_td_rows(odds, draws, player_map, ev_floor=float(cfg.get("scoring", "straight_ev_floor", default=.06)), market_trust=0.0, week=week, max_market_age_minutes=999999)
    return build_scorer_handoff(cfg, season, week, run_id, state, draws, priced, pd.DataFrame(), None, {"mode":"OFFLINE_DEMO", "paid_credits_used":0}, {"mode":"OFFLINE_DEMO"})
