from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nfl_model.models.calibration import calibrate_probability
from nfl_model.pricing.engine import MARKET_TO_STAT
from nfl_model.pricing.fair_price import fair_american_odds
from nfl_model.simulation.monte_carlo import probability_from_draws

STAT_TO_MARKET = {v: k for k, v in MARKET_TO_STAT.items()}

CATEGORY_STATS = {
    "receiving": {"receptions", "receiving_yards"},
    "rushing": {"rushing_attempts", "rushing_yards"},
    "passing": {"passing_attempts", "completions", "passing_yards"},
}

FORECAST_COLUMNS = [
    "forecast_id", "forecast_snapshot_id", "forecast_snapshot_time_utc",
    "aita_event_id", "kickoff_utc", "game_label", "home_team", "away_team",
    "aita_player_id", "player_name", "position", "team", "opponent",
    "board_category", "stat", "market_key_equivalent",
    "model_mean", "model_sd", "model_p10", "model_p25", "model_median", "model_p75", "model_p90",
    "reference_line", "reference_line_source", "reference_line_method",
    "p_over_raw", "p_under_raw", "p_push", "model_pick_side", "model_pick_probability_raw",
    "model_pick_probability_calibrated", "fair_odds_model_pick_raw", "fair_odds_model_pick_calibrated",
    "directional_edge_pp", "directional_strength", "role_certainty_score", "model_agreement_score",
    "data_freshness_score", "availability_status", "depth_rank",
    "forecast_status", "market_blind", "calibration_key",
]

MARKET_PICK_COLUMNS = [
    "market_pick_id", "forecast_snapshot_id", "forecast_snapshot_time_utc",
    "aita_event_id", "odds_api_event_id", "kickoff_utc", "game_label", "home_team", "away_team",
    "aita_player_id", "player_name", "position", "team", "opponent",
    "board_category", "market_key", "stat", "consensus_line", "consensus_line_method",
    "books_posting_market", "book_count", "p_over_raw", "p_under_raw", "p_push",
    "model_pick_side", "model_pick_probability_raw", "model_pick_probability_calibrated",
    "fair_odds_model_pick_raw", "fair_odds_model_pick_calibrated", "directional_edge_pp", "directional_strength",
    "best_posted_price_for_pick", "best_posted_book_for_pick", "pick_price_status",
    "role_certainty_score", "model_agreement_score", "data_freshness_score",
    "market_pick_status", "calibration_key",
]


def _category_for_stat(stat: str) -> str | None:
    for category, stats in CATEGORY_STATS.items():
        if stat in stats:
            return category
    return None


def _directional_strength(p: float) -> str:
    if p >= 0.70:
        return "VERY_STRONG_DIRECTION"
    if p >= 0.65:
        return "STRONG_DIRECTION"
    if p >= 0.60:
        return "MODERATE_DIRECTION"
    if p >= 0.55:
        return "LEAN_DIRECTION"
    return "NEAR_COIN_FLIP"


def _model_reference_line(mean: float) -> float:
    """Sportsbook-style half point near the model mean.

    This line is deliberately generated from the football model alone. It is a calibration
    reference, not a claimed sportsbook line and not an EV signal.
    """
    if not np.isfinite(mean):
        return np.nan
    return float(max(0.5, np.floor(float(mean)) + 0.5))


def _safe_float(value: Any, default: float = np.nan) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _event_lookup(slate: pd.DataFrame) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if slate.empty:
        return out
    for _, row in slate.iterrows():
        home = str(row.get("home_team") or "")
        away = str(row.get("away_team") or "")
        event = str(row.get("aita_event_id") or "")
        base = {
            "aita_event_id": event,
            "kickoff_utc": row.get("kickoff_utc"),
            "home_team": home,
            "away_team": away,
            "game_label": f"{away} @ {home}",
        }
        if home:
            out[home] = {**base, "opponent": away}
        if away:
            out[away] = {**base, "opponent": home}
    return out


