from __future__ import annotations
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from nfl_model.models.calibration import calibrate_probability, blend_with_market
from nfl_model.pricing.conservative import conservative_probability
from nfl_model.pricing.ev import ev_pct
from nfl_model.pricing.fair_price import fair_american_odds
from nfl_model.pricing.buy_to import worst_acceptable_american
from nfl_model.simulation.monte_carlo import probability_from_draws

MARKET_TO_STAT = {
    "player_receptions": "receptions",
    "player_rush_attempts": "rushing_attempts",
    "player_pass_attempts": "passing_attempts",
    "player_pass_completions": "completions",
    "player_reception_yds": "receiving_yards",
    "player_rush_yds": "rushing_yards",
    "player_pass_yds": "passing_yards",
}


def _market_age_minutes(ts: object) -> float | None:
    if ts is None or (isinstance(ts, float) and np.isnan(ts)):
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 60.0)
    except Exception:
        return None


def _layer_decomposition(p_raw: float, p_cal: float, p_blend: float, p_cons: float, p_mkt: float | None) -> str:
    """Exact transformation attribution in probability points; not a fake causal football decomposition."""
    anchor = p_mkt if p_mkt is not None else .5
    return (
        f"RAW_VS_MARKET={(p_raw-anchor)*100:+.2f}pp;"
        f"CALIBRATION={(p_cal-p_raw)*100:+.2f}pp;"
        f"MARKET_BLEND={(p_blend-p_cal)*100:+.2f}pp;"
        f"UNCERTAINTY={(p_cons-p_blend)*100:+.2f}pp"
    )


