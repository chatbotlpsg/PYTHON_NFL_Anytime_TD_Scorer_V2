from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZipFile

from nfl_model.config import load_config
from nfl_model.scorer_pipeline import run_scorer_live, run_scorer_demo


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nfl-scorer", description="AITA NFL market-blind TD scorer probability + EV pipeline")
    p.add_argument("--root", default=".", help="Repository root")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate-config")
    v.add_argument("--season", type=int, default=2026)
    v.add_argument("--week", type=int, required=True)

    d = sub.add_parser("demo")
    d.add_argument("--season", type=int, default=2026)
    d.add_argument("--week", type=int, required=True)
    d.add_argument("--draws", type=int, default=50000)

    r = sub.add_parser("run")
    r.add_argument("--season", type=int, default=2026)
    r.add_argument("--week", type=int, required=True)
    r.add_argument("--draws", type=int)
    r.add_argument("--slate-date", help="NFL calendar date YYYY-MM-DD; filters the weekly ESPN slate before simulation")
    r.add_argument("--aita-event-id", action="append", help="Optional repeatable AITA event-id filter")
    r.add_argument("--slate-label", help="Optional immutable run label, e.g. SUN_0913")
    r.add_argument("--starter-override", action="append", help="Repeatable game-day starter override TEAM:POS:PLAYER, e.g. CHI:QB:Case Keenum")
    r.add_argument("--inactive-player", action="append", help="Repeatable game-day inactive override TEAM:PLAYER, e.g. CHI:Caleb Williams")

    a = sub.add_parser("audit-handoff")
    a.add_argument("--zip", required=True)
    return p


def _audit_zip(path: Path) -> dict:
    required_fragments = [
        "NFL_SCORER_QB_SLATE_PROBABILITY_BOARD_", "NFL_SCORER_RB_SLATE_PROBABILITY_BOARD_",
        "NFL_SCORER_WR_SLATE_PROBABILITY_BOARD_", "NFL_SCORER_TE_SLATE_PROBABILITY_BOARD_",
        "NFL_SCORER_MATCHUP_PROBABILITY_BOARD_", "NFL_SCORER_SLATE_PROBABILITY_BOARD_",
        "NFL_SCORER_CURRENT_ROSTER_VALIDATION_BOARD_", "NFL_SCORER_CURRENT_SEASON_TEAM_OFFENSE_",
        "NFL_SCORER_CURRENT_SEASON_PLAYER_TD_FORM_", "NFL_SCORER_ESPN_TOP_STATS_BOARD_",
        "NFL_SCORER_FANTASY_CONTEXT_BOARD_", "NFL_SCORER_FFTODAY_WEEKLY_PROJECTIONS_",
        "NFL_SCORER_FANTASYPROS_WEEKLY_RANKINGS_", "NFL_SCORER_PFR_CURRENT_FANTASY_ACTUALS_",
        "NFL_SCORER_EXTERNAL_FANTASY_CONSENSUS_BOARD_", "NFL_SCORER_DEFENSIVE_TD_VULNERABILITY_BOARD_",
        "NFL_SCORER_PLAYER_TD_STYLE_BOARD_", "NFL_SCORER_QB_GOAL_LINE_COMPETITION_BOARD_",
        "NFL_SCORER_MARKET_SNAPSHOT_", "NFL_SCORER_EV_PLAY_BOARD_", "NFL_SCORER_EDGE_LEADERBOARD_",
        "NFL_SCORER_JOINT_PAIR_BOARD_", "NFL_SCORER_JOINT_TRIPLE_BOARD_", "NFL_SCORER_PARLAY_MATH_CANDIDATE_BOARD_",
        "NFL_SCORER_MATCHUP_EV_PLAY_BOARD_", "NFL_SCORER_SLATE_EV_PLAY_BOARD_", "NFL_SCORER_RUN_MANIFEST_",
        "NFL_SCORER_PROVIDER_HEALTH_", "TRADING_AGENT_PARLAY_PROTOCOL.md", "NFL_SCORER_TRADING_AGENT_USER_INPUT_PROMPT_V1.md", "README.md",
    ]
    forbidden = ["closing_lines", "CLV", "trade_grades", "actual_entries"]
    with ZipFile(path, "r") as zf:
        names = zf.namelist()
    missing = [frag for frag in required_fragments if not any(frag in n for n in names)]
    bad = [n for n in names if any(x.lower() in n.lower() for x in forbidden)]
    return {"status": "OK" if not missing and not bad else "FAIL", "missing": missing, "forbidden": bad, "files": len(names)}


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    cfg = load_config(args.root)
    if args.command == "validate-config":
        scoring = cfg.get("scoring")
        required = ["straight_ev_floor", "market_trust", "other_touchdown_share", "joint_pair_top_n", "joint_triple_top_n"]
        missing = [x for x in required if x not in scoring]
        external = cfg.get("external_fantasy", default={}) or {}
        external_required = ["enabled", "weights", "multiplier_min", "multiplier_max", "minimum_sources_for_rejection"]
        external_missing = [x for x in external_required if x not in external]
        current_scoring = cfg.get("current_season_scoring", default={}) or {}
        current_required = ["enabled", "player_prior_games", "player_multiplier_min", "player_multiplier_max", "team_multiplier_min", "team_multiplier_max", "suppression_team_percentile", "minimum_games_for_suppression"]
        current_missing = [x for x in current_required if x not in current_scoring]
        status = "OK" if not missing and not external_missing and not current_missing else "FAIL"
        print(json.dumps({"status": status, "model_version": cfg.get("project", "model_version"), "scoring_missing": missing, "external_fantasy_missing": external_missing, "current_season_scoring_missing": current_missing}, indent=2))
        return 0 if status == "OK" else 1
    if args.command == "demo":
        art = run_scorer_demo(cfg, args.season, args.week, args.draws)
        print(f"RUN_ID={art.run_id}\nHANDOFF_ZIP={art.handoff_zip}")
        return 0
    if args.command == "run":
        art = run_scorer_live(cfg, args.season, args.week, args.draws, args.slate_date, args.aita_event_id, args.slate_label, args.starter_override, args.inactive_player)
        print(f"RUN_ID={art.run_id}\nHANDOFF_ZIP={art.handoff_zip}")
        return 0
    if args.command == "audit-handoff":
        report = _audit_zip(Path(args.zip))
        print(json.dumps(report, indent=2))
        return 0 if report["status"] == "OK" else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
