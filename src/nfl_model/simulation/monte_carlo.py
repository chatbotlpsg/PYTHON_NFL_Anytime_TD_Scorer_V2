from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd

from nfl_model.models.plays import sample_team_plays
from nfl_model.models.pass_run import sample_pass_plays
from nfl_model.models.rb_opportunity import allocate_rb_carries
from nfl_model.models.production import simulate_rushing_yards


@dataclass
class SimulationResult:
    draws: dict[str, np.ndarray]
    summary: pd.DataFrame
    reconciliation: dict[str, Any]


def _series_summary(name: str, values: np.ndarray, meta: dict) -> dict:
    q = np.quantile(values, [0.10, 0.25, 0.50, 0.75, 0.90])
    return {
        **meta, "stat": name,
        "mean": float(np.mean(values)), "sd": float(np.std(values)),
        "p10": float(q[0]), "p25": float(q[1]), "median": float(q[2]), "p75": float(q[3]), "p90": float(q[4]),
    }


def _allocate_counts(rng: np.random.Generator, totals: np.ndarray, weights: np.ndarray, concentration: float) -> np.ndarray:
    """Vectorized sequential-binomial allocation. Every row sums exactly to totals."""
    n = len(totals)
    k = len(weights)
    if k == 0:
        return np.empty((n, 0), dtype=np.int16)
    weights = np.asarray(weights, dtype=float)
    weights = np.clip(weights, 1e-6, None)
    weights = weights / weights.sum()
    role_shares = rng.dirichlet(weights * max(concentration, 2.0), size=n)
    out = np.zeros((n, k), dtype=np.int16)
    remaining = totals.astype(np.int32).copy()
    remaining_share = np.ones(n, dtype=float)
    for j in range(k - 1):
        conditional = np.divide(role_shares[:, j], remaining_share, out=np.zeros(n), where=remaining_share > 1e-12)
        conditional = np.clip(conditional, 0, 1)
        x = rng.binomial(remaining, conditional)
        out[:, j] = x.astype(np.int16)
        remaining -= x
        remaining_share -= role_shares[:, j]
    out[:, -1] = remaining.astype(np.int16)
    return out