def _player_lookup(player_map: pd.DataFrame) -> pd.DataFrame:
    if player_map.empty or "aita_player_id" not in player_map.columns:
        return pd.DataFrame()
    p = player_map.copy()
    p["aita_player_id"] = p["aita_player_id"].astype(str)
    p = p.drop_duplicates("aita_player_id", keep="last").set_index("aita_player_id")
    return p


def _forecast_id(snapshot_id: str, event_id: str, player_id: str, stat: str, line: float) -> str:
    raw = f"{snapshot_id}|{event_id}|{player_id}|{stat}|{line:.3f}"
    return "NFL-FCST-" + hashlib.sha1(raw.encode()).hexdigest()[:20].upper()


def build_full_forecast_boards(
    sim_draws: dict[str, np.ndarray],
    sim_summary: pd.DataFrame,
    slate: pd.DataFrame,
    player_map: pd.DataFrame,
    snapshot_id: str,
    snapshot_time_utc: str,
) -> dict[str, pd.DataFrame]:
    """Build market-blind receiving/rushing/passing forecast boards.

    Every player-stat series actually produced by the simulator receives a deterministic
    sportsbook-style model reference line and an OVER/UNDER directional pick. These rows are
    calibration forecasts, not bets and not EV recommendations.
    """
    events = _event_lookup(slate)
    players = _player_lookup(player_map)
    rows: list[dict[str, Any]] = []

    if sim_summary.empty:
        empty = pd.DataFrame(columns=FORECAST_COLUMNS)
        return {"all": empty.copy(), "receiving": empty.copy(), "rushing": empty.copy(), "passing": empty.copy()}

    summary = sim_summary.copy()
    summary = summary[summary.get("player_id", pd.Series(index=summary.index, dtype=object)).astype(str).ne("GAME")]

    for _, row in summary.iterrows():
        stat = str(row.get("stat") or "")
        category = _category_for_stat(stat)
        if category is None:
            continue
        player_id = str(row.get("player_id") or "")
        team = str(row.get("team") or "")
        key = f"PLAYER|{player_id}|{stat}"
        if not player_id or key not in sim_draws:
            continue

        event = events.get(team, {})
        event_id = str(event.get("aita_event_id") or "")
        values = sim_draws[key]
        mean = _safe_float(row.get("mean"), float(np.mean(values)))
        line = _model_reference_line(mean)
        if not np.isfinite(line):
            continue

        p_over, p_push_over, _ = probability_from_draws(values, "OVER", line)
        p_under, p_push_under, _ = probability_from_draws(values, "UNDER", line)
        p_push = max(p_push_over, p_push_under)
        if p_over >= p_under:
            side, p_pick = "OVER", p_over
        else:
            side, p_pick = "UNDER", p_under
        p_cal = calibrate_probability(p_pick)

        meta = players.loc[player_id] if isinstance(players, pd.DataFrame) and player_id in players.index else {}
        if isinstance(meta, pd.DataFrame):
            meta = meta.iloc[-1]
        get_meta = meta.get if hasattr(meta, "get") else lambda _k, default=None: default
        player_name = row.get("player_name") or get_meta("full_name")
        position = str(row.get("position") or get_meta("position") or "")
        calibration_key = f"{event_id}|{player_id}|{stat}|{line:.1f}"

        rows.append({
            "forecast_id": _forecast_id(snapshot_id, event_id, player_id, stat, line),
            "forecast_snapshot_id": snapshot_id,
            "forecast_snapshot_time_utc": snapshot_time_utc,
            "aita_event_id": event_id,
            "kickoff_utc": event.get("kickoff_utc"),
            "game_label": event.get("game_label"),
            "home_team": event.get("home_team"),
            "away_team": event.get("away_team"),
            "aita_player_id": player_id,
            "player_name": player_name,
            "position": position,
            "team": team,
            "opponent": event.get("opponent"),
            "board_category": category.upper(),
            "stat": stat,
            "market_key_equivalent": STAT_TO_MARKET.get(stat),
            "model_mean": mean,
            "model_sd": _safe_float(row.get("sd")),
            "model_p10": _safe_float(row.get("p10")),
            "model_p25": _safe_float(row.get("p25")),
            "model_median": _safe_float(row.get("median")),
            "model_p75": _safe_float(row.get("p75")),
            "model_p90": _safe_float(row.get("p90")),
            "reference_line": line,
            "reference_line_source": "MODEL_NATIVE",
            "reference_line_method": "HALF_POINT_NEAREST_MODEL_MEAN_NO_MARKET_INPUT",
            "p_over_raw": p_over,
            "p_under_raw": p_under,
            "p_push": p_push,
            "model_pick_side": side,
            "model_pick_probability_raw": p_pick,
            "model_pick_probability_calibrated": p_cal,
            "fair_odds_model_pick_raw": fair_american_odds(p_pick, p_push),
            "fair_odds_model_pick_calibrated": fair_american_odds(p_cal, p_push),
            "directional_edge_pp": (p_pick - 0.5) * 100.0,
            "directional_strength": _directional_strength(p_pick),
            "role_certainty_score": _safe_float(get_meta("role_certainty_score")),
            "model_agreement_score": _safe_float(get_meta("model_agreement_score")),
            "data_freshness_score": _safe_float(get_meta("data_freshness_score")),
            "availability_status": get_meta("availability_status"),
            "depth_rank": get_meta("depth_rank"),
            "forecast_status": "CALIBRATION_FORECAST_NOT_EV_PLAY",
            "market_blind": True,
            "calibration_key": calibration_key,
        })

    all_board = pd.DataFrame(rows, columns=FORECAST_COLUMNS)
    if not all_board.empty:
        all_board = all_board.sort_values(
            ["kickoff_utc", "aita_event_id", "board_category", "team", "model_pick_probability_raw", "player_name", "stat"],
            ascending=[True, True, True, True, False, True, True],
            na_position="last",
        ).reset_index(drop=True)
        all_board["forecast_rank_within_game_category"] = (
            all_board.groupby(["aita_event_id", "board_category"])["model_pick_probability_raw"]
            .rank(method="first", ascending=False).astype(int)
        )

    return {
        "all": all_board,
        "receiving": all_board[all_board["board_category"].eq("RECEIVING")].copy() if not all_board.empty else pd.DataFrame(columns=all_board.columns),
        "rushing": all_board[all_board["board_category"].eq("RUSHING")].copy() if not all_board.empty else pd.DataFrame(columns=all_board.columns),
        "passing": all_board[all_board["board_category"].eq("PASSING")].copy() if not all_board.empty else pd.DataFrame(columns=all_board.columns),
    }