def price_prop_rows(
    odds_rows: pd.DataFrame,
    draws: dict[str, np.ndarray],
    player_map: pd.DataFrame,
    ev_floors: dict[str, float],
    market_trust: dict[str, float],
    uncertainty_cfg: dict,
    extreme_disagreement_pp: float = 0.18,
    allowed_positions: dict[str, list[str]] | None = None,
    week: int | None = None,
    max_market_age_minutes: float = 90.0,
    buy_to_extra_ev_margin: float = 0.01,
    hard_stop_extra_ev_margin: float = 0.0,
) -> pd.DataFrame:
    if odds_rows.empty:
        return pd.DataFrame()
    lookup = player_map.set_index("aita_player_id") if not player_map.empty else pd.DataFrame()
    allowed_positions = allowed_positions or {}
    out = []
    for _, row in odds_rows.iterrows():
        pid = row.get("aita_player_id")
        market_key = str(row.get("market_key") or "")
        stat = MARKET_TO_STAT.get(market_key)
        key = f"PLAYER|{pid}|{stat}" if pid and stat else None
        meta = lookup.loc[pid] if isinstance(lookup, pd.DataFrame) and pid in lookup.index else {}
        if isinstance(meta, pd.DataFrame):
            meta = meta.iloc[-1]
        position = str(meta.get("position", row.get("position") or "")) if hasattr(meta, "get") else str(row.get("position") or "")
        if str(row.get("entity_status") or "RESOLVED") == "ENTITY_QUARANTINE":
            out.append({**row.to_dict(), "position": position or None, "model_status": "REJECTED", "rejection_reason": "ENTITY_FAILURE"})
            continue
        critical_ok = meta.get("critical_current_state_ok", True) if hasattr(meta, "get") else True
        if critical_ok is not None and not pd.isna(critical_ok) and not bool(critical_ok):
            out.append({**row.to_dict(), "position": position or None, "model_status": "REJECTED", "rejection_reason": "DATA_QUALITY"})
            continue
        allowed = set(allowed_positions.get(market_key, []))
        if allowed and position not in allowed:
            out.append({**row.to_dict(), "position": position, "model_status": "REJECTED", "rejection_reason": "V1_POSITION_SCOPE"})
            continue
        if not key or key not in draws or pd.isna(row.get("line")) or pd.isna(row.get("american_odds")):
            out.append({**row.to_dict(), "position": position or None, "model_status": "MARKET_NOT_PRICED", "rejection_reason": "ENTITY_FAILURE_OR_MISSING_DRAWS"})
            continue

        age_min = _market_age_minutes(row.get("market_last_update") or row.get("book_last_update"))
        if age_min is not None and age_min > float(max_market_age_minutes):
            out.append({**row.to_dict(), "position": position, "market_age_minutes": age_min, "model_status": "REJECTED", "rejection_reason": "STALE_ODDS"})
            continue

        p_raw, p_push, _ = probability_from_draws(draws[key], str(row["side"]), float(row["line"]))
        p_cal = calibrate_probability(p_raw)
        p_mkt = row.get("market_novig_prob")
        p_mkt = float(p_mkt) if p_mkt is not None and not pd.isna(p_mkt) else None
        p_blend = blend_with_market(p_cal, p_mkt, float(market_trust.get(market_key, 0.45)))

        role_certainty = float(meta.get("role_certainty_score", 70.0)) if hasattr(meta, "get") else 70.0
        historical_agreement = float(meta.get("model_agreement_score", 75.0)) if hasattr(meta, "get") else 75.0
        freshness = float(meta.get("data_freshness_score", 90.0)) if hasattr(meta, "get") else 90.0
        challenger_values = [p_raw, p_cal, p_blend] + ([p_mkt] if p_mkt is not None else [])
        dispersion = float(np.std(challenger_values))
        dispersion_score = float(np.clip(100.0 - dispersion * 450.0, 20.0, 100.0))
        model_agreement = 0.55 * historical_agreement + 0.45 * dispersion_score
        uncertainty_multiplier = float(uncertainty_cfg.get("week1_multiplier", 1.0)) if week == 1 else 1.0
        p_cons, haircut = conservative_probability(
            p_blend, p_mkt, role_certainty, model_agreement, freshness,
            week1_multiplier=uncertainty_multiplier,
            max_haircut_fraction=float(uncertainty_cfg.get("max_edge_haircut_fraction", 0.8)),
        )
        odds = float(row["american_odds"])
        floor = float(ev_floors.get(market_key, 0.05))
        raw_ev, cal_ev, blend_ev, cons_ev = [ev_pct(p, odds, p_push) for p in [p_raw, p_cal, p_blend, p_cons]]
        fair_raw, fair_cal, fair_blend, fair_cons = [fair_american_odds(p, p_push) for p in [p_raw, p_cal, p_blend, p_cons]]
        disagreement = abs(p_cal - p_mkt) if p_mkt is not None else 0.0
        confidence_score = float(np.clip(0.42 * role_certainty + 0.33 * model_agreement + 0.25 * freshness, 0.0, 100.0))
        status = "ACTIONABLE_AT_REFERENCE_PRICE" if cons_ev / 100.0 >= floor else "REJECTED"
        rejection = "" if status.startswith("ACTIONABLE") else "INSUFFICIENT_EV"
        if disagreement >= extreme_disagreement_pp:
            status, rejection = "EXTREME_MODEL_MARKET_DISAGREEMENT", "EXTREME_MODEL_MARKET_DISAGREEMENT"

        out.append({
            **row.to_dict(),
            "position": position or row.get("position"),
            "market_age_minutes": age_min,
            "p_raw": p_raw, "p_push": p_push, "p_calibrated": p_cal, "p_blend": p_blend,
            "p_conservative": p_cons, "uncertainty_haircut_fraction": haircut,
            "fair_odds_raw": fair_raw, "fair_odds_calibrated": fair_cal, "fair_odds_blended": fair_blend,
            "fair_odds_conservative": fair_cons, "ev_raw_pct": raw_ev, "ev_calibrated_pct": cal_ev,
            "ev_blended_pct": blend_ev, "ev_conservative_pct": cons_ev,
            "minimum_required_ev_pct": floor * 100,
            "buy_to_price": worst_acceptable_american(p_cons, floor + float(buy_to_extra_ev_margin), p_push),
            "hard_stop_price": worst_acceptable_american(p_cons, floor + float(hard_stop_extra_ev_margin), p_push),
            "role_certainty_score": role_certainty, "model_agreement_score": model_agreement,
            "model_dispersion": dispersion, "confidence_score": confidence_score,
            "data_freshness_score": freshness, "market_trust_score": float(market_trust.get(market_key, 0.45)) * 100.0,
            "probability_edge_pp": (p_cons - p_mkt) * 100.0 if p_mkt is not None else np.nan,
            "model_market_disagreement_pp": disagreement * 100,
            "probability_layer_decomposition": _layer_decomposition(p_raw, p_cal, p_blend, p_cons, p_mkt),
            "calibration_method": "IDENTITY_NEAR_SHRINKAGE_UNTIL_WALK_FORWARD_ARTIFACT",
            "market_trust_method": "INITIAL_CONFIG_PRIOR_UNTIL_DATASET_B_CALIBRATION",
            "model_status": status, "rejection_reason": rejection,
        })
    return pd.DataFrame(out)