def _allocate_targets_from_routes(
    rng: np.random.Generator,
    team_targets: np.ndarray,
    routes: np.ndarray,
    target_rates: np.ndarray,
    uncertainty: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Route-first target allocation with exact team-target reconciliation.

    Player routes are generated before targets. Each modeled player's target desire is route count × target rate with
    per-draw role noise. Targets are sequentially allocated subject to the player's route capacity. Any unassigned
    target falls into OTHER, preserving team/QB accounting without forcing impossible player opportunity.
    """
    n, k = routes.shape if routes.ndim == 2 else (len(team_targets), 0)
    if k == 0:
        return np.empty((n, 0), dtype=np.int16), team_targets.astype(np.int16)
    tr = np.clip(np.asarray(target_rates, dtype=float), .025, .45)
    propensity_noise = rng.lognormal(mean=-0.5 * (0.12 * uncertainty) ** 2, sigma=0.12 * uncertainty, size=(n, k))
    desire = routes.astype(float) * tr[None, :] * propensity_noise
    # OTHER absorbs checkdowns, ancillary WR/TE/RB routes, spikes/throwaways counted as targetable feed artifacts.
    other_desire = np.maximum(1.5, team_targets.astype(float) * 0.075)
    remaining = team_targets.astype(np.int32).copy()
    out = np.zeros((n, k), dtype=np.int16)
    remaining_desire = desire.sum(axis=1) + other_desire
    # High-desire players first reduces capacity clipping and stabilizes the finite target surface.
    order = np.argsort(-np.nanmean(desire, axis=0))
    for j in order:
        cond = np.divide(desire[:, j], np.maximum(remaining_desire, 1e-9))
        cond = np.clip(cond, 0.0, 1.0)
        x = rng.binomial(remaining, cond)
        x = np.minimum(x, routes[:, j]).astype(np.int16)
        out[:, j] = x
        remaining -= x.astype(np.int32)
        remaining_desire -= desire[:, j]
    other = remaining.astype(np.int16)
    return out, other


def _sample_attempts(rng: np.random.Generator, pass_plays: np.ndarray, sack_rate: float, scramble_rate: float, uncertainty: float) -> np.ndarray:
    non_attempt_mean = float(np.clip(sack_rate + scramble_rate, 0.0, 0.28))
    non_attempt = np.clip(rng.normal(non_attempt_mean, 0.012 * uncertainty, len(pass_plays)), 0.0, 0.30)
    return rng.binomial(pass_plays, 1.0 - non_attempt).astype(np.int16)


def _receiving_yards(
    rng: np.random.Generator,
    receptions: np.ndarray,
    adot: float,
    yac_per_reception: float,
    ypr_fallback: float,
    uncertainty: float,
) -> np.ndarray:
    """Opportunity-first receiving production: caught air yards + YAC."""
    n = len(receptions)
    if not np.isfinite(adot) or adot <= 0:
        # Infer a conservative air/YAC split from historical yards per reception when air-yard fields are absent.
        adot = max(2.0, ypr_fallback * 0.68)
    if not np.isfinite(yac_per_reception) or yac_per_reception < 0:
        yac_per_reception = max(1.0, ypr_fallback - adot * 0.78)
    caught_air = np.clip(rng.lognormal(np.log(max(adot * .78, 1.0)) - .06, .34 * uncertainty, n), .2, 34.0)
    yac = np.clip(rng.lognormal(np.log(max(yac_per_reception, .6)) - .08, .42 * uncertainty, n), 0.0, 30.0)
    # Heavy-tail explosive component, but generated from the same catch opportunity.
    explosive = rng.binomial(receptions, np.clip(.055 + adot / 300.0, .04, .14))
    bonus = explosive * rng.lognormal(np.log(8.0), .55, n)
    yards = receptions * (caught_air + yac) + bonus
    return np.rint(np.maximum(0, yards)).astype(np.int32)


def simulate_team(
    team: str,
    team_state: dict,
    qb: dict | None,
    rbs: list[dict],
    receivers: list[dict],
    n: int,
    seed: int,
    week1_uncertainty: float = 1.0,
    script_shift: float | np.ndarray = 0.0,
    team_plays_override: np.ndarray | None = None,
    weather: dict | None = None,
) -> SimulationResult:
    rng = np.random.default_rng(seed)
    weather = weather or {}
    if team_plays_override is None:
        plays = sample_team_plays(
            rng, float(team_state.get("plays_mean", 63.0)), float(team_state.get("plays_sd", 7.0)), n,
            uncertainty=week1_uncertainty,
        )
    else:
        plays = np.asarray(team_plays_override, dtype=np.int16).copy()
        if len(plays) != n:
            raise ValueError("team_plays_override length must equal simulation draws")

    weather_pass_shift = float(weather.get("pass_rate_shift", 0.0) or 0.0)
    combined_shift = np.asarray(script_shift, dtype=float) + weather_pass_shift
    pass_plays, rush_plays = sample_pass_plays(
        rng,
        plays,
        float(team_state.get("pass_rate", 0.58)),
        combined_shift,
        early_down_pass_rate=float(team_state.get("neutral_pass_rate", team_state.get("pass_rate", .58))),
        success_rate=float(team_state.get("success_rate", .43)),
    )
    draws: dict[str, np.ndarray] = {
        f"TEAM|{team}|offensive_plays": plays,
        f"TEAM|{team}|pass_plays": pass_plays,
        f"TEAM|{team}|rush_plays": rush_plays,
    }
    rows = [
        _series_summary("offensive_plays", plays, {"team": team, "player_id": "TEAM", "player_name": team, "position": "TEAM"}),
        _series_summary("pass_plays", pass_plays, {"team": team, "player_id": "TEAM", "player_name": team, "position": "TEAM"}),
        _series_summary("rush_plays", rush_plays, {"team": team, "player_id": "TEAM", "player_name": team, "position": "TEAM"}),
    ]

    qb_sack = float((qb or {}).get("sack_per_dropback", 0.07))
    qb_scramble = float((qb or {}).get("scramble_proxy_rate", 0.04))
    attempts = _sample_attempts(rng, pass_plays, qb_sack, qb_scramble, week1_uncertainty)
    qb_id = str((qb or {}).get("aita_player_id") or (qb or {}).get("gsis_id") or (qb or {}).get("player_name") or "UNMAPPED_QB")

    # RB rushing uses a finite subset of team rushes; QB/WR/other runs remain residual.
    backfield_concentration = float(np.clip(sum(float(r.get("carries_mean", 0.0)) for r in rbs) / 18.0, .55, 1.0))
    rb_team_share_mean = float(np.clip(.77 + .13 * backfield_concentration, .70, .92))
    rb_team_share = np.clip(rng.normal(rb_team_share_mean, 0.055 * week1_uncertainty, n), 0.55, 0.97)
    rb_team_carries = rng.binomial(rush_plays, rb_team_share)
    carry_means = [float(r.get("carries_mean", 1.0)) for r in rbs]
    rb_alloc = allocate_rb_carries(rng, rb_team_carries, carry_means)
    rb_stat: dict[str, dict[str, np.ndarray]] = {}
    for rb, carries in zip(rbs, rb_alloc):
        pid = str(rb.get("aita_player_id") or rb.get("gsis_id") or rb.get("player_name"))
        rush_yards = simulate_rushing_yards(rng, carries, float(rb.get("rush_yards_per_carry", 4.1)))
        rb_stat[pid] = {"rushing_attempts": carries, "rushing_yards": rush_yards}

    # Route engine comes before target engine. RBs + WR/TE share one finite route/target pool.
    receiving_pool: list[dict] = []
    team_pass_mean = max(float(np.mean(pass_plays)), 1.0)
    for rb in rbs:
        targets_mean = float(rb.get("targets_mean", 2.5))
        route_share = float(np.clip(rb.get("route_share_median", 0.18 + targets_mean / 18.0), 0.10, 0.72))
        receiving_pool.append({
            "player_id": str(rb.get("aita_player_id") or rb.get("gsis_id") or rb.get("player_name")),
            "player_name": rb.get("player_name"), "position": "RB",
            "route_share": route_share, "route_sd": float(rb.get("route_share_sd", .10)) * week1_uncertainty,
            "target_rate": float(np.clip(targets_mean / max(team_pass_mean * route_share, 1.0), .05, .34)),
            "catch_rate": float(rb.get("catch_rate", 0.72)), "ypr": float(rb.get("rec_yards_per_reception", 7.2)),
            "adot": float(rb.get("adot", 2.0) or 2.0), "yac": float(rb.get("yac_per_reception", 5.0) or 5.0),
        })
    for rec in receivers:
        targets_mean = float(rec.get("targets_mean", 5.0))
        route_share = float(np.clip(rec.get("route_share_median", .75), .08, .99))
        receiving_pool.append({
            "player_id": str(rec.get("aita_player_id") or rec.get("gsis_id") or rec.get("player_name")),
            "player_name": rec.get("player_name"), "position": rec.get("position", "WR"),
            "route_share": route_share, "route_sd": float(rec.get("route_share_sd", 0.10)) * week1_uncertainty,
            "target_rate": float(np.clip(rec.get("target_rate_per_route", targets_mean / max(team_pass_mean * route_share, 1.0)), .04, .40)),
            "catch_rate": float(rec.get("catch_rate", 0.65)), "ypr": float(rec.get("yards_per_reception", 11.5)),
            "adot": float(rec.get("adot", np.nan)), "yac": float(rec.get("yac_per_reception", np.nan)),
        })

    route_cols = []
    for rec in receiving_pool:
        route_share = np.clip(rng.normal(rec["route_share"], rec["route_sd"], n), 0.03, 0.995)
        route_cols.append(rng.binomial(pass_plays, route_share).astype(np.int16))
    route_matrix = np.column_stack(route_cols) if route_cols else np.empty((n, 0), dtype=np.int16)

    targetable_rate = np.clip(rng.normal(0.92, 0.025 * week1_uncertainty, n), 0.80, 0.985)
    team_targets = rng.binomial(attempts, targetable_rate).astype(np.int16)
    target_rates = np.asarray([p["target_rate"] for p in receiving_pool], dtype=float)
    target_alloc, other_targets = _allocate_targets_from_routes(rng, team_targets, route_matrix, target_rates, week1_uncertainty)

    completion_weather_mult = float(weather.get("completion_multiplier", 1.0) or 1.0)
    deep_weather_mult = float(weather.get("deep_yardage_multiplier", 1.0) or 1.0)
    modeled_receptions = np.zeros(n, dtype=np.int16)
    modeled_rec_yards = np.zeros(n, dtype=np.int32)
    for j, rec in enumerate(receiving_pool):
        pid = rec["player_id"]
        routes = route_matrix[:, j].astype(np.int16)
        targets = target_alloc[:, j].astype(np.int16)
        catch_mean = float(np.clip(rec["catch_rate"] * completion_weather_mult, .25, .96))
        catch_p = np.clip(rng.normal(catch_mean, 0.028 * week1_uncertainty, n), 0.25, 0.97)
        receptions = rng.binomial(targets, catch_p).astype(np.int16)
        rec_yards = _receiving_yards(
            rng, receptions, float(rec["adot"]) * deep_weather_mult, float(rec["yac"]), float(rec["ypr"]), week1_uncertainty
        )
        modeled_receptions += receptions
        modeled_rec_yards += rec_yards.astype(np.int32)
        for stat, values in {"routes": routes, "targets": targets, "receptions": receptions, "receiving_yards": rec_yards}.items():
            draws[f"PLAYER|{pid}|{stat}"] = values
            rows.append(_series_summary(stat, values, {"team": team, "player_id": pid, "player_name": rec["player_name"], "position": rec["position"]}))

    qb_completion_rate = float((qb or {}).get("completion_rate", 0.64)) * completion_weather_mult
    other_catch_p = np.clip(rng.normal(qb_completion_rate, 0.035 * week1_uncertainty, n), 0.30, 0.88)
    other_receptions = rng.binomial(other_targets, other_catch_p).astype(np.int16)
    completions = np.minimum(modeled_receptions + other_receptions, attempts).astype(np.int16)
    ypa = float((qb or {}).get("pass_yards_per_attempt", 7.0)) * deep_weather_mult
    other_ypr_mean = ypa / max(float(np.clip(qb_completion_rate, .40, .82)), .40)
    other_ypr = np.clip(rng.lognormal(np.log(max(other_ypr_mean, 3.0)) - .08, .30 * week1_uncertainty, n), 2.0, 25.0)
    other_yards = np.rint(other_receptions * other_ypr).astype(np.int32)
    passing_yards = np.maximum(0, modeled_rec_yards + other_yards).astype(np.int32)

    draws[f"PLAYER|{qb_id}|passing_attempts"] = attempts
    draws[f"PLAYER|{qb_id}|completions"] = completions
    draws[f"PLAYER|{qb_id}|passing_yards"] = passing_yards
    rows.append(_series_summary("passing_attempts", attempts, {"team": team, "player_id": qb_id, "player_name": (qb or {}).get("player_name"), "position": "QB"}))
    rows.append(_series_summary("completions", completions, {"team": team, "player_id": qb_id, "player_name": (qb or {}).get("player_name"), "position": "QB"}))
    rows.append(_series_summary("passing_yards", passing_yards, {"team": team, "player_id": qb_id, "player_name": (qb or {}).get("player_name"), "position": "QB"}))

    for rb, carries in zip(rbs, rb_alloc):
        pid = str(rb.get("aita_player_id") or rb.get("gsis_id") or rb.get("player_name"))
        for stat, values in rb_stat[pid].items():
            draws[f"PLAYER|{pid}|{stat}"] = values
            rows.append(_series_summary(stat, values, {"team": team, "player_id": pid, "player_name": rb.get("player_name"), "position": "RB"}))

    rb_carry_sum = np.sum(np.column_stack(rb_alloc), axis=1) if rb_alloc else np.zeros(n)
    target_sum = target_alloc.sum(axis=1) + other_targets if target_alloc.size else other_targets
    route_target_violation = int(np.max(target_alloc - route_matrix)) if target_alloc.size else 0
    player_reception_arrays = [v for k, v in draws.items() if k.startswith("PLAYER|") and k.endswith("|receptions")]
    player_reception_sum = np.sum(np.column_stack(player_reception_arrays), axis=1) if player_reception_arrays else np.zeros(n)
    recon = {
        "team": team,
        "max_player_rb_carries_minus_team_rushes": int(np.max(rb_carry_sum - rush_plays)) if len(rush_plays) else 0,
        "team_plays_identity_max_abs_error": int(np.max(np.abs(plays - pass_plays - rush_plays))),
        "max_targets_minus_attempts": int(np.max(target_sum - attempts)) if len(attempts) else 0,
        "max_targets_minus_routes": route_target_violation,
        "max_modeled_receptions_minus_qb_completions": int(np.max(player_reception_sum - completions)) if len(completions) else 0,
        "status": "OK",
    }
    keys = [
        "max_player_rb_carries_minus_team_rushes", "team_plays_identity_max_abs_error",
        "max_targets_minus_attempts", "max_targets_minus_routes", "max_modeled_receptions_minus_qb_completions",
    ]
    if any(recon[k] > 0 for k in keys):
        recon["status"] = "SIMULATION_RECONCILIATION_FAILURE"
    return SimulationResult(draws, pd.DataFrame(rows), recon)


def probability_from_draws(values: np.ndarray, side: str, line: float) -> tuple[float, float, float]:
    side = side.upper()
    if side == "OVER":
        win = values > line
        push = values == line
    elif side == "UNDER":
        win = values < line
        push = values == line
    else:
        raise ValueError(f"Unsupported prop side: {side}")
    p_win = float(np.mean(win))
    p_push = float(np.mean(push))
    p_loss = max(0.0, 1.0 - p_win - p_push)
    return p_win, p_push, p_loss