def _consensus_line(group: pd.DataFrame) -> float | None:
    x = group[[c for c in ["bookmaker", "line"] if c in group.columns]].copy()
    if "line" not in x.columns:
        return None
    x["line"] = pd.to_numeric(x["line"], errors="coerce")
    x = x.dropna(subset=["line"])
    if x.empty:
        return None
    if "bookmaker" in x.columns:
        x = x.drop_duplicates(["bookmaker", "line"])
    counts = x["line"].value_counts()
    candidates = counts[counts.eq(counts.max())].index.to_numpy(dtype=float)
    med = float(x["line"].median())
    return float(sorted(candidates, key=lambda v: (abs(v - med), v))[0])


def build_market_lined_pick_boards(
    priced: pd.DataFrame,
    sim_draws: dict[str, np.ndarray],
    slate: pd.DataFrame,
    player_map: pd.DataFrame,
    snapshot_id: str,
    snapshot_time_utc: str,
) -> dict[str, pd.DataFrame]:
    """One most-probable side per player/market at the consensus posted line.

    This board is probability-first and deliberately independent of EV status. The EV board remains
    the only price-sensitive bet board.
    """
    empty = pd.DataFrame(columns=MARKET_PICK_COLUMNS)
    if priced.empty:
        return {"all": empty.copy(), "receiving": empty.copy(), "rushing": empty.copy(), "passing": empty.copy()}

    events_by_team = _event_lookup(slate)
    players = _player_lookup(player_map)
    rows: list[dict[str, Any]] = []
    p = priced.copy()
    if "aita_player_id" not in p.columns or "market_key" not in p.columns:
        return {"all": empty.copy(), "receiving": empty.copy(), "rushing": empty.copy(), "passing": empty.copy()}

    grouping = ["aita_event_id", "aita_player_id", "market_key"]
    for keys, group in p.groupby(grouping, dropna=False):
        event_id, player_id, market_key = map(str, keys)
        stat = MARKET_TO_STAT.get(market_key)
        category = _category_for_stat(str(stat)) if stat else None
        line = _consensus_line(group)
        draw_key = f"PLAYER|{player_id}|{stat}" if stat else None
        if category is None or line is None or not draw_key or draw_key not in sim_draws:
            continue

        values = sim_draws[draw_key]
        p_over, p_push_over, _ = probability_from_draws(values, "OVER", line)
        p_under, p_push_under, _ = probability_from_draws(values, "UNDER", line)
        p_push = max(p_push_over, p_push_under)
        side, p_pick = ("OVER", p_over) if p_over >= p_under else ("UNDER", p_under)
        p_cal = calibrate_probability(p_pick)

        meta = players.loc[player_id] if isinstance(players, pd.DataFrame) and player_id in players.index else {}
        if isinstance(meta, pd.DataFrame):
            meta = meta.iloc[-1]
        get_meta = meta.get if hasattr(meta, "get") else lambda _k, default=None: default
        team = str(group.get("team", pd.Series(dtype=object)).dropna().astype(str).iloc[0]) if "team" in group and group["team"].notna().any() else str(get_meta("current_team") or "")
        event = events_by_team.get(team, {})
        player_name = (
            group["player_name_raw"].dropna().astype(str).iloc[0]
            if "player_name_raw" in group.columns and group["player_name_raw"].notna().any()
            else get_meta("full_name")
        )

        at_line = group[pd.to_numeric(group["line"], errors="coerce").eq(line)].copy()
        picked_quotes = at_line[at_line.get("side", pd.Series(index=at_line.index, dtype=object)).astype(str).str.upper().eq(side)].copy()
        best_price = np.nan
        best_book = None
        if not picked_quotes.empty and "american_odds" in picked_quotes.columns:
            picked_quotes["_price"] = pd.to_numeric(picked_quotes["american_odds"], errors="coerce")
            picked_quotes = picked_quotes.dropna(subset=["_price"])
            if not picked_quotes.empty:
                best = picked_quotes.sort_values("_price", ascending=False).iloc[0]
                best_price = float(best["_price"])
                best_book = best.get("bookmaker")

        books = sorted(set(group.get("bookmaker", pd.Series(dtype=object)).dropna().astype(str)))
        odds_event_ids = group.get("odds_api_event_id", pd.Series(dtype=object)).dropna().astype(str)
        odds_event_id = odds_event_ids.iloc[0] if not odds_event_ids.empty else None
        raw = f"{snapshot_id}|{event_id}|{player_id}|{market_key}|{line:.3f}"
        market_pick_id = "NFL-MKT-PICK-" + hashlib.sha1(raw.encode()).hexdigest()[:18].upper()

        rows.append({
            "market_pick_id": market_pick_id,
            "forecast_snapshot_id": snapshot_id,
            "forecast_snapshot_time_utc": snapshot_time_utc,
            "aita_event_id": event_id,
            "odds_api_event_id": odds_event_id,
            "kickoff_utc": event.get("kickoff_utc"),
            "game_label": event.get("game_label"),
            "home_team": event.get("home_team"),
            "away_team": event.get("away_team"),
            "aita_player_id": player_id,
            "player_name": player_name,
            "position": get_meta("position"),
            "team": team,
            "opponent": event.get("opponent"),
            "board_category": category.upper(),
            "market_key": market_key,
            "stat": stat,
            "consensus_line": line,
            "consensus_line_method": "MOST_COMMON_POSTED_LINE_ACROSS_SELECTED_BOOKS_TIE_MEDIAN",
            "books_posting_market": ";".join(books),
            "book_count": len(books),
            "p_over_raw": p_over,
            "p_under_raw": p_under,
            "p_push": p_push,
            "model_pick_side": side,
            "model_pick_probability_raw": p_pick,
            "model_pick_probability_calibrated": p_cal,
            "fair_odds_model_pick_raw": fair_american_odds(p_pick, p_push),
            "fair_odds_model_pick_calibrated": fair_american_odds(p_cal, p_push),
            "directional_edge_pp": (p_pick - 0.5) * 100.0,
            "directional_strength": _directional_strength(p_pick),
            "best_posted_price_for_pick": best_price,
            "best_posted_book_for_pick": best_book,
            "pick_price_status": "PRICE_AVAILABLE" if np.isfinite(best_price) else "PICK_SIDE_NOT_POSTED_AT_CONSENSUS_LINE",
            "role_certainty_score": _safe_float(get_meta("role_certainty_score")),
            "model_agreement_score": _safe_float(get_meta("model_agreement_score")),
            "data_freshness_score": _safe_float(get_meta("data_freshness_score")),
            "market_pick_status": "DIRECTIONAL_FORECAST_NOT_EV_PLAY",
            "calibration_key": f"{event_id}|{player_id}|{market_key}|{line:.1f}",
        })

    board = pd.DataFrame(rows, columns=MARKET_PICK_COLUMNS)
    if not board.empty:
        board = board.sort_values(
            ["kickoff_utc", "aita_event_id", "board_category", "model_pick_probability_raw", "player_name", "market_key"],
            ascending=[True, True, True, False, True, True], na_position="last",
        ).reset_index(drop=True)
        board["market_pick_rank_within_game_category"] = (
            board.groupby(["aita_event_id", "board_category"])["model_pick_probability_raw"]
            .rank(method="first", ascending=False).astype(int)
        )

    return {
        "all": board,
        "receiving": board[board["board_category"].eq("RECEIVING")].copy() if not board.empty else pd.DataFrame(columns=board.columns),
        "rushing": board[board["board_category"].eq("RUSHING")].copy() if not board.empty else pd.DataFrame(columns=board.columns),
        "passing": board[board["board_category"].eq("PASSING")].copy() if not board.empty else pd.DataFrame(columns=board.columns),
    }


