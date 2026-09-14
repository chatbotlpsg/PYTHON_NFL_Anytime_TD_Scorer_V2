from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from nfl_model.config import load_config
from nfl_model.package.handoff import deterministic_zip
from nfl_model.boards.forecast import build_full_forecast_boards, write_layer1_forecast_snapshot
from nfl_model.pipeline import ingest_football, make_run_id, run_demo, run_live, simulate_slate
from nfl_model.providers.odds_api.client import OddsAPIClient
from nfl_model.providers.odds_api.normalize import normalize_event_odds
from nfl_model.providers.odds_api.quota import estimate_plan
from nfl_model.utils import utc_now_iso

APPROVED_V1 = {
    "player_receptions", "player_rush_attempts", "player_pass_attempts", "player_pass_completions",
    "player_reception_yds", "player_rush_yds", "player_pass_yds",
}


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nfl-model", description="AITA NFL opportunity-first player alpha pipeline")
    p.add_argument("--root", default=".", help="NFL_MODEL repository root")
    sub = p.add_subparsers(dest="command", required=True)

    def sw(name: str):
        x = sub.add_parser(name)
        x.add_argument("--season", type=int, default=2026)
        x.add_argument("--week", type=int, required=True)
        return x

    sw("validate-config")
    op = sw("odds-plan")
    op.add_argument("--events", type=int, default=16)
    op.add_argument("--shortlist-events", type=int, default=6)
    op.add_argument("--reprice-market-families", type=int, default=2)
    demo = sw("demo")
    demo.add_argument("--draws", type=int, default=25000)
    run = sw("run")
    run.add_argument("--mode", choices=["production", "development"], default="production")
    run.add_argument("--draws", type=int)
    run.add_argument("--shortlist-events", type=int, default=6)
    run.add_argument("--aita-event-id", action="append", help="Restrict production run to one or more AITA event IDs")
    run.add_argument("--slate-label", help="Short label embedded in the immutable run id, e.g. WED_KICKOFF or SUN_DAY")
    sw("ingest-football")
    sim = sw("simulate")
    sim.add_argument("--draws", type=int, default=50000)

    fm = sw("fetch-mainlines")
    fm.add_argument("--force-refresh", action="store_true")
    fo = sw("fetch-opportunity-odds")
    fo.add_argument("--event-id", action="append", required=True)
    fo.add_argument("--force-refresh", action="store_true")
    fy = sw("fetch-shortlist-yardage")
    fy.add_argument("--event-id", action="append", required=True)
    fy.add_argument("--force-refresh", action="store_true")
    rp = sw("reprice")
    rp.add_argument("--event-id", required=True)
    rp.add_argument("--market", action="append", required=True)

    au = sw("audit")
    au.add_argument("--run-dir", required=True)
    pkg = sw("package")
    pkg.add_argument("--run-dir", required=True)
    pkg.add_argument("--output", required=True)
    return p


def _odds_client(cfg):
    load_dotenv(cfg.root / ".env")
    odds_cfg = cfg.get("odds")
    return OddsAPIClient(
        cfg.get("providers", "odds_base"), cfg.root / cfg.get("storage", "cache_dir") / "odds_api",
        cfg.root / cfg.get("storage", "raw_dir") / "odds_api" / "quota_ledger.jsonl",
        list(odds_cfg["bookmakers"]), int(odds_cfg["monthly_credit_reserve"]), int(odds_cfg["cache_ttl_minutes"]),
        int(odds_cfg["timeout_seconds"]), int(odds_cfg["max_retries"]),
    )


