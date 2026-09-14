from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from nfl_model import __version__
from nfl_model.audit.validation import assert_simulation_reconciliation, validate_player_map, validate_slate
from nfl_model.boards.builder import build_boards
from nfl_model.boards.forecast import build_full_forecast_boards, build_market_lined_pick_boards
from nfl_model.config import AppConfig
from nfl_model.features.team import build_team_state
from nfl_model.features.current_role import enrich_player_map_with_current_context, bootstrap_missing_role_states
from nfl_model.features.coaching import build_coaching_state
from nfl_model.features.matchup import build_matchup_state
from nfl_model.features.qb import build_qb_state
from nfl_model.features.rb import build_rb_state
from nfl_model.features.receivers import build_receiver_state
from nfl_model.features.scoring import build_scorer_state, build_team_td_state, bootstrap_missing_scorer_state
from nfl_model.ids.teams import canonical_team, team_from_full_name
from nfl_model.ids.resolver import build_player_map
from nfl_model.normalize.market import add_novig_probabilities, attach_player_ids
from nfl_model.package.handoff import boundary_manifest, deterministic_zip, write_handoff_readme
from nfl_model.portfolio.correlation import correlation_matrix
from nfl_model.pricing.engine import price_prop_rows, MARKET_TO_STAT
from nfl_model.providers.espn.client import ESPNClient
from nfl_model.providers.espn.normalize import normalize_depth_chart, normalize_injuries, normalize_roster, normalize_scoreboard
from nfl_model.providers.nflverse.client import NFLVerseClient
from nfl_model.providers.nws.client import NWSClient
from nfl_model.providers.odds_api.client import OddsAPIClient
from nfl_model.providers.odds_api.normalize import normalize_event_odds
from nfl_model.providers.odds_api.quota import estimate_plan
from nfl_model.simulation.monte_carlo import SimulationResult, simulate_team
from nfl_model.simulation.scoring import simulate_scorers
from nfl_model.simulation.game_state import simulate_game
from nfl_model.simulation.convergence import probability_convergence
from nfl_model.storage.snapshots import save_json_snapshot
from nfl_model.utils import normalize_name, sha256_file, utc_now_iso


@dataclass
class PipelineArtifacts:
    run_id: str
    run_dir: Path
    handoff_zip: Path


def make_run_id(season: int, week: int) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"NFL-{season}-W{week:02d}-{stamp}"


def _git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "UNAVAILABLE"


def _role_certainty(games: int, week: int, position: str) -> float:
    base = min(96.0, 58.0 + games * 3.1)
    if week == 1:
        base -= 7.0
    if position in {"RB", "WR", "TE"}:
        base -= 2.0
    return float(max(35.0, min(96.0, base)))