def write_layer1_forecast_snapshot(
    boards: dict[str, pd.DataFrame],
    features_dir: Path,
    season: int,
    week: int,
    snapshot_id: str,
) -> dict[str, Path]:
    """Write immutable snapshot + latest convenience copies."""
    features_dir.mkdir(parents=True, exist_ok=True)
    snap_dir = features_dir / "forecast_snapshots" / snapshot_id
    if snap_dir.exists():
        raise RuntimeError(f"Immutable forecast snapshot already exists: {snap_dir}")
    snap_dir.mkdir(parents=True)

    names = {
        "all": f"NFL_ALL_PLAYER_FORECAST_BOARD_{season}-W{week:02d}.csv",
        "receiving": f"NFL_RECEIVING_FORECAST_BOARD_{season}-W{week:02d}.csv",
        "rushing": f"NFL_RUSHING_FORECAST_BOARD_{season}-W{week:02d}.csv",
        "passing": f"NFL_PASSING_FORECAST_BOARD_{season}-W{week:02d}.csv",
    }
    paths: dict[str, Path] = {}
    for key, name in names.items():
        df = boards.get(key, pd.DataFrame())
        immutable = snap_dir / name
        latest = features_dir / name
        df.to_csv(immutable, index=False)
        df.to_csv(latest, index=False)
        paths[key] = immutable
    return paths
