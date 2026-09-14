from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np


@dataclass
class GameSimulation:
    draws: dict[str, np.ndarray]
    home_script_shift: np.ndarray
    away_script_shift: np.ndarray
    summary: dict[str, Any]


def _safe(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _baseline_means(home_state: dict, away_state: dict) -> tuple[float, float]:
    """Shrunk pre-market score priors from time-decayed team offense/defense state."""
    h_off = _safe(home_state.get("epa_per_play"))
    a_off = _safe(away_state.get("epa_per_play"))
    h_def = _safe(home_state.get("epa_allowed_per_play"))
    a_def = _safe(away_state.get("epa_allowed_per_play"))
    h_succ = _safe(home_state.get("success_rate"), .43)
    a_succ = _safe(away_state.get("success_rate"), .43)
    h_succ_d = _safe(home_state.get("success_rate_allowed"), .43)
    a_succ_d = _safe(away_state.get("success_rate_allowed"), .43)
    home_match = (h_off - a_def) * 8.5 + (h_succ - a_succ_d) * 11.0 + 1.25
    away_match = (a_off - h_def) * 8.5 + (a_succ - h_succ_d) * 11.0
    return float(np.clip(22.4 + home_match, 13.0, 34.5)), float(np.clip(22.1 + away_match, 13.0, 34.5))


def _anchored_score_means(home_mean: float, away_mean: float, anchor: dict[str, float], market_weight: float) -> tuple[float, float, float | None, float | None, float]:
    market_total = anchor.get("total")
    home_spread = anchor.get("home_spread")
    applied_weight = 0.0
    if market_total is not None and home_spread is not None:
        total = _safe(market_total, home_mean + away_mean)
        hs = _safe(home_spread, away_mean - home_mean)
        # Home spread is signed from the home perspective. -3 means home by 3.
        market_home = total / 2.0 - hs / 2.0
        market_away = total - market_home
        applied_weight = float(np.clip(market_weight, 0.0, 0.85))
        home_mean = (1.0 - applied_weight) * home_mean + applied_weight * market_home
        away_mean = (1.0 - applied_weight) * away_mean + applied_weight * market_away
    return home_mean, away_mean, market_total, home_spread, applied_weight


def _drive_count_mean(state: dict) -> float:
    plays = _safe(state.get("plays_mean"), 63.0)
    # NFL teams typically operate around 10-13 offensive possessions. Faster teams receive a modest lift.
    return float(np.clip(10.8 + (plays - 63.0) / 10.5, 9.4, 13.6))


def _plays_per_drive_mean(state: dict) -> float:
    plays = _safe(state.get("plays_mean"), 63.0)
    drives = _drive_count_mean(state)
    success = _safe(state.get("success_rate"), .43)
    third = _safe(state.get("third_down_rate"), .40)
    base = plays / max(drives, 1.0)
    return float(np.clip(base + (success - .43) * 3.4 + (third - .40) * 1.4, 4.4, 7.4))


def _turnover_per_drive(state: dict) -> float:
    # PBP turnover_rate is per play. Convert to a bounded possession-level probability.
    per_play = float(np.clip(_safe(state.get("turnover_rate"), .025), 0.005, 0.08))
    ppd = _plays_per_drive_mean(state)
    return float(np.clip(1.0 - (1.0 - per_play) ** ppd, 0.045, 0.22))


def _scoring_probabilities(points_mean: float, drives_mean: float, state: dict, opponent_state: dict) -> tuple[float, float, float]:
    """Translate the score prior into possession outcome probabilities.

    The target expected points/drive is the primary anchor. Red-zone and explosive-play states only tilt
    the TD/FG mix; they do not create free expected points. Turnover probability is separately bounded.
    """
    epd = float(np.clip(points_mean / max(drives_mean, 1.0), 1.10, 3.25))
    rz = _safe(state.get("red_zone_td_rate"), .55)
    opp_rz = _safe(opponent_state.get("red_zone_td_rate_allowed"), .55)
    explosive = _safe(state.get("explosive_pass_rate"), .08) + _safe(state.get("explosive_run_rate"), .10)
    opp_explosive = _safe(opponent_state.get("explosive_pass_rate_allowed"), .08) + _safe(opponent_state.get("explosive_run_rate_allowed"), .10)
    td_point_share = float(np.clip(.68 + (rz - opp_rz) * .10 + (explosive - opp_explosive) * .12, .56, .79))
    p_td = float(np.clip(epd * td_point_share / 7.0, .10, .38))
    p_fg = float(np.clip(epd * (1.0 - td_point_share) / 3.0, .08, .31))
    p_to = _turnover_per_drive(state)
    # Leave enough mass for punts/downs/end-of-half; reduce FG first if necessary.
    if p_td + p_fg + p_to > .84:
        p_fg = max(.05, .84 - p_td - p_to)
    return p_td, p_fg, p_to


def _sample_drive_points(rng: np.random.Generator, active: np.ndarray, p_td: float, p_fg: float, p_to: float) -> np.ndarray:
    u = rng.random(len(active))
    pts = np.zeros(len(active), dtype=np.int16)
    pts[active & (u < p_td)] = 7
    pts[active & (u >= p_td) & (u < p_td + p_fg)] = 3
    # turnover/punt/downs/end-half all score zero; turnover probability remains useful in state calibration.
    return pts


def _drive_script_shift(score_diff: np.ndarray, progress: float) -> np.ndarray:
    """Continuous score/time pass-rate pressure.

    A deficit matters more late than early. A lead lowers pass rate, but the leading-side run shift is capped
    because even strong favorites keep throwing in neutral/early-down states.
    """
    urgency = 0.42 + 1.05 * float(np.clip(progress, 0.0, 1.0))
    return np.clip(-score_diff.astype(float) * 0.0064 * urgency, -0.125, 0.185)


def _sample_drive_plays(rng: np.random.Generator, active: np.ndarray, mean: float, score_diff: np.ndarray, progress: float) -> np.ndarray:
    # Teams trailing late play slightly faster; teams sitting on a lead shorten possessions.
    shift = _drive_script_shift(score_diff, progress)
    pace_mult = np.clip(1.0 + shift * 0.28, 0.93, 1.08)
    lam = np.clip(mean * pace_mult, 3.6, 8.2)
    plays = np.where(active, 1 + rng.poisson(np.maximum(lam - 1.0, .25)), 0)
    return np.clip(plays, 0, 14).astype(np.int16)


def simulate_game(
    event_id: str,
    home_team: str,
    away_team: str,
    home_state: dict,
    away_state: dict,
    n: int,
    seed: int,
    anchor: dict[str, float] | None = None,
    market_weight: float = 0.62,
) -> GameSimulation:
    """Vectorized possession/game-state simulation.

    This is intentionally a drive-state engine rather than an independent final-score regression. It simulates
    possessions, drive play counts, score evolution, and time-sensitive lead/trail pressure, then hands the resulting
    per-draw play volume and script state into the player-opportunity simulator.
    """
    rng = np.random.default_rng(seed)
    home_mean, away_mean = _baseline_means(home_state, away_state)
    home_mean, away_mean, market_total, home_spread, applied_weight = _anchored_score_means(
        home_mean, away_mean, anchor or {}, market_weight
    )

    h_drive_mean = _drive_count_mean(home_state)
    a_drive_mean = _drive_count_mean(away_state)
    common_pace = rng.normal(0.0, .55, n)
    home_drives = np.rint(np.clip(rng.normal(h_drive_mean, 1.15, n) + common_pace, 7, 16)).astype(np.int16)
    away_drives = np.rint(np.clip(rng.normal(a_drive_mean, 1.15, n) + common_pace, 7, 16)).astype(np.int16)

    h_td, h_fg, h_to = _scoring_probabilities(home_mean, h_drive_mean, home_state, away_state)
    a_td, a_fg, a_to = _scoring_probabilities(away_mean, a_drive_mean, away_state, home_state)
    h_ppd = _plays_per_drive_mean(home_state)
    a_ppd = _plays_per_drive_mean(away_state)

    home_points = np.zeros(n, dtype=np.int16)
    away_points = np.zeros(n, dtype=np.int16)
    home_touchdowns = np.zeros(n, dtype=np.int16)
    away_touchdowns = np.zeros(n, dtype=np.int16)
    home_plays = np.zeros(n, dtype=np.int16)
    away_plays = np.zeros(n, dtype=np.int16)
    home_shift_num = np.zeros(n, dtype=float)
    away_shift_num = np.zeros(n, dtype=float)

    # Simulate possession rounds. A draw-level coin flip determines which offense receives the first
    # possession, so score-state pressure on the second possession observes the first possession's result.
    max_rounds = 16
    home_first = rng.random(n) < .5

    def run_home(mask: np.ndarray, progress: float) -> None:
        nonlocal home_points, home_touchdowns, home_plays, home_shift_num
        active = mask & (d < home_drives)
        score_diff = home_points - away_points
        shift = _drive_script_shift(score_diff, progress)
        plays = _sample_drive_plays(rng, active, h_ppd, score_diff, progress)
        pts = _sample_drive_points(rng, active, h_td, h_fg, h_to)
        home_points[active] += pts[active]
        home_touchdowns[active] += (pts[active] == 7).astype(np.int16)
        home_plays += plays
        home_shift_num += shift * plays

    def run_away(mask: np.ndarray, progress: float) -> None:
        nonlocal away_points, away_touchdowns, away_plays, away_shift_num
        active = mask & (d < away_drives)
        score_diff = away_points - home_points
        shift = _drive_script_shift(score_diff, progress)
        plays = _sample_drive_plays(rng, active, a_ppd, score_diff, progress)
        pts = _sample_drive_points(rng, active, a_td, a_fg, a_to)
        away_points[active] += pts[active]
        away_touchdowns[active] += (pts[active] == 7).astype(np.int16)
        away_plays += plays
        away_shift_num += shift * plays

    for d in range(max_rounds):
        progress = (d + .5) / max_rounds
        run_home(home_first, progress)
        run_away(home_first, progress)
        run_away(~home_first, progress)
        run_home(~home_first, progress)

    # Add a small end-game scoring noise component for missed/extra possessions, safeties and clock artifacts.
    # It is deliberately much smaller than the old score-regression noise; the possession engine drives the outcome.
    home_points = np.clip(home_points + rng.choice([0, 0, 0, 0, 3, -3], size=n, p=[.56, .12, .10, .08, .08, .06]), 0, 63).astype(np.int16)
    away_points = np.clip(away_points + rng.choice([0, 0, 0, 0, 3, -3], size=n, p=[.56, .12, .10, .08, .08, .06]), 0, 63).astype(np.int16)

    margin = (home_points - away_points).astype(np.int16)
    total_points = (home_points + away_points).astype(np.int16)
    home_win = (margin > 0).astype(np.int8)
    away_win = (margin < 0).astype(np.int8)
    tie = (margin == 0).astype(np.int8)
    home_shift = np.divide(home_shift_num, np.maximum(home_plays, 1), dtype=float)
    away_shift = np.divide(away_shift_num, np.maximum(away_plays, 1), dtype=float)
    home_shift = np.clip(home_shift, -0.12, 0.18)
    away_shift = np.clip(away_shift, -0.12, 0.18)

    draws = {
        f"GAME|{event_id}|home_points": home_points,
        f"GAME|{event_id}|away_points": away_points,
        f"GAME|{event_id}|home_touchdowns": home_touchdowns,
        f"GAME|{event_id}|away_touchdowns": away_touchdowns,
        f"GAME|{event_id}|margin": margin,
        f"GAME|{event_id}|total": total_points,
        f"GAME|{event_id}|home_win": home_win,
        f"GAME|{event_id}|away_win": away_win,
        f"GAME|{event_id}|tie": tie,
        f"GAME|{event_id}|home_drives": home_drives,
        f"GAME|{event_id}|away_drives": away_drives,
        f"GAME|{event_id}|home_offensive_plays": home_plays,
        f"GAME|{event_id}|away_offensive_plays": away_plays,
        f"GAME|{event_id}|home_script_shift": home_shift,
        f"GAME|{event_id}|away_script_shift": away_shift,
    }
    summary = {
        "aita_event_id": event_id,
        "home_team": home_team,
        "away_team": away_team,
        "home_points_mean": float(home_points.mean()),
        "away_points_mean": float(away_points.mean()),
        "home_touchdowns_mean": float(home_touchdowns.mean()),
        "away_touchdowns_mean": float(away_touchdowns.mean()),
        "total_mean": float(total_points.mean()),
        "margin_home_mean": float(margin.mean()),
        "p_home_win_raw": float(home_win.mean()),
        "p_away_win_raw": float(away_win.mean()),
        "p_tie_raw": float(tie.mean()),
        "home_drives_mean": float(home_drives.mean()),
        "away_drives_mean": float(away_drives.mean()),
        "home_plays_mean": float(home_plays.mean()),
        "away_plays_mean": float(away_plays.mean()),
        "home_script_shift_mean": float(home_shift.mean()),
        "away_script_shift_mean": float(away_shift.mean()),
        "market_anchor_total": market_total,
        "market_anchor_home_spread": home_spread,
        "anchor_weight": applied_weight,
        "engine": "POSSESSION_GAME_STATE_V2",
    }
    return GameSimulation(draws, home_shift, away_shift, summary)