def _augment_player_map(qb: pd.DataFrame, rb: pd.DataFrame, rec: pd.DataFrame, season: int, week: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for frame in [qb, rb, rec]:
        if frame.empty:
            continue
        for _, r in frame.iterrows():
            pos = str(r.get("position", ""))
            games = int(r.get("games_observed", 0) or 0)
            rows.append({
                "player_id": str(r.get("gsis_id", "")),
                "gsis_id": str(r.get("gsis_id", "")),
                "full_name": r.get("player_name"),
                "position": pos,
                "current_team": canonical_team(str(r.get("team", ""))),
                "role_certainty_score": _role_certainty(games, week, pos),
                "model_agreement_score": float(max(55.0, min(93.0, 65.0 + games * 2.0))),
                "data_freshness_score": 90.0 if week == 1 else 95.0,
                "season": season,
                "week": week,
            })
    pm = build_player_map(rows)
    if not pm.empty:
        aux = pd.DataFrame(rows)
        aux["normalized_name"] = aux["full_name"].fillna("").map(normalize_name)
        keep = ["normalized_name", "current_team", "role_certainty_score", "model_agreement_score", "data_freshness_score"]
        aux = aux[keep].drop_duplicates(["normalized_name", "current_team"], keep="last")
        pm = pm.merge(aux, on=["normalized_name", "current_team"], how="left")
    return pm


def _merge_espn_ids(player_map: pd.DataFrame, rosters: pd.DataFrame) -> pd.DataFrame:
    if player_map.empty or rosters.empty:
        return player_map
    p = player_map.copy()
    r = rosters.copy()
    r["normalized_name"] = r["full_name"].fillna("").map(normalize_name)
    for _, rr in r.iterrows():
        q = p[
            p["normalized_name"].eq(rr["normalized_name"]) &
            p["current_team"].eq(canonical_team(str(rr["current_team"]))) &
            p["position"].fillna("").eq(str(rr.get("position") or ""))
        ]
        if len(q) == 1:
            p.loc[q.index, "espn_athlete_id"] = rr.get("espn_athlete_id")
    return p


def _player_states_with_ids(frame: pd.DataFrame, player_map: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    out = frame.copy()
    out["normalized_name"] = out["player_name"].fillna("").map(normalize_name)
    cols = ["aita_player_id", "normalized_name", "current_team", "position"]
    pm = player_map[cols].copy()
    out["team"] = out["team"].fillna("").map(canonical_team)
    out = out.merge(pm, left_on=["normalized_name", "team", "position"], right_on=["normalized_name", "current_team", "position"], how="left")
    return out.drop(columns=["current_team"], errors="ignore")


def ingest_football(cfg: AppConfig, season: int, week: int) -> dict[str, Any]:
    raw_dir = cfg.root / cfg.get("storage", "raw_dir")
    normalized_dir = cfg.root / cfg.get("storage", "normalized_dir") / str(season) / f"week_{week:02d}"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    health: dict[str, Any] = {}

    espn = ESPNClient(cfg.get("providers", "espn_base"), timeout=int(cfg.get("providers", "request_timeout_seconds", default=20)))
    scoreboard = espn.get_weekly_slate(season, week)
    snap = save_json_snapshot(raw_dir, "espn", season, week, "scoreboard", scoreboard)
    slate = normalize_scoreboard(scoreboard, season, week)
    errors = validate_slate(slate)
    if errors:
        raise RuntimeError(f"EVENT_GATE_FAILED: {errors}")
    slate.to_csv(normalized_dir / "fact_schedule.csv", index=False)
    # Canonical entity maps are persisted independently of downstream feature tables.
    team_rows = []
    for _, g in slate.iterrows():
        for side in ("home", "away"):
            abbr = str(g[f"{side}_team"])
            team_rows.append({
                "aita_team_id": f"NFL-TEAM-{abbr}",
                "team_abbr": abbr,
                "team_name": abbr,
                "espn_team_id": str(g[f"{side}_espn_team_id"]),
                "nflverse_team_abbr": abbr,
                "odds_api_team_name": None,
            })
    pd.DataFrame(team_rows).drop_duplicates("aita_team_id").to_csv(normalized_dir / "entity_map_team.csv", index=False)
    slate[["aita_event_id", "season", "week", "kickoff_utc", "home_team", "away_team", "espn_event_id"]].assign(odds_api_event_id=None).to_csv(
        normalized_dir / "entity_map_event.csv", index=False
    )
    health["espn_scoreboard"] = "OK"

    roster_frames, depth_frames = [], []

    team_pairs: dict[str, str] = {}

    for _, game in slate.iterrows():
        team_pairs[
            game["home_team"]
        ] = str(
            game["home_espn_team_id"]
        )

        team_pairs[
            game["away_team"]
        ] = str(
            game["away_espn_team_id"]
        )

    team_id_to_abbr = {
        team_id: team
        for team, team_id
        in team_pairs.items()
    }

    # --------------------------------------------------------
    # CURRENT ROSTERS + DEPTH CHARTS
    #
    # These calls are independent.
    #
    # A roster failure must NOT suppress a healthy depth-chart
    # call for the same team.
    # --------------------------------------------------------

    for team, team_id in sorted(
        team_pairs.items()
    ):

        try:
            rj = espn.get_roster(
                team_id
            )

            save_json_snapshot(
                raw_dir,
                "espn",
                season,
                week,
                f"roster_{team}",
                rj,
            )

            roster_frames.append(
                normalize_roster(
                    rj,
                    team,
                )
            )

            health[
                f"espn_{team}_roster"
            ] = "OK"

        except Exception as exc:

            health[
                f"espn_{team}_roster"
            ] = (
                f"DEGRADED:"
                f"{type(exc).__name__}"
            )

        try:
            dj = espn.get_depth_chart(
                team_id
            )

            save_json_snapshot(
                raw_dir,
                "espn",
                season,
                week,
                f"depthchart_{team}",
                dj,
            )

            depth_frames.append(
                normalize_depth_chart(
                    dj,
                    team,
                )
            )

            health[
                f"espn_{team}_depthchart"
            ] = "OK"

        except Exception as exc:

            health[
                f"espn_{team}_depthchart"
            ] = (
                f"DEGRADED:"
                f"{type(exc).__name__}"
            )

    # --------------------------------------------------------
    # CURRENT INJURIES
    #
    # ESPN team-specific injury endpoints are currently
    # returning empty objects.
    #
    # The league-wide endpoint contains the real 2026
    # injury state, grouped by ESPN team ID.
    #
    # Fetch ONCE and normalize by canonical team.
    # --------------------------------------------------------

    injuries = pd.DataFrame()

    try:
        league_injuries_json = (
            espn.get_injuries()
        )

        save_json_snapshot(
            raw_dir,
            "espn",
            season,
            week,
            "injuries_league",
            league_injuries_json,
        )

        injuries = normalize_injuries(
            league_injuries_json,
            team_id_to_abbr=(
                team_id_to_abbr
            ),
        )

        # Provider health reflects successful retrieval and
        # schema normalization, NOT whether zero players happen
        # to be injured.
        health[
            "espn_injuries"
        ] = "OK"

    except Exception as exc:

        health[
            "espn_injuries"
        ] = (
            f"DEGRADED:"
            f"{type(exc).__name__}"
        )

    rosters = (
        pd.concat(
            roster_frames,
            ignore_index=True,
        )
        if roster_frames
        else pd.DataFrame(
            columns=[
                "espn_athlete_id",
                "full_name",
                "position",
                "current_team",
                "jersey",
                "active_flag",
            ]
        )
    )

    depths = (
        pd.concat(
            depth_frames,
            ignore_index=True,
        )
        if depth_frames
        else pd.DataFrame(
            columns=[
                "team",
                "unit",
                "position",
                "rank",
                "espn_athlete_id",
                "player_name",
            ]
        )
    )

    if (
        injuries.empty
        and len(injuries.columns) == 0
    ):
        injuries = pd.DataFrame(
            columns=[
                "team",
                "espn_team_id",
                "injury_id",
                "espn_athlete_id",
                "player_name",
                "status",
                "date",
                "details",
            ]
        )

    rosters.to_csv(
        normalized_dir
        / "fact_roster_snapshot.csv",
        index=False,
    )

    depths.to_csv(
        normalized_dir
        / "fact_depth_chart_snapshot.csv",
        index=False,
    )

    injuries.to_csv(
        normalized_dir
        / "fact_injury_snapshot.csv",
        index=False,
    )

    health[
        "espn_rosters"
    ] = (
        "OK"
        if not rosters.empty
        else "DEGRADED"
    )

    health[
        "espn_depthcharts"
    ] = (
        "OK"
        if not depths.empty
        else "DEGRADED"
    )

    transactions = pd.DataFrame()
    try:
        tj = espn.get_transactions()
        save_json_snapshot(raw_dir, "espn", season, week, "transactions", tj)
        # Keep raw payload as the source of truth; normalized transaction schema is provider-dependent.
        transactions = pd.DataFrame(tj.get("transactions", [])) if isinstance(tj, dict) else pd.DataFrame()
        transactions.to_csv(normalized_dir / "fact_transaction_snapshot.csv", index=False)
        health["espn_transactions"] = "OK"
    except Exception as exc:
        health["espn_transactions"] = f"DEGRADED:{type(exc).__name__}"
        pd.DataFrame().to_csv(normalized_dir / "fact_transaction_snapshot.csv", index=False)

    seasons = [int(s) for s in cfg.get("history", "seasons")]
    nflv = NFLVerseClient(cfg.root / cfg.get("storage", "cache_dir") / "nflverse")
    pbp = nflv.load_pbp(seasons).to_pandas()
    player_stats = nflv.load_player_stats(seasons).to_pandas()
    snap_counts = nflv.load_snap_counts(seasons).to_pandas()
    # Cache the remaining historical backbone tables required by the architecture even when
    # a particular V1 feature does not yet consume every field directly.
    historical_health = {}
    for name, loader in [
        ("team_stats", nflv.load_team_stats),
        ("schedules", nflv.load_schedules),
        ("rosters_weekly", nflv.load_rosters_weekly),
        ("participation", nflv.load_participation),
        ("injuries", nflv.load_injuries),
        ("depth_charts", nflv.load_depth_charts),
    ]:
        try:
            loader(seasons)
            historical_health[f"nflverse_{name}"] = "OK"
        except Exception as exc:
            historical_health[f"nflverse_{name}"] = f"DEGRADED:{type(exc).__name__}"
    health.update(historical_health)
    team_state = build_team_state(pbp, float(cfg.get("history", "ewm_halflife_weeks", default=6.0)))
    qb_state = build_qb_state(player_stats, snap_counts)
    rb_state = build_rb_state(player_stats)
    rec_state = build_receiver_state(player_stats, snap_counts)
    scorer_state = build_scorer_state(player_stats)
    team_td_state = build_team_td_state(player_stats)
    player_map = _augment_player_map(qb_state, rb_state, rec_state, season, week)
    player_map = _merge_espn_ids(player_map, rosters)
    player_map = enrich_player_map_with_current_context(player_map, rosters, depths, injuries)
    degraded_current_state_teams = {
        team
        for team in team_pairs
        if any(
            str(
                health.get(
                    f"espn_{team}_{component}",
                    "OK",
                )
            ).startswith("DEGRADED")
            for component in (
                "roster",
                "depthchart",
            )
        )
    }

    # A failed league-wide injury snapshot is critical for
    # all player-prop teams because availability cannot be
    # verified.
    if str(
        health.get(
            "espn_injuries",
            "OK",
        )
    ).startswith("DEGRADED"):

        degraded_current_state_teams.update(
            team_pairs.keys()
        )
    if not player_map.empty:
        player_map["critical_current_state_ok"] = ~player_map["current_team"].isin(degraded_current_state_teams)
        player_map.loc[~player_map["critical_current_state_ok"], "data_freshness_score"] = 0.0
    pm_errors = validate_player_map(player_map)
    if pm_errors:
        raise RuntimeError(f"PLAYER_GATE_FAILED: {pm_errors}")
    qb_state = _player_states_with_ids(qb_state, player_map)
    rb_state = _player_states_with_ids(rb_state, player_map)
    rec_state = _player_states_with_ids(rec_state, player_map)
    scorer_state = _player_states_with_ids(scorer_state, player_map)
    qb_state, rb_state, rec_state = bootstrap_missing_role_states(player_map, qb_state, rb_state, rec_state)
    scorer_state = bootstrap_missing_scorer_state(player_map, scorer_state)
    coaching_state = build_coaching_state(team_state)
    matchup_state = build_matchup_state(slate, team_state)

    team_state.to_csv(normalized_dir / "team_state.csv", index=False)
    qb_state.to_csv(normalized_dir / "qb_state.csv", index=False)
    rb_state.to_csv(normalized_dir / "rb_state.csv", index=False)
    rec_state.to_csv(normalized_dir / "receiver_state.csv", index=False)
    scorer_state.to_csv(normalized_dir / "scorer_state.csv", index=False)
    team_td_state.to_csv(normalized_dir / "team_td_state.csv", index=False)
    coaching_state.to_csv(normalized_dir / "coaching_state.csv", index=False)
    matchup_state.to_csv(normalized_dir / "matchup_state.csv", index=False)
    player_map.to_csv(normalized_dir / "entity_map_player.csv", index=False)
    health["nflverse_pbp"] = "OK"
    health["nflverse_snap_counts"] = "OK"

    # Weather only for OUTDOOR sites; domes/covered roofs are explicitly zero-impact.
    weather_rows = []
    nws = NWSClient(cfg.get("providers", "nws_base"), timeout=int(cfg.get("providers", "request_timeout_seconds", default=20)))
    stadiums = cfg.stadiums.get("stadiums", {})
    for _, game in slate.iterrows():
        st = stadiums.get(game["home_team"], {})
        roof = str(st.get("roof_type", "UNKNOWN"))
        row = {"aita_event_id": game["aita_event_id"], "home_team": game["home_team"], "roof_type": roof,
               "temperature": None, "wind_speed": None, "wind_direction": None, "precipitation_probability": None,
               "weather_status": "ZERO_IMPACT_DOME_OR_COVERED" if roof in {"DOME", "COVERED"} else "ROOF_STATUS_REVIEW"}
        if roof == "OUTDOOR" and st.get("lat") is not None:
            try:
                hourly = nws.hourly(float(st["lat"]), float(st["lon"]))
                save_json_snapshot(raw_dir, "nws", season, week, f"weather_{game['home_team']}", hourly)
                p = nws.nearest_period(hourly, game["kickoff_utc"])
                row.update({
                    "temperature": p.get("temperature"), "wind_speed": p.get("windSpeed"),
                    "wind_direction": p.get("windDirection"),
                    "precipitation_probability": (p.get("probabilityOfPrecipitation") or {}).get("value"),
                    "weather_status": "OK",
                })
            except Exception as exc:
                row["weather_status"] = f"DEGRADED:{type(exc).__name__}"
        weather_rows.append(row)
    weather = pd.DataFrame(weather_rows)
    weather.to_csv(normalized_dir / "fact_weather_snapshot.csv", index=False)
    health["nws_weather"] = "OK" if not weather.empty else "DEGRADED"

    return {
        "slate": slate, "rosters": rosters, "depths": depths, "injuries": injuries, "transactions": transactions,
        "team_state": team_state, "qb_state": qb_state, "rb_state": rb_state, "rec_state": rec_state, "scorer_state": scorer_state, "team_td_state": team_td_state,
        "coaching_state": coaching_state, "matchup_state": matchup_state,
        "player_map": player_map, "weather": weather, "provider_health": health,
        "normalized_dir": normalized_dir, "scoreboard_snapshot": snap,
    }



def _weather_effects_for_event(weather: pd.DataFrame, event_id: str) -> dict[str, float]:
    """Convert NWS snapshot into bounded football effects; wind dominates generic weather narratives."""
    if weather is None or weather.empty:
        return {}
    g = weather[weather["aita_event_id"].astype(str).eq(str(event_id))]
    if g.empty:
        return {}
    row = g.iloc[-1]
    status = str(row.get("weather_status") or "")
    roof = str(row.get("roof_type") or "UNKNOWN")
    if roof in {"DOME", "COVERED"} or status.startswith("ZERO_IMPACT"):
        return {"pass_rate_shift": 0.0, "completion_multiplier": 1.0, "deep_yardage_multiplier": 1.0, "scoring_multiplier": 1.0}
    wind_text = str(row.get("wind_speed") or "")
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", wind_text)]
    wind = max(nums) if nums else 0.0
    precip = row.get("precipitation_probability")
    try:
        precip = float(precip) if precip is not None and not pd.isna(precip) else 0.0
    except (TypeError, ValueError):
        precip = 0.0
    # Below ~12 mph the model intentionally does almost nothing. Wind effects become material in the high teens/20s.
    wind_severity = float(np.clip((wind - 12.0) / 18.0, 0.0, 1.0))
    rain_severity = float(np.clip((precip - 45.0) / 55.0, 0.0, 1.0))
    return {
        "wind_mph": wind,
        "precip_probability": precip,
        "pass_rate_shift": -0.018 * wind_severity - 0.006 * rain_severity,
        "completion_multiplier": 1.0 - 0.045 * wind_severity - 0.018 * rain_severity,
        "deep_yardage_multiplier": 1.0 - 0.12 * wind_severity - 0.035 * rain_severity,
        "scoring_multiplier": 1.0 - 0.055 * wind_severity - 0.018 * rain_severity,
    }

def simulate_slate(cfg: AppConfig, season: int, week: int, state: dict[str, Any], draws_n: int,
                   game_anchors: dict[str, dict[str, float]] | None = None) -> tuple[dict[str, np.ndarray], pd.DataFrame, list[dict]]:
    slate = state["slate"]
    team_state = state["team_state"].set_index("team") if not state["team_state"].empty else pd.DataFrame()
    qbs, rbs, recs = state["qb_state"], state["rb_state"], state["rec_state"]
    game_anchors = game_anchors or {}
    pm = state.get("player_map", pd.DataFrame())
    unavailable = set()
    if not pm.empty and "available_for_simulation" in pm.columns:
        unavailable = set(pm.loc[~pm["available_for_simulation"].fillna(True).astype(bool), "aita_player_id"].dropna().astype(str))
    all_draws: dict[str, np.ndarray] = {}
    summaries: list[pd.DataFrame] = []
    reconciliations = []
    game_summaries = []
    base_seed = int(cfg.get("project", "random_seed", default=260901))
    week1_mult = float(cfg.get("uncertainty", "week1_multiplier", default=1.0)) if week == 1 else 1.0
    market_weight = float(cfg.get("pricing", "mainline_anchor_weight", default=0.62))

    def team_dict(team: str) -> dict:
        if isinstance(team_state, pd.DataFrame) and team in team_state.index:
            r = team_state.loc[team]
            if isinstance(r, pd.DataFrame):
                r = r.iloc[-1]
            return r.to_dict()
        return {"plays_mean": 63.0, "plays_sd": 7.0, "pass_rate": 0.58, "epa_per_play": 0.0, "success_rate": 0.43}

    def role_inputs(team: str):
        qg = qbs[qbs["team"].map(canonical_team).eq(team)].copy() if not qbs.empty else pd.DataFrame()
        rg = rbs[rbs["team"].map(canonical_team).eq(team)].copy() if not rbs.empty else pd.DataFrame()
        wg = recs[recs["team"].map(canonical_team).eq(team)].copy() if not recs.empty else pd.DataFrame()
        if unavailable:
            for local in [qg, rg, wg]:
                if not local.empty and "aita_player_id" in local.columns:
                    local.drop(local[local["aita_player_id"].astype(str).isin(unavailable)].index, inplace=True)
        qb = qg.sort_values("attempts_mean", ascending=False).iloc[0].to_dict() if not qg.empty else None
        rb_list = rg.sort_values("carries_mean", ascending=False).head(4).to_dict("records") if not rg.empty else []
        wr_list = wg.sort_values("targets_mean", ascending=False).head(8).to_dict("records") if not wg.empty else []
        return qb, rb_list, wr_list

    for i, game in slate.reset_index(drop=True).iterrows():
        event_id = str(game["aita_event_id"])
        home, away = str(game["home_team"]), str(game["away_team"])
        h_state, a_state = team_dict(home), team_dict(away)
        weather_effects = _weather_effects_for_event(state.get("weather", pd.DataFrame()), event_id)
        # Weather scoring impact is a bounded modifier to the independent pre-market environment. Mainline anchoring remains
        # the stronger external information source when present.
        h_game_state, a_game_state = dict(h_state), dict(a_state)
        score_mult = float(weather_effects.get("scoring_multiplier", 1.0))
        if score_mult < 1.0:
            for st in (h_game_state, a_game_state):
                st["epa_per_play"] = float(st.get("epa_per_play", 0.0)) * score_mult
        gs = simulate_game(event_id, home, away, h_game_state, a_game_state, draws_n, base_seed + i * 104729,
                           anchor=game_anchors.get(event_id), market_weight=market_weight)
        all_draws.update(gs.draws)
        game_summaries.append(gs.summary)
        team_inputs = [
            (home, h_state, gs.home_script_shift, gs.draws[f"GAME|{event_id}|home_offensive_plays"]),
            (away, a_state, gs.away_script_shift, gs.draws[f"GAME|{event_id}|away_offensive_plays"]),
        ]
        for j, (team, ts, script_shift, game_plays) in enumerate(team_inputs):
            qb, rb_list, wr_list = role_inputs(team)
            sim = simulate_team(team, ts, qb, rb_list, wr_list, draws_n, base_seed + i * 104729 + (j + 1) * 7919,
                                week1_uncertainty=week1_mult, script_shift=script_shift,
                                team_plays_override=game_plays, weather=weather_effects)
            all_draws.update(sim.draws)
            summaries.append(sim.summary)
            reconciliations.append(sim.reconciliation)
    assert_simulation_reconciliation(reconciliations)
    player_summary = pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame()
    games_df = pd.DataFrame(game_summaries)
    if not games_df.empty:
        game_rows = []
        for _, r in games_df.iterrows():
            for stat, col in [("home_points", "home_points_mean"), ("away_points", "away_points_mean"), ("game_total", "total_mean"), ("home_margin", "margin_home_mean")]:
                game_rows.append({"team": r["home_team"], "player_id": "GAME", "player_name": r["aita_event_id"], "position": "GAME",
                                  "stat": stat, "mean": r[col], "sd": np.nan, "p10": np.nan, "p25": np.nan, "median": np.nan, "p75": np.nan, "p90": np.nan,
                                  "aita_event_id": r["aita_event_id"]})
        player_summary = pd.concat([player_summary, pd.DataFrame(game_rows)], ignore_index=True, sort=False)
    state["game_sim_summary"] = games_df
    scorer_draws, scorer_summary, scorer_recon = simulate_scorers(
        slate, all_draws, state.get("scorer_state", pd.DataFrame()), pm, base_seed + 900001,
        team_td_state=state.get("team_td_state", pd.DataFrame()),
        other_share=float(cfg.get("scoring", "other_touchdown_share", default=0.12)),
    )
    all_draws.update(scorer_draws)
    state["scorer_sim_summary"] = scorer_summary
    state["scorer_reconciliation"] = scorer_recon
    return all_draws, player_summary, reconciliations

def _map_odds_events(
    odds_events: list[dict],
    slate: pd.DataFrame,
    max_time_delta_hours: float = 12.0,
) -> tuple[dict[str, str], dict[str, set[str]]]:
    """One-to-one Odds API -> AITA event mapping.

    Match on:
      1. exact home team
      2. exact away team
      3. kickoff-time proximity

    Kickoff is mandatory because the Odds API may return games from
    multiple future weeks and NFL opponents can meet more than once.
    """

    if slate.empty:
        return {}, {}

    s = slate.copy()

    s["_kickoff_utc"] = pd.to_datetime(
        s["kickoff_utc"],
        utc=True,
        errors="coerce",
    )

    candidates = []

    for ev in odds_events:
        odds_id = str(
            ev.get("id") or ""
        )

        home = team_from_full_name(
            ev.get("home_team", "")
        )

        away = team_from_full_name(
            ev.get("away_team", "")
        )

        commence = pd.to_datetime(
            ev.get("commence_time"),
            utc=True,
            errors="coerce",
        )

        if (
            not odds_id
            or not home
            or not away
            or pd.isna(commence)
        ):
            continue

        possible = s[
            s["home_team"].astype(str).eq(home)
            &
            s["away_team"].astype(str).eq(away)
        ].copy()

        if possible.empty:
            continue

        possible["_delta"] = (
            possible["_kickoff_utc"]
            - commence
        ).abs()

        possible = possible[
            possible["_delta"]
            <= pd.Timedelta(
                hours=max_time_delta_hours
            )
        ]

        if possible.empty:
            continue

        best_idx = (
            possible["_delta"]
            .idxmin()
        )

        best = possible.loc[
            best_idx
        ]

        candidates.append(
            (
                best["_delta"],
                odds_id,
                str(best["aita_event_id"]),
                home,
                away,
            )
        )

    # Enforce one-to-one assignment.
    candidates.sort(
        key=lambda x: x[0]
    )

    event_to_aita: dict[str, str] = {}
    event_teams: dict[str, set[str]] = {}

    used_aita: set[str] = set()

    for (
        _delta,
        odds_id,
        aita_id,
        home,
        away,
    ) in candidates:

        if aita_id in used_aita:
            continue

        event_to_aita[
            odds_id
        ] = aita_id

        event_teams[
            odds_id
        ] = {
            home,
            away,
        }

        used_aita.add(
            aita_id
        )

    return (
        event_to_aita,
        event_teams,
    )


def _extract_mainline_anchors(main_df: pd.DataFrame, slate: pd.DataFrame) -> dict[str, dict[str, float]]:
    if main_df.empty or slate.empty:
        return {}
    anchors: dict[str, dict[str, float]] = {}
    for _, game in slate.iterrows():
        event = game["aita_event_id"]
        g = main_df[main_df["aita_event_id"].eq(event)]
        if g.empty:
            continue
        totals = pd.to_numeric(g.loc[g["market_key"].eq("totals"), "line"], errors="coerce").dropna()
        spreads = g[g["market_key"].eq("spreads")].copy()
        if totals.empty or spreads.empty:
            continue
        home_full = str(g.iloc[0].get("home_team_raw") or "").upper()
        hs = pd.to_numeric(spreads.loc[spreads["side"].astype(str).str.upper().eq(home_full), "line"], errors="coerce").dropna()
        if hs.empty:
            continue
        anchors[str(event)] = {"total": float(totals.median()), "home_spread": float(hs.median())}
    return anchors


def _build_game_pricing_board(main_df: pd.DataFrame, slate: pd.DataFrame, draws: dict[str, np.ndarray]) -> pd.DataFrame:
    from nfl_model.pricing.fair_price import fair_american_odds
    rows = []
    for _, g in slate.iterrows():
        eid = str(g["aita_event_id"])
        hp = draws.get(f"GAME|{eid}|home_points")
        ap = draws.get(f"GAME|{eid}|away_points")
        hw = draws.get(f"GAME|{eid}|home_win")
        if hp is None or ap is None or hw is None:
            continue
        sub = main_df[main_df["aita_event_id"].eq(eid)] if not main_df.empty else pd.DataFrame()
        total_lines = pd.to_numeric(sub.loc[sub["market_key"].eq("totals"), "line"], errors="coerce").dropna() if not sub.empty else pd.Series(dtype=float)
        spreads = sub[sub["market_key"].eq("spreads")] if not sub.empty else pd.DataFrame()
        home_full = str(sub.iloc[0].get("home_team_raw") or "").upper() if not sub.empty else ""
        home_spread_vals = pd.to_numeric(spreads.loc[spreads["side"].astype(str).str.upper().eq(home_full), "line"], errors="coerce").dropna() if not spreads.empty else pd.Series(dtype=float)
        p_home = float(np.mean(hw))
        rows.append({
            "aita_event_id": eid, "home_team": g["home_team"], "away_team": g["away_team"],
            "p_home_win_raw": p_home, "p_away_win_raw": float(np.mean(draws[f"GAME|{eid}|away_win"])),
            "p_tie_raw": float(np.mean(draws[f"GAME|{eid}|tie"])),
            "fair_home_moneyline_raw": fair_american_odds(p_home, float(np.mean(draws[f"GAME|{eid}|tie"]))),
            "model_home_points_mean": float(np.mean(hp)), "model_away_points_mean": float(np.mean(ap)),
            "model_total_mean": float(np.mean(hp + ap)), "model_home_margin_mean": float(np.mean(hp - ap)),
            "model_home_spread_fair": float(-np.mean(hp - ap)),
            "market_total_median": float(total_lines.median()) if not total_lines.empty else np.nan,
            "market_home_spread_median": float(home_spread_vals.median()) if not home_spread_vals.empty else np.nan,
            "market_snapshot_rows": int(len(sub)),
        })
    return pd.DataFrame(rows)




def _annotate_convergence(cfg: AppConfig, priced: pd.DataFrame, draws: dict[str, np.ndarray]) -> pd.DataFrame:
    """Attach candidate-line Monte Carlo convergence and quarantine unstable actionable rows."""
    if priced.empty:
        return priced.copy()
    out = priced.copy()
    checkpoints = [int(x) for x in cfg.get("simulation", "convergence_checkpoints")]
    tolerance = float(cfg.get("simulation", "probability_tolerance"))
    statuses, deltas, estimates = [], [], []
    for _, row in out.iterrows():
        stat = MARKET_TO_STAT.get(str(row.get("market_key") or ""))
        pid = row.get("aita_player_id")
        key = f"PLAYER|{pid}|{stat}" if pid and stat else None
        if not key or key not in draws or pd.isna(row.get("line")):
            result = {"status": "NO_DRAWS", "estimates": []}
        else:
            result = probability_convergence(draws[key], str(row.get("side")), float(row.get("line")), checkpoints, tolerance)
        statuses.append(result.get("status"))
        deltas.append(result.get("max_recent_delta", np.nan))
        estimates.append(json.dumps(result.get("estimates", []), separators=(",", ":")))
    out["convergence_status"] = statuses
    out["convergence_max_recent_delta"] = deltas
    out["convergence_estimates"] = estimates
    unstable = out["convergence_status"].eq("NOT_CONVERGED") & out["model_status"].eq("ACTIONABLE_AT_REFERENCE_PRICE")
    out.loc[unstable, "model_status"] = "REJECTED"
    out.loc[unstable, "rejection_reason"] = "DATA_QUALITY"
    return out

def _write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _provider_health_json(health: dict, odds_client: OddsAPIClient | None) -> dict:
    out = dict(health)
    if odds_client is not None:
        out["odds_api"] = "OK"
        out["odds_credits_remaining"] = odds_client.last_remaining
    return out


def _final_boards_markdown(run_id: str, boards: dict[str, pd.DataFrame],
                           forecast_boards: dict[str, pd.DataFrame] | None = None,
                           market_pick_boards: dict[str, pd.DataFrame] | None = None) -> str:
    parts = [
        f"# NFL Final Boards — {run_id}", "",
        "Python pricing snapshot only. Trading decisions occur after handoff.", "",
        "## Board Doctrine", "",
        "- Full Forecast Boards are market-blind calibration forecasts for every player/stat series produced by the simulator.",
        "- Market-Lined Pick Boards choose the model's more probable OVER/UNDER side at the consensus posted line; they are not EV plays.",
        "- EV Play Board is the price-sensitive actionable board and remains separate from forecast accuracy tracking.",
        "- Actual entry, closing line, result grading, CLV, and Dataset B remain Trading-Agent responsibilities.", "",
    ]
    forecast_boards = forecast_boards or {}
    for title, key in [("Receiving Forecast Board", "receiving"), ("Rushing Forecast Board", "rushing"), ("Passing Forecast Board", "passing")]:
        df = forecast_boards.get(key, pd.DataFrame())
        parts += [f"## {title}", ""]
        if df.empty:
            parts += ["No modeled rows.", ""]
            continue
        cols = [c for c in ["forecast_id", "game_label", "player_name", "position", "team", "stat", "model_mean", "model_median", "reference_line", "model_pick_side", "model_pick_probability_raw", "directional_strength", "role_certainty_score"] if c in df.columns]
        parts += [df[cols].head(150).to_markdown(index=False), ""]
    mp = market_pick_boards.get("all", pd.DataFrame()) if market_pick_boards else pd.DataFrame()
    parts += ["## Market-Lined Most-Probable Side Board", ""]
    if mp.empty:
        parts += ["No market-lined rows.", ""]
    else:
        cols = [c for c in ["market_pick_id", "game_label", "player_name", "market_key", "consensus_line", "model_pick_side", "model_pick_probability_raw", "best_posted_price_for_pick", "best_posted_book_for_pick", "directional_strength"] if c in mp.columns]
        parts += [mp[cols].head(200).to_markdown(index=False), ""]
    for title, key in [("EV Play Board", "ev"), ("Edge Leaderboard", "leaderboard"), ("Rejections", "rejection")]:
        df = boards.get(key, pd.DataFrame())
        parts += [f"## {title}", ""]
        if df.empty:
            parts += ["No rows.", ""]
            continue
        cols = [c for c in ["candidate_id", "player_name", "team", "market_key", "side", "line", "bookmaker", "american_odds", "p_conservative", "fair_odds_conservative", "ev_conservative_pct", "buy_to_price", "hard_stop_price", "model_status", "rejection_reason"] if c in df.columns]
        parts += [df[cols].head(100).to_markdown(index=False), ""]
    return "\n".join(parts)


def build_handoff(cfg: AppConfig, season: int, week: int, run_id: str, state: dict[str, Any],
                  sim_draws: dict[str, np.ndarray], sim_summary: pd.DataFrame,
                  priced: pd.DataFrame, game_pricing: pd.DataFrame, odds_client: OddsAPIClient | None,
                  quota_report: dict[str, Any], lineage: dict[str, Any]) -> PipelineArtifacts:
    outputs_root = cfg.root / cfg.get("storage", "outputs_dir")
    run_dir = outputs_root / run_id
    if run_dir.exists():
        raise RuntimeError(f"Immutable run already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    priced = _annotate_convergence(cfg, priced, sim_draws)
    boards = build_boards(priced, run_id)
    forecast_snapshot_time = utc_now_iso()
    forecast_boards = build_full_forecast_boards(
        sim_draws, sim_summary, state["slate"], state["player_map"], run_id, forecast_snapshot_time
    )
    market_pick_boards = build_market_lined_pick_boards(
        priced, sim_draws, state["slate"], state["player_map"], run_id, forecast_snapshot_time
    )
    priced_snapshot = pd.concat([boards["opportunity"], boards["production"]], ignore_index=True, sort=False)

    slate = state["slate"].copy()
    player_roles = pd.concat([state["qb_state"], state["rb_state"], state["rec_state"]], ignore_index=True, sort=False)
    corr = correlation_matrix(sim_draws)
    uncertainty = priced_snapshot[[c for c in ["candidate_id", "aita_player_id", "market_key", "p_raw", "p_calibrated", "p_blend", "p_conservative", "uncertainty_haircut_fraction", "role_certainty_score", "model_agreement_score", "data_freshness_score", "confidence_score", "model_dispersion"] if c in priced_snapshot.columns]].copy() if not priced_snapshot.empty else pd.DataFrame()

    _write_csv(slate, run_dir / f"NFL_SLATE_{season}-W{week:02d}.csv")
    _write_csv(state["team_state"], run_dir / f"NFL_TEAM_STATE_{season}-W{week:02d}.csv")
    _write_csv(player_roles, run_dir / f"NFL_PLAYER_ROLE_STATE_{season}-W{week:02d}.csv")
    _write_csv(game_pricing, run_dir / f"NFL_GAME_PRICING_BOARD_{season}-W{week:02d}.csv")
    _write_csv(forecast_boards["all"], run_dir / f"NFL_ALL_PLAYER_FORECAST_BOARD_{season}-W{week:02d}.csv")
    _write_csv(forecast_boards["receiving"], run_dir / f"NFL_RECEIVING_FORECAST_BOARD_{season}-W{week:02d}.csv")
    _write_csv(forecast_boards["rushing"], run_dir / f"NFL_RUSHING_FORECAST_BOARD_{season}-W{week:02d}.csv")
    _write_csv(forecast_boards["passing"], run_dir / f"NFL_PASSING_FORECAST_BOARD_{season}-W{week:02d}.csv")
    _write_csv(market_pick_boards["all"], run_dir / f"NFL_MARKET_LINED_PICK_BOARD_{season}-W{week:02d}.csv")
    _write_csv(market_pick_boards["receiving"], run_dir / f"NFL_RECEIVING_MARKET_PICK_BOARD_{season}-W{week:02d}.csv")
    _write_csv(market_pick_boards["rushing"], run_dir / f"NFL_RUSHING_MARKET_PICK_BOARD_{season}-W{week:02d}.csv")
    _write_csv(market_pick_boards["passing"], run_dir / f"NFL_PASSING_MARKET_PICK_BOARD_{season}-W{week:02d}.csv")
    _write_csv(boards["opportunity"], run_dir / f"NFL_OPPORTUNITY_PROP_BOARD_{season}-W{week:02d}.csv")
    _write_csv(boards["production"], run_dir / f"NFL_PRODUCTION_PROP_BOARD_{season}-W{week:02d}.csv")
    _write_csv(boards["ev"], run_dir / f"NFL_EV_PLAY_BOARD_{season}-W{week:02d}.csv")
    _write_csv(boards["leaderboard"], run_dir / f"NFL_EDGE_LEADERBOARD_{season}-W{week:02d}.csv")
    _write_csv(boards["rejection"], run_dir / f"NFL_REJECTION_BOARD_{season}-W{week:02d}.csv")
    _write_csv(boards["thesis"], run_dir / f"NFL_THESIS_BOARD_{season}-W{week:02d}.csv")
    _write_csv(corr, run_dir / f"NFL_CORRELATION_MATRIX_{season}-W{week:02d}.csv")
    _write_csv(uncertainty, run_dir / f"NFL_UNCERTAINTY_REPORT_{season}-W{week:02d}.csv")
    convergence_cols = [c for c in ["candidate_id", "aita_player_id", "market_key", "side", "line", "convergence_status", "convergence_max_recent_delta", "convergence_estimates"] if c in priced_snapshot.columns]
    _write_csv(priced_snapshot[convergence_cols] if convergence_cols else pd.DataFrame(), run_dir / f"NFL_CONVERGENCE_REPORT_{season}-W{week:02d}.csv")
    _write_csv(priced_snapshot, run_dir / f"NFL_MARKET_SNAPSHOT_{season}-W{week:02d}.csv")
    try:
        sim_summary.to_parquet(run_dir / f"NFL_MONTE_CARLO_SUMMARY_{season}-W{week:02d}.parquet", index=False)
    except ImportError:
        # Parquet is optional in the handoff spec; keep deterministic CSV fallback in minimal test environments.
        sim_summary.to_csv(run_dir / f"NFL_MONTE_CARLO_SUMMARY_{season}-W{week:02d}.csv", index=False)

    health = _provider_health_json(state.get("provider_health", {}), odds_client)
    (run_dir / f"NFL_PROVIDER_HEALTH_{season}-W{week:02d}.json").write_text(json.dumps(health, indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / f"NFL_ODDS_QUOTA_REPORT_{season}-W{week:02d}.json").write_text(json.dumps(quota_report, indent=2, sort_keys=True), encoding="utf-8")
    metadata = {
        "model_version": __version__,
        "market_scope": list(cfg.markets.get("markets", {}).keys()),
        "pipeline_boundary": boundary_manifest(),
        "board_doctrine": {
            "full_forecast_boards": "MARKET_BLIND_CALIBRATION_FORECASTS_NOT_BETS",
            "market_lined_pick_boards": "MOST_PROBABLE_SIDE_AT_CONSENSUS_POSTED_LINE_NOT_EV_FILTERED",
            "ev_play_board": "PRICE_SENSITIVE_CONSERVATIVE_EV_ACTIONABLE_ONLY",
            "grading_owner": "CLAUDE_NFL_TRADING_AGENT_DATASET_B",
        },
    }
    (run_dir / "NFL_MODEL_METADATA.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / "NFL_DATA_LINEAGE.json").write_text(json.dumps(lineage, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "run_id": run_id, "model_version": __version__, "git_commit": _git_commit(cfg.root), "season": season, "week": week,
        "run_timestamp_utc": utc_now_iso(), "config_hash": cfg.config_hash,
        "random_seed": cfg.get("project", "random_seed"), "simulation_count": int(len(next(iter(sim_draws.values()))) if sim_draws else 0),
        "pipeline_boundary": boundary_manifest(),
    }
    (run_dir / f"NFL_RUN_MANIFEST_{season}-W{week:02d}.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / f"NFL_FINAL_BOARDS_{season}-W{week:02d}.md").write_text(
        _final_boards_markdown(run_id, boards, forecast_boards, market_pick_boards), encoding="utf-8"
    )
    write_handoff_readme(run_dir / "README.md", run_id)

    zip_path = outputs_root / f"NFL_TRADING_AGENT_HANDOFF_{season}-W{week:02d}_{run_id}.zip"
    deterministic_zip(run_dir, zip_path)
    return PipelineArtifacts(run_id, run_dir, zip_path)



def _subset_state_for_slate(state: dict[str, Any], selected_aita_event_ids: list[str] | None) -> dict[str, Any]:
    """Return an in-memory slate subset without rewriting the normalized Week-level source tables."""
    if not selected_aita_event_ids:
        return state

    wanted = {str(x).strip() for x in selected_aita_event_ids if str(x).strip()}
    if not wanted:
        return state

    slate = state["slate"].copy()
    slate["aita_event_id"] = slate["aita_event_id"].astype(str)
    available = set(slate["aita_event_id"])
    missing = sorted(wanted - available)
    if missing:
        raise RuntimeError(f"UNKNOWN_AITA_EVENT_IDS: {missing}")

    slate = slate[slate["aita_event_id"].isin(wanted)].copy().reset_index(drop=True)
    if slate.empty:
        raise RuntimeError("EMPTY_SLATE_AFTER_EVENT_FILTER")

    teams = set(slate["home_team"].astype(str)) | set(slate["away_team"].astype(str))
    out = dict(state)
    out["slate"] = slate
    out["selected_aita_event_ids"] = sorted(wanted)

    team_tables = {
        "rosters": "current_team",
        "depths": "team",
        "injuries": "team",
        "team_state": "team",
        "qb_state": "team",
        "rb_state": "team",
        "rec_state": "team",
        "scorer_state": "team",
        "team_td_state": "team",
        "coaching_state": "team",
        "matchup_state": "team",
        "player_map": "current_team",
    }
    for key, col in team_tables.items():
        df = out.get(key)
        if isinstance(df, pd.DataFrame) and not df.empty and col in df.columns:
            out[key] = df[df[col].astype(str).isin(teams)].copy().reset_index(drop=True)

    weather = out.get("weather")
    if isinstance(weather, pd.DataFrame) and not weather.empty and "aita_event_id" in weather.columns:
        out["weather"] = weather[weather["aita_event_id"].astype(str).isin(wanted)].copy().reset_index(drop=True)

    return out


def _safe_slate_label(value: str | None) -> str | None:
    if value is None:
        return None
    label = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value).strip().upper()).strip("_")
    return label or None


def run_live(
    cfg: AppConfig,
    season: int,
    week: int,
    draws_n: int | None = None,
    shortlist_events: int = 6,
    selected_aita_event_ids: list[str] | None = None,
    slate_label: str | None = None,
) -> PipelineArtifacts:
    load_dotenv(cfg.root / ".env")
    run_id = make_run_id(season, week)
    label = _safe_slate_label(slate_label)
    if label:
        run_id = f"{run_id}-{label}"
    state = ingest_football(cfg, season, week)
    state = _subset_state_for_slate(state, selected_aita_event_ids)
    draws_n = int(draws_n or cfg.get("simulation", "production_draws", default=100000))
    sim_draws, sim_summary, recon = simulate_slate(cfg, season, week, state, draws_n)

    odds_cfg = cfg.get("odds")
    odds_client = OddsAPIClient(
        cfg.get("providers", "odds_base"),
        cfg.root / cfg.get("storage", "cache_dir") / "odds_api",
        cfg.root / cfg.get("storage", "raw_dir") / "odds_api" / "quota_ledger.jsonl",
        bookmakers=list(odds_cfg["bookmakers"]), reserve=int(odds_cfg["monthly_credit_reserve"]),
        ttl_minutes=int(odds_cfg["cache_ttl_minutes"]), timeout=int(odds_cfg["timeout_seconds"]), max_retries=int(odds_cfg["max_retries"]),
    )
    events = odds_client.events(odds_cfg["sport_key"])
    event_to_aita, event_teams = _map_odds_events(events, state["slate"])
    eligible_events = [e for e in events if str(e.get("id")) in event_to_aita]
    # Enrich the event identity map with the Odds API event id once market discovery has resolved the matchup.
    event_map_path = Path(state["normalized_dir"]) / "entity_map_event.csv"
    event_map = pd.read_csv(event_map_path) if event_map_path.exists() else state["slate"][["aita_event_id"]].copy()
    inv_event = {aita: odds for odds, aita in event_to_aita.items()}
    new_odds_ids = event_map["aita_event_id"].astype(str).map(inv_event)
    if "odds_api_event_id" in event_map.columns:
        event_map["odds_api_event_id"] = new_odds_ids.combine_first(event_map["odds_api_event_id"])
    else:
        event_map["odds_api_event_id"] = new_odds_ids
    event_map.to_csv(event_map_path, index=False)

    plan = estimate_plan(len(eligible_events), len(odds_cfg["opportunity_markets"]), len(odds_cfg["production_markets"]),
                         min(shortlist_events, len(eligible_events)), 2, list(odds_cfg["bookmakers"]))
    if odds_client.last_remaining is not None and odds_client.last_remaining - plan.planned_max < int(odds_cfg["monthly_credit_reserve"]):
        raise RuntimeError(f"BLOCKED_BY_QUOTA_GOVERNOR: remaining={odds_client.last_remaining} planned={plan.planned_max} reserve={odds_cfg['monthly_credit_reserve']}")
    quota_report = {**plan.__dict__, "credits_remaining_before_paid_calls": odds_client.last_remaining,
                    "monthly_credit_reserve": odds_cfg["monthly_credit_reserve"]}

    main_raw = odds_client.mainlines(odds_cfg["sport_key"], list(odds_cfg["mainlines"]))
    main_df = normalize_event_odds(main_raw, utc_now_iso())
    if not main_df.empty:
        main_df["aita_event_id"] = main_df["odds_api_event_id"].astype(str).map(event_to_aita)
        main_df = main_df[main_df["aita_event_id"].notna()].copy()

    # Layer 1 remains permanently market-blind. Mainlines are stored as a pricing/challenger
    # context only and MUST NOT overwrite the original football forecast distributions.
    game_anchors = _extract_mainline_anchors(main_df, state["slate"])

    prop_frames = []
    for ev in eligible_events:
        payload = odds_client.event_odds(odds_cfg["sport_key"], str(ev["id"]), list(odds_cfg["opportunity_markets"]))
        frame = normalize_event_odds(payload, utc_now_iso())
        if not frame.empty:
            frame["aita_event_id"] = str(ev["id"])
            prop_frames.append(frame)
    opportunity_odds = pd.concat(prop_frames, ignore_index=True) if prop_frames else pd.DataFrame()
    if not opportunity_odds.empty:
        opportunity_odds["aita_event_id"] = opportunity_odds["odds_api_event_id"].astype(str).map(event_to_aita)
        opportunity_odds = attach_player_ids(opportunity_odds, state["player_map"], event_teams)
        opportunity_odds = add_novig_probabilities(opportunity_odds)
        opp_lookup = state["slate"].set_index("aita_event_id")
        opportunity_odds["opponent"] = opportunity_odds.apply(lambda r: _opponent_for_row(r, opp_lookup), axis=1)
        priced_opp = price_prop_rows(
            opportunity_odds, sim_draws, state["player_map"], cfg.get("pricing", "initial_ev_floors"),
            cfg.get("pricing", "market_trust"), cfg.get("uncertainty"), float(cfg.get("pricing", "extreme_disagreement_pp", default=0.18)),
            **_pricing_kwargs(cfg, week),
        )
    else:
        priced_opp = pd.DataFrame()

    # Production markets are purchased only for the opportunity shortlist.
    shortlist = []
    if not priced_opp.empty:
        tmp = priced_opp[priced_opp["model_status"].eq("ACTIONABLE_AT_REFERENCE_PRICE")].sort_values("ev_conservative_pct", ascending=False)
        shortlist = tmp["odds_api_event_id"].astype(str).drop_duplicates().head(shortlist_events).tolist()
    prod_frames = []
    for event_id in shortlist:
        payload = odds_client.event_odds(odds_cfg["sport_key"], event_id, list(odds_cfg["production_markets"]))
        frame = normalize_event_odds(payload, utc_now_iso())
        if not frame.empty: prod_frames.append(frame)
    production_odds = pd.concat(prod_frames, ignore_index=True) if prod_frames else pd.DataFrame()
    if not production_odds.empty:
        production_odds["aita_event_id"] = production_odds["odds_api_event_id"].astype(str).map(event_to_aita)
        production_odds = attach_player_ids(production_odds, state["player_map"], event_teams)
        production_odds = add_novig_probabilities(production_odds)
        opp_lookup = state["slate"].set_index("aita_event_id")
        production_odds["opponent"] = production_odds.apply(lambda r: _opponent_for_row(r, opp_lookup), axis=1)
        priced_prod = price_prop_rows(
            production_odds, sim_draws, state["player_map"], cfg.get("pricing", "initial_ev_floors"),
            cfg.get("pricing", "market_trust"), cfg.get("uncertainty"), float(cfg.get("pricing", "extreme_disagreement_pp", default=0.18)),
            **_pricing_kwargs(cfg, week),
        )
    else:
        priced_prod = pd.DataFrame()
    priced = pd.concat([priced_opp, priced_prod], ignore_index=True, sort=False) if not priced_opp.empty or not priced_prod.empty else pd.DataFrame()

    # Final reprice is deliberately limited to candidate event/market families. The refreshed
    # quotes REPLACE the earlier candidate rows so Dataset A is the exact handoff-time reference.
    if not priced.empty:
        candidate_pairs = priced[priced["model_status"].eq("ACTIONABLE_AT_REFERENCE_PRICE")][["odds_api_event_id", "market_key"]].drop_duplicates()
        refreshed_frames = []
        refreshed_keys: set[tuple[str, str]] = set()
        for event_id, g in candidate_pairs.groupby("odds_api_event_id"):
            markets = g["market_key"].astype(str).tolist()[:3]
            if not markets:
                continue
            payload = odds_client.event_odds(odds_cfg["sport_key"], str(event_id), markets, force_refresh=True)
            frame = normalize_event_odds(payload, utc_now_iso())
            if frame.empty:
                continue
            frame["aita_event_id"] = frame["odds_api_event_id"].astype(str).map(event_to_aita)
            frame = attach_player_ids(frame, state["player_map"], event_teams)
            frame = add_novig_probabilities(frame)
            opp_lookup = state["slate"].set_index("aita_event_id")
            frame["opponent"] = frame.apply(lambda r: _opponent_for_row(r, opp_lookup), axis=1)
            refreshed_frames.append(price_prop_rows(
                frame, sim_draws, state["player_map"], cfg.get("pricing", "initial_ev_floors"),
                cfg.get("pricing", "market_trust"), cfg.get("uncertainty"), float(cfg.get("pricing", "extreme_disagreement_pp", default=0.18)),
                **_pricing_kwargs(cfg, week),
            ))
            refreshed_keys.update((str(event_id), str(m)) for m in markets)
        if refreshed_frames:
            refreshed = pd.concat(refreshed_frames, ignore_index=True, sort=False)
            keep = ~priced.apply(lambda r: (str(r.get("odds_api_event_id")), str(r.get("market_key"))) in refreshed_keys, axis=1)
            priced = pd.concat([priced.loc[keep], refreshed], ignore_index=True, sort=False)

    quota_report["credits_remaining_after_pricing"] = odds_client.last_remaining
    lineage = {
        "scoreboard_snapshot": state.get("scoreboard_snapshot"),
        "nflverse_cache_dir": str(cfg.root / cfg.get("storage", "cache_dir") / "nflverse"),
        "odds_quota_ledger": str(cfg.root / cfg.get("storage", "raw_dir") / "odds_api" / "quota_ledger.jsonl"),
        "entity_join_rule": "NAME + EVENT TEAM (+ POSITION when available); ambiguous rows quarantined",
        "simulation_reconciliation": recon,
        "mainline_game_anchors": game_anchors,
        "slate_label": label,
        "selected_aita_event_ids": sorted(state.get("selected_aita_event_ids", [])),
    }
    return build_handoff(cfg, season, week, run_id, state, sim_draws, sim_summary, priced, _build_game_pricing_board(main_df, state["slate"], sim_draws), odds_client, quota_report, lineage)



def _pricing_kwargs(cfg: AppConfig, week: int) -> dict[str, Any]:
    return {
        "allowed_positions": {k: list(v.get("positions", [])) for k, v in cfg.markets.get("markets", {}).items()},
        "week": week,
        "max_market_age_minutes": float(cfg.get("pricing", "max_market_age_minutes", default=90.0)),
        "buy_to_extra_ev_margin": float(cfg.get("pricing", "buy_to_extra_ev_margin", default=0.01)),
        "hard_stop_extra_ev_margin": float(cfg.get("pricing", "hard_stop_extra_ev_margin", default=0.0)),
    }

def _opponent_for_row(row: pd.Series, slate_idx: pd.DataFrame) -> str | None:
    event = row.get("aita_event_id")
    team = row.get("team")
    if event not in slate_idx.index:
        return None
    g = slate_idx.loc[event]
    if team == g["home_team"]: return g["away_team"]
    if team == g["away_team"]: return g["home_team"]
    return None


def run_demo(cfg: AppConfig, season: int, week: int, draws_n: int = 25000) -> PipelineArtifacts:
    """Offline deterministic end-to-end proof using synthetic frozen football + market inputs."""
    run_id = make_run_id(season, week) + "-DEMO"
    slate = pd.DataFrame([{
        "aita_event_id": f"NFL-DEMO-{season}-W{week:02d}", "season": season, "week": week,
        "kickoff_utc": f"{season}-09-10T00:20:00Z", "home_team": "KC", "away_team": "BUF",
        "home_espn_team_id": "12", "away_espn_team_id": "2", "espn_event_id": "DEMO", "status": "STATUS_SCHEDULED", "venue": "DEMO",
    }])
    team_state = pd.DataFrame([
        {"team": "KC", "plays_mean": 65.0, "plays_sd": 6.5, "pass_rate": 0.61, "epa_per_play": 0.12, "success_rate": 0.47, "games_observed": 18},
        {"team": "BUF", "plays_mean": 64.0, "plays_sd": 6.8, "pass_rate": 0.59, "epa_per_play": 0.10, "success_rate": 0.46, "games_observed": 18},
    ])
    qb = pd.DataFrame([
        {"gsis_id": "00-DEMO-QB1", "player_name": "Demo KC Quarterback", "team": "KC", "position": "QB", "attempts_mean": 36, "completion_rate": .67, "pass_yards_per_attempt": 7.5, "sack_per_dropback": .05, "scramble_proxy_rate": .05, "games_observed": 18},
        {"gsis_id": "00-DEMO-QB2", "player_name": "Demo BUF Quarterback", "team": "BUF", "position": "QB", "attempts_mean": 35, "completion_rate": .65, "pass_yards_per_attempt": 7.3, "sack_per_dropback": .06, "scramble_proxy_rate": .07, "games_observed": 18},
    ])
    rb = pd.DataFrame([
        {"gsis_id": "00-DEMO-RB1", "player_name": "Demo KC Running Back", "team": "KC", "position": "RB", "carries_mean": 15, "targets_mean": 3.5, "catch_rate": .76, "rush_yards_per_carry": 4.5, "rec_yards_per_reception": 7.4, "games_observed": 16},
        {"gsis_id": "00-DEMO-RB2", "player_name": "Demo BUF Running Back", "team": "BUF", "position": "RB", "carries_mean": 16, "targets_mean": 3.0, "catch_rate": .73, "rush_yards_per_carry": 4.4, "rec_yards_per_reception": 7.0, "games_observed": 17},
    ])
    rec = pd.DataFrame([
        {"gsis_id": "00-DEMO-WR1", "player_name": "Demo KC Receiver", "team": "KC", "position": "WR", "targets_mean": 8.0, "route_share_median": .86, "route_share_sd": .08, "catch_rate": .66, "yards_per_reception": 12.0, "games_observed": 18},
        {"gsis_id": "00-DEMO-WR2", "player_name": "Demo BUF Receiver", "team": "BUF", "position": "WR", "targets_mean": 8.5, "route_share_median": .88, "route_share_sd": .08, "catch_rate": .65, "yards_per_reception": 13.0, "games_observed": 18},
    ])
    pm = _augment_player_map(qb, rb, rec, season, week)
    qb, rb, rec = (_player_states_with_ids(x, pm) for x in [qb, rb, rec])
    state = {"slate": slate, "team_state": team_state, "qb_state": qb, "rb_state": rb, "rec_state": rec,
             "player_map": pm, "provider_health": {"demo_fixture": "OK"}}
    sim_draws, sim_summary, recon = simulate_slate(cfg, season, week, state, draws_n)
    event_id = "ODDS-DEMO-1"
    event_teams = {event_id: {"KC", "BUF"}}
    rows = [
        {"odds_api_event_id": event_id, "bookmaker": "draftkings", "market_key": "player_receptions", "player_name_raw": "Demo KC Receiver", "side": "OVER", "line": 4.5, "american_odds": -110, "snapshot_time_utc": utc_now_iso()},
        {"odds_api_event_id": event_id, "bookmaker": "draftkings", "market_key": "player_receptions", "player_name_raw": "Demo KC Receiver", "side": "UNDER", "line": 4.5, "american_odds": -110, "snapshot_time_utc": utc_now_iso()},
        {"odds_api_event_id": event_id, "bookmaker": "fanduel", "market_key": "player_rush_attempts", "player_name_raw": "Demo KC Running Back", "side": "OVER", "line": 13.5, "american_odds": -105, "snapshot_time_utc": utc_now_iso()},
        {"odds_api_event_id": event_id, "bookmaker": "fanduel", "market_key": "player_rush_attempts", "player_name_raw": "Demo KC Running Back", "side": "UNDER", "line": 13.5, "american_odds": -115, "snapshot_time_utc": utc_now_iso()},
        {"odds_api_event_id": event_id, "bookmaker": "betrivers", "market_key": "player_pass_attempts", "player_name_raw": "Demo KC Quarterback", "side": "OVER", "line": 34.5, "american_odds": -108, "snapshot_time_utc": utc_now_iso()},
        {"odds_api_event_id": event_id, "bookmaker": "betrivers", "market_key": "player_pass_attempts", "player_name_raw": "Demo KC Quarterback", "side": "UNDER", "line": 34.5, "american_odds": -112, "snapshot_time_utc": utc_now_iso()},
    ]
    odds = pd.DataFrame(rows)
    odds["aita_event_id"] = slate.iloc[0]["aita_event_id"]
    odds = attach_player_ids(odds, pm, event_teams)
    odds["opponent"] = "BUF"
    odds = add_novig_probabilities(odds)
    priced = price_prop_rows(odds, sim_draws, pm, cfg.get("pricing", "initial_ev_floors"), cfg.get("pricing", "market_trust"), cfg.get("uncertainty"), float(cfg.get("pricing", "extreme_disagreement_pp", default=.18)), **_pricing_kwargs(cfg, week))
    quota = {"mode": "OFFLINE_DEMO", "paid_credits_used": 0}
    lineage = {"mode": "OFFLINE_DEMO", "simulation_reconciliation": recon}
    return build_handoff(cfg, season, week, run_id, state, sim_draws, sim_summary, priced, _build_game_pricing_board(pd.DataFrame(), slate, sim_draws), None, quota, lineage)