def _write_manual_odds(cfg, season, week, label, payload):
    path = cfg.root / cfg.get("storage", "raw_dir") / "odds_api" / str(season) / f"week_{week:02d}"
    path.mkdir(parents=True, exist_ok=True)
    out = path / f"{label}_{utc_now_iso().replace(':','')}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    cfg = load_config(args.root)
    cmd = args.command

    if cmd == "validate-config":
        markets = set(cfg.markets.get("markets", {}).keys())
        illegal = markets - APPROVED_V1
        if illegal:
            raise SystemExit(f"INVALID_V1_SCOPE: {sorted(illegal)}")
        if set(cfg.get("odds", "opportunity_markets")) != {"player_receptions", "player_rush_attempts", "player_pass_attempts", "player_pass_completions"}:
            raise SystemExit("INVALID_OPPORTUNITY_MARKET_SET")
        print(f"STATUS: OK\nMODEL_VERSION: {cfg.get('project','model_version')}\nCONFIG_HASH: {cfg.config_hash}")
        return 0

    if cmd == "odds-plan":
        o = cfg.get("odds")
        plan = estimate_plan(args.events, len(o["opportunity_markets"]), len(o["production_markets"]), args.shortlist_events,
                             args.reprice_market_families, list(o["bookmakers"]))
        print(f"Events: {plan.events}")
        print(f"Opportunity markets: {len(o['opportunity_markets'])}")
        print(f"Bookmakers: {','.join(o['bookmakers'])}")
        print(f"\nExpected max opportunity cost: {plan.opportunity_cost} credits")
        print(f"Mainline cost: {plan.mainline_cost} credits")
        print(f"Secondary shortlisted allowance: {plan.production_cost} credits")
        print(f"Reprice allowance: {plan.reprice_cost} credits")
        print(f"\nPlanned max: {plan.planned_max}")
        print(f"Safety reserve: {o['monthly_credit_reserve']}")
        print("STATUS: PLAN_READY (live remaining credits are checked before paid calls)")
        return 0

    if cmd == "demo":
        art = run_demo(cfg, args.season, args.week, args.draws)
        print(f"RUN_ID={art.run_id}\nHANDOFF_ZIP={art.handoff_zip}")
        return 0

    if cmd == "run":
        default_draws = cfg.get("simulation", "production_draws" if args.mode == "production" else "development_draws")
        art = run_live(
            cfg, args.season, args.week, args.draws or int(default_draws), args.shortlist_events,
            selected_aita_event_ids=args.aita_event_id, slate_label=args.slate_label,
        )
        print(f"RUN_ID={art.run_id}\nHANDOFF_ZIP={art.handoff_zip}")
        return 0

    if cmd == "ingest-football":
        state = ingest_football(cfg, args.season, args.week)
        print(f"SLATE_ROWS={len(state['slate'])}\nPLAYER_MAP_ROWS={len(state['player_map'])}\nNORMALIZED_DIR={state['normalized_dir']}")
        return 0

    if cmd == "simulate":
        state = ingest_football(cfg, args.season, args.week)
        draws, summary, recon = simulate_slate(cfg, args.season, args.week, state, args.draws)
        out = cfg.root / cfg.get("storage", "features_dir") / str(args.season) / f"week_{args.week:02d}"
        out.mkdir(parents=True, exist_ok=True)
        summary.to_parquet(out / "simulation_summary.parquet", index=False)
        (out / "simulation_reconciliation.json").write_text(json.dumps(recon, indent=2), encoding="utf-8")
        snapshot_id = make_run_id(args.season, args.week) + "-LAYER1"
        snapshot_time = utc_now_iso()
        forecast_boards = build_full_forecast_boards(
            draws, summary, state["slate"], state["player_map"], snapshot_id, snapshot_time
        )
        paths = write_layer1_forecast_snapshot(
            forecast_boards, out, args.season, args.week, snapshot_id
        )
        print(
            f"DRAWS={args.draws}\nSERIES={len(draws)}\nOUT={out}\n"
            f"FORECAST_SNAPSHOT_ID={snapshot_id}\n"
            f"RECEIVING_BOARD_ROWS={len(forecast_boards['receiving'])}\n"
            f"RUSHING_BOARD_ROWS={len(forecast_boards['rushing'])}\n"
            f"PASSING_BOARD_ROWS={len(forecast_boards['passing'])}\n"
            f"FORECAST_SNAPSHOT_DIR={paths['all'].parent}"
        )
        return 0

    if cmd in {"fetch-mainlines", "fetch-opportunity-odds", "fetch-shortlist-yardage", "reprice"}:
        client = _odds_client(cfg)
        o = cfg.get("odds")
        if cmd == "fetch-mainlines":
            payload = client.mainlines(o["sport_key"], list(o["mainlines"]), args.force_refresh)
            out = _write_manual_odds(cfg, args.season, args.week, "mainlines", payload)
        elif cmd == "fetch-opportunity-odds":
            payload = {eid: client.event_odds(o["sport_key"], eid, list(o["opportunity_markets"]), args.force_refresh) for eid in args.event_id}
            out = _write_manual_odds(cfg, args.season, args.week, "opportunity", payload)
        elif cmd == "fetch-shortlist-yardage":
            payload = {eid: client.event_odds(o["sport_key"], eid, list(o["production_markets"]), args.force_refresh) for eid in args.event_id}
            out = _write_manual_odds(cfg, args.season, args.week, "production", payload)
        else:
            illegal = set(args.market) - APPROVED_V1
            if illegal: raise SystemExit(f"INVALID_V1_SCOPE: {sorted(illegal)}")
            payload = client.event_odds(o["sport_key"], args.event_id, args.market, True)
            out = _write_manual_odds(cfg, args.season, args.week, "reprice", payload)
        print(f"OUT={out}\nCREDITS_REMAINING={client.last_remaining}")
        return 0

    if cmd == "audit":
        run_dir = Path(args.run_dir)
        required = ["README.md", f"NFL_RUN_MANIFEST_{args.season}-W{args.week:02d}.json", f"NFL_MARKET_SNAPSHOT_{args.season}-W{args.week:02d}.csv"]
        missing = [x for x in required if not (run_dir / x).exists()]
        forbidden = [x for x in ["CLV.csv", "closing_lines.csv", "trade_grades.csv", "actual_entries.csv"] if (run_dir / x).exists()]
        status = "OK" if not missing and not forbidden else "FAIL"
        print(json.dumps({"status": status, "missing": missing, "forbidden_post_handoff_artifacts": forbidden}, indent=2))
        return 0 if status == "OK" else 2

    if cmd == "package":
        path = deterministic_zip(Path(args.run_dir), Path(args.output))
        print(f"ZIP={path}")
        return 0

    raise SystemExit(f"Unknown command: {cmd}")
